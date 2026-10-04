# Model evaluation results

Generated 2026-10-03 · Dataset: demo

This report records the latest completed training run for each asset. Errors are measured on fractional next-observation returns, not price levels.

**All prices in these runs are synthetic. These results validate the software pipeline and do not establish performance on real financial markets.**

| Asset | Model MAE | Zero-return MAE | RMSE | Direction accuracy | Test observations | Lower MAE than baseline |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| DEMO-BD | 0.005103 | 0.005020 | 0.006338 | 49.9% | 353 | No |
| DEMO-EQ | 0.010031 | 0.010001 | 0.012211 | 51.3% | 353 | No |
| DEMO-MM | 0.000157 | 0.000395 | 0.000199 | 97.5% | 353 | Yes |
| XAG | 0.013077 | 0.012966 | 0.016439 | 49.0% | 353 | No |
| XAU | 0.008468 | 0.008429 | 0.010568 | 51.3% | 353 | No |
| XPT | 0.010116 | 0.009948 | 0.012750 | 47.3% | 353 | No |

## Chronology and repeatability

### DEMO-BD

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.004924, 0.004904, 0.005120. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: -10.10%. Buy-and-hold return: 2.13%. Cost: 10 bps per position change. Forecast after final refit: +0.049% for the next observation.

Saved artifact: `artifacts\models\demo\demo-bd-364e91b2bae2.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

### DEMO-EQ

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.010251, 0.009676, 0.009339. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: -12.74%. Buy-and-hold return: -7.40%. Cost: 10 bps per position change. Forecast after final refit: +0.056% for the next observation.

Saved artifact: `artifacts\models\demo\demo-eq-96763db6d388.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

### DEMO-MM

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.000158, 0.000165, 0.000157. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: 0.00%. Buy-and-hold return: 14.83%. Cost: 10 bps per position change. Forecast after final refit: +0.038% for the next observation.

Saved artifact: `artifacts\models\demo\demo-mm-5d6d5762cc35.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

### XAG

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.012888, 0.013533, 0.013115. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: -13.76%. Buy-and-hold return: -3.28%. Cost: 10 bps per position change. Forecast after final refit: -0.078% for the next observation.

Saved artifact: `artifacts\models\demo\xag-770f81ea473c.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

### XAU

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.007842, 0.008677, 0.007750. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: -21.22%. Buy-and-hold return: -4.14%. Cost: 10 bps per position change. Forecast after final refit: -0.002% for the next observation.

Saved artifact: `artifacts\models\demo\xau-b7fa9b708d20.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

### XPT

Estimator: `sklearn.ensemble.RandomForestRegressor`. Data ends 2026-10-02. Training: 2019-12-30–2025-05-23 (1410 observations). Holdout feature dates: 2025-05-27–2026-10-01 (353 observations). Each holdout target is the following close return.

Expanding-window MAE: 0.010947, 0.010526, 0.010058. A one-observation gap separates training from validation and the final holdout.

Illustrative long/cash return: -37.46%. Buy-and-hold return: -44.21%. Cost: 10 bps per position change. Forecast after final refit: -0.308% for the next observation.

Saved artifact: `artifacts\models\demo\xpt-01e474ad6e79.joblib`. Its adjacent JSON contains full evaluation metrics and holdout curves.

## Interpretation and limits

1 of 6 models achieved lower holdout MAE than the zero-return baseline. Models without improvement are labeled accordingly in the UI. No significance test or real-market predictive advantage is claimed.

The backtest assumes feature-day close execution, ignores taxes, slippage and settlement constraints, and uses 10 bps per position change. Capacity figures in the UI are independent alternatives before fees, not a jointly optimized trading plan. The resilience score is a separate documented heuristic, not the output of this prediction model.

## Reproduce

```powershell
.\.venv\Scripts\python.exe manage.py train_models --dataset demo
.\.venv\Scripts\python.exe manage.py model_report --dataset demo
```

Exact real-data reproducibility requires retaining the input observations and locked package versions. The demo generator preserves past observations when extended to a later date; models trained on a longer series naturally have different holdout boundaries and metrics.
