"""Pluggable estimator, chronological holdout and expanding-window evaluation."""

import importlib
import json
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.utils.text import slugify
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from portfolio.models import ModelRun, Price


def features(prices):
    r = prices.pct_change()
    x = pd.DataFrame(
        {
            'return_1': r,
            'return_5': prices.pct_change(5),
            'return_20': prices.pct_change(20),
            'volatility_20': r.rolling(20).std(),
            'ma_gap': prices / prices.rolling(20).mean() - 1,
        }
    )
    for lag in (1, 2, 3, 5):
        x[f'lag_{lag}'] = r.shift(lag)
    return x.replace([np.inf, -np.inf], np.nan)


def new_estimator():
    module, name = settings.ML_MODEL_CLASS.rsplit('.', 1)
    cls = getattr(importlib.import_module(module), name)
    if name == 'RandomForestRegressor':
        return cls(n_estimators=80, max_depth=5, min_samples_leaf=12, random_state=42, n_jobs=1)
    estimator = cls()
    if 'random_state' in estimator.get_params():
        estimator.set_params(random_state=42)
    return estimator


def train_asset(asset, dataset):
    rows = list(
        Price.objects.filter(asset=asset, dataset=dataset)
        .order_by('date')
        .values_list('date', 'close')
    )
    prices = pd.Series({d: float(p) for d, p in rows}, dtype=float)
    x = features(prices)
    target = prices.pct_change().shift(-1)
    training = x.assign(target=target).dropna()
    if len(training) < 180:
        raise ValueError(f'{asset.symbol}: at least 201 price observations are required.')
    split = int(len(training) * 0.8)
    # Purge one sample: its target would touch the first holdout day.
    train, test = training.iloc[: split - 1], training.iloc[split:]
    columns = list(x.columns)
    model = new_estimator()
    model.fit(train[columns], train.target)
    prediction = model.predict(test[columns])
    actual = test.target.to_numpy()
    base = np.zeros(len(actual))
    folds = []
    for a, b in TimeSeriesSplit(n_splits=3, gap=1).split(train):
        candidate = new_estimator()
        candidate.fit(train.iloc[a][columns], train.iloc[a].target)
        estimate = candidate.predict(train.iloc[b][columns])
        folds.append(float(mean_absolute_error(train.iloc[b].target, estimate)))
    # Hypothetical long/cash strategy: next close return, 10 bps per position change.
    positions = (prediction > 0.001).astype(float)
    costs = np.abs(np.diff(np.r_[0, positions])) * 0.001
    strategy = positions * actual - costs
    metrics = {
        'mae': float(mean_absolute_error(actual, prediction)),
        'rmse': float(np.sqrt(mean_squared_error(actual, prediction))),
        'baseline_mae': float(mean_absolute_error(actual, base)),
        'direction_accuracy': float(np.mean(np.sign(actual) == np.sign(prediction)) * 100),
        'cv_mae': folds,
        'train_rows': len(train),
        'test_rows': len(test),
        'train_start': str(train.index[0]),
        'train_end': str(train.index[-1]),
        'test_start': str(test.index[0]),
        'test_end': str(test.index[-1]),
        'strategy_return_pct': float((np.prod(1 + strategy) - 1) * 100),
        'buy_hold_return_pct': float((np.prod(1 + actual) - 1) * 100),
        'cost_bps': 10,
        'features': columns,
        'target': 'Next observation close-to-close return in asset quote currency',
        'dataset': dataset,
        'warning': 'Synthetic data: pipeline demonstration only.'
        if dataset == 'demo'
        else 'Historical results do not establish future performance.',
        'test_curve': [
            {'date': str(d), 'strategy': float(a), 'baseline': float(b)}
            for d, a, b in zip(
                test.index, 100 * np.cumprod(1 + strategy), 100 * np.cumprod(1 + actual)
            )
        ],
    }
    # Refit a separate final estimator after evaluation. Unseen next return stays unknown.
    model = new_estimator()
    model.fit(training[columns], training.target)
    next_return = float(model.predict(x.dropna().iloc[[-1]])[0])
    output_dir = settings.BASE_DIR / 'artifacts' / 'models' / dataset
    output_dir.mkdir(parents=True, exist_ok=True)
    run_name = f'{slugify(asset.symbol)}-{uuid4().hex[:12]}'
    artifact = output_dir / f'{run_name}.joblib'
    joblib.dump(
        {
            'model': model,
            'features': columns,
            'data_end': str(prices.index[-1]),
            'dataset': dataset,
        },
        artifact,
    )
    (output_dir / f'{run_name}.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    return ModelRun.objects.create(
        asset=asset,
        dataset=dataset,
        model_name=settings.ML_MODEL_CLASS,
        data_end=prices.index[-1],
        prediction=next_return,
        metrics=metrics,
        artifact=str(artifact.relative_to(settings.BASE_DIR)),
    )
