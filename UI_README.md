# PortfolioAI dashboard

From this project's directory in PowerShell with Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo --create-account
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/dashboard/ and register or sign in with the example account printed during setup. The new dashboard also opens after sign-in. The existing overview continues to use the local ledger. Model training is optional for the existing AI Insights lab and is unnecessary for this dashboard.

## Data sources

The authenticated page and `GET /api/dashboard/?lang=tr&currency=TRY&profile=balanced` use the same adapter. `USE_MOCK_DASHBOARD=true` is the default. The API returns the example as supplied. The page formats the selected currency from the values in the file and selects localized text where available. When a file contains a single text version it displays that text verbatim. The language and profile controls do not regenerate offline results.

| Card | Payload field |
| --- | --- |
| Portfolio and savings tracker | `portfolio`, including `allocation_by_subcategory` and optional `savings_tracker` |
| Stay the course | Optional `stay_the_course` with locale-specific summary and details |
| Savings plan | `savings_plan` and `user_basket.trajectory` |
| Robustness | `robustness`, `sub_scores` and `scenarios` |
| AI comments | `ai_comments`, using `text_tr` or `text_en` |
| Theme news | `news.themes` or `theme_status` |
| Model basket comparison | `rebalancing.target_comparison`, `contribution_only` and optional `cash_allocation` |
| Fund cards | `fund_cards`, including `gru_view`, risk, eligibility and news status |

The supplied contract example lives in `dashboard/mock/example.json`. Add actual `persona_1.json` through `persona_4.json` to that directory as they arrive. The panel will list the available files and the same file can be selected with `?fixture=persona_1` on the API. The shipped example has no theme news, crisis table, subcategory model weights, cash allocations, tracker or discipline card. It only includes a 21-day fund horizon. Missing fields are shown as unavailable or omitted where optional. If a horizon has a percentile and no status label, the display uses strong at 67 and above, weak at 33 and below, and neutral otherwise. Confirm these display thresholds with the bridge owner or use the bridge's explicit labels. The supplied allocation weights sum to 113.04%, so the values are shown as supplied alongside a pie of their relative shares.

The transaction form searches the assets already stored in SQLite. When the full fund catalog arrives, import it with `python manage.py import_fund_catalog path/to/universe_scores.json`. Existing asset records are preserved. Notes can link to a fund or the portfolio. The Benchmark page uses ledger-based time-weighted returns with a default start of 100 on the first transaction date. Run `python manage.py refresh_benchmarks` daily to refresh the on-disk SQLite cache from Yahoo Finance. It can run in Windows Task Scheduler, and the page uses the SQLite data on every request. Live portfolio valuation also requires historical prices for the assets held.

## Bridge integration

Clone or unpack the AI repository next to this project after it is delivered. From this folder, install it in the same environment and restart Django with `USE_MOCK_DASHBOARD=false` in `.env`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ../ai-repo
```

`dashboard/services.py` is the only module that imports `service_bridge`. It uses the active portfolio and current market prices for positions, translates metal symbols to the bridge names and converts cash to the selected currency. The current published contract only accepts fund purchases and cash deposits in its historical contribution list. For ledgers containing withdrawals, sales or trades in grams, it sends current holdings and balance and leaves the historical contribution list empty until that contract is confirmed. The ledger retains complete records. A live integration check requires the delivered bridge, sample personas and market data.
