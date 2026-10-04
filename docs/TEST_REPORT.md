# Testing and validation report

Completed 3 October 2026. Environment: Windows, Python 3.13.5, Django 5.2.17, SQLite. Locked dependencies are recorded in `requirements.txt`.

## Automated verification

**39 tests passed.** Django system checks report no issues. Migration checking reports no pending model changes. Ruff static checks and formatting checks pass.

```powershell
.\.venv\Scripts\python.exe manage.py test --verbosity 1
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

| Area | Verified behavior |
| --- | --- |
| Accounting | Weighted average purchases, partial sales, commissions, realized profit and cash |
| Invalid trades | Overselling and insufficient cash rejected; failed write rolled back |
| Historical modifications | Deposit reduction/deletion and deletion of a purchase needed for a later sale rejected atomically |
| Currency valuation | Historical USD/TRY conversion, foreign-currency trade fees and reporting valuation |
| Cash-flow performance | Deposits do not create return; withdrawals do not create a loss; price appreciation does create return |
| Market chronology | No future prices or cross-dataset fallback; observations older than seven days rejected |
| Authentication | Anonymous access redirects to login; registration creates an isolated market portfolio |
| Authorization | Other users cannot edit/delete transactions or notes or select another owner's portfolio |
| Web protections | Destructive routes require POST; CSRF checks enforced; note HTML escaped |
| Input and pages | Empty pages render; malformed date filters show a user-facing error; transaction form saves a deposit |
| Data imports | CSV schema, batch rollback, idempotence, invalid numbers, future dates and live DEMO symbols |
| Providers | NewsAPI, X, GoldAPI, TEFAS and Yahoo normalization fixtures; missing keys and failure paths |
| Metal units | USD/troy-ounce to TRY/gram conversion checked against an exact fixture |
| Shared data | Non-staff web upload rejected |
| Analytics | Known-path maximum drawdown and insufficient-history handling |
| Model chronology | Features unaffected by changes to future observations |
| Model command | Missing eligible data produces a failing command status |
| Demo repeatability | Adding later days preserves every earlier synthetic price and exchange rate |
| Sentiment | Positive/negative/neutral labels checked on three deliberately simple English fixtures |

The sentiment fixture is a sanity check, not a representative financial-language benchmark. Provider fixtures verify mapping and failure handling; they do not verify every upstream service's access plan or network availability.

## Integration and model runs

On 1 October, the Yahoo historical adapter successfully imported 18 observations for 28–30 September 2026: nine benchmark closes and nine currency rates. TEFAS's AAK request for that period returned no observations; the command reported an error and preserved stored data. Those outcomes are visible in the connection log.

GoldAPI, NewsAPI and X have no supplied keys. Their authenticated adapters are implemented and fixture-tested; live credential verification is deferred as agreed. Metal historical coverage can be supplied through CSV/JSON. The normalized market API needs an actual service implementing the documented schema.

On 3 October, the demo data generator was extended without altering any existing historical price or FX value. A compatibility check compared all observations through 1 October and found **zero differences**. The dataset contains 16,065 synthetic prices and 5,355 synthetic rates through 2 October. Six models were trained, evaluated and saved. The latest per-asset metrics, holdout dates and artifact locations are in `MODEL_RESULTS.md`.

Only the synthetic money-market fund improved on the zero-return baseline's MAE. The other five models are labeled as having no baseline improvement. This is an expected possible outcome of transparent evaluation; no real-market forecasting accuracy is inferred from synthetic data.

## Browser verification

The working local app was checked in the in-app browser. Sign-in opens the populated learning dashboard. Holdings, benchmark and AI screens display values from the ledger and stored observations. The comparison currency was changed to USD and the displayed returns updated. A planning note was created and saved through the actual form. News and social-sentiment screens display clearly labeled synthetic material.

The dashboard was inspected at the desktop viewport and at 390 × 844 pixels. The mobile layout stacks cards and charts, retains reachable navigation, and keeps wide tables inside horizontal scroll containers. Plotly is served locally. An initial global SVG-style collision was corrected and charts were visually rechecked.

## Validation boundary

This report establishes application behavior on the tested local environment. It does not establish forecasting usefulness on real data, uninterrupted provider access, intraday accuracy, fund settlement correctness or suitability for public deployment. Real-data evaluation should preserve input histories, rerun models, inspect baseline comparisons and record upstream source conventions.
