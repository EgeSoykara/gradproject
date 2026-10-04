from datetime import date

import numpy as np
import pandas as pd

from .valuation import MissingData


def risk_metrics(returns, weights=(), annual_risk_free=0.0):
    returns = pd.Series(returns, dtype=float).dropna()
    if len(returns) < 30:
        return None
    vol = float(returns.std(ddof=1) * np.sqrt(252))
    wealth = pd.concat(
        [pd.Series([1.0]), (1 + returns).cumprod().reset_index(drop=True)], ignore_index=True
    )
    drawdown = float((wealth / wealth.cummax() - 1).min())
    excess = float(returns.mean() * 252 - annual_risk_free)
    sharpe = excess / vol if vol > 1e-10 else None
    concentration = sum(float(w) ** 2 for w in weights)
    components = {
        'volatility': max(0, 1 - vol / 0.60),
        'drawdown': max(0, 1 - abs(drawdown) / 0.60),
        'diversification': max(0, 1 - concentration),
    }
    score = round(
        100
        * (
            0.4 * components['volatility']
            + 0.4 * components['drawdown']
            + 0.2 * components['diversification']
        )
    )
    return {
        'volatility': vol * 100,
        'drawdown': drawdown * 100,
        'sharpe': sharpe,
        'score': score,
        'observations': len(returns),
        'components': components,
        'risk_free': annual_risk_free,
        'method': 'Heuristic v1 · 40% volatility / 40% drawdown / 20% diversification',
    }


def stress_tests(snap, book):
    windows = [
        ('Pandemic window', date(2020, 2, 19), date(2020, 3, 23)),
        ('2022 tightening window', date(2022, 1, 3), date(2022, 10, 12)),
    ]
    results = []
    for name, start, end in windows:
        try:
            weighted_return = 0.0
            for h in snap['holdings']:
                aid = h['asset'].id
                p0 = book.asset_try(aid, start) / book.rate(snap['currency'], start)
                p1 = book.asset_try(aid, end) / book.rate(snap['currency'], end)
                weighted_return += h['weight'] / 100 * float(p1 / p0 - 1)
            cash_weight = float(snap['cash'] / snap['total']) if snap['total'] else 0
            weighted_return += cash_weight * float(
                book.rate(snap['currency'], start) / book.rate(snap['currency'], end) - 1
            )
            results.append(
                {
                    'name': name,
                    'start': start,
                    'end': end,
                    'return_pct': weighted_return * 100,
                    'impact': float(snap['total']) * weighted_return,
                }
            )
        except MissingData as exc:
            results.append({'name': name, 'error': str(exc)})
    return results


def correlation_matrix(snap, book):
    data = {}
    for h in snap['holdings']:
        aid = h['asset'].id
        rows = book.prices.get(aid, [])[-253:]
        data[h['asset'].symbol] = pd.Series(
            {d: float(p * book.rate(h['asset'].currency, d)) for d, p in rows}
        )
    if len(data) < 2:
        return pd.DataFrame()
    return pd.DataFrame(data).pct_change(fill_method=None).dropna().corr()
