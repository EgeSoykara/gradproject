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

The original contract example lives in `dashboard/mock/example.json`. Copy the delivered persona JSON files into `dashboard/mock/`. The panel lists the available personas and the API accepts `?fixture=persona_1`. English uses the supplied English file for Persona 2. The other personas use the localized fields in their original files. Missing fields appear as unavailable or are omitted for optional cards. Persona files stay outside Git.

The transaction form searches the assets already stored in SQLite. When the full fund catalog arrives, import it with `python manage.py import_fund_catalog path/to/universe_scores.json`. Existing asset records are preserved. Notes can link to a fund or the portfolio. The Benchmark page uses ledger-based time-weighted returns with a default start of 100 on the first transaction date. Run `python manage.py refresh_benchmarks` daily to refresh the on-disk SQLite cache from Yahoo Finance. It can run in Windows Task Scheduler, and the page uses the SQLite data on every request. Live portfolio valuation also requires historical prices for the assets held.

## Bridge integration

Unpack `EgeSpecial.zip` and place `PortfolioAI_Ege` next to this project. Keep the supplied key file as `.env` inside `PortfolioAI_Ege`. From the Django folder, run:

```powershell
$enginePatch = (Resolve-Path -LiteralPath 'integrations/ai-engine.patch').Path
git -C ../PortfolioAI_Ege apply $enginePatch
.\.venv\Scripts\python.exe -m pip install -e ../PortfolioAI_Ege 'statsmodels==0.15.0' 'tefas-crawler==0.6.0' 'transformers==5.18.0'
Copy-Item ../PortfolioAI_Ege/results/dashboard_examples/persona_*.json dashboard/mock/
.\.venv\Scripts\python.exe manage.py import_fund_catalog ../PortfolioAI_Ege/data/universe_scores.json
.\start.ps1 -Engine
```

Run the patch once on a fresh extraction. It adapts the bridge's savings tracker to use the Django ledger's external cash flows and exposes the sentiment breakdown for each theme. The bridge keeps its original cash-flow behavior for callers using its original signature.

`dashboard/services.py` sends the active portfolio's positions and complete history to a separate local process running `dashboard/bridge_worker.py`. Positions use prices from the supplied archives and metal symbols are translated to the engine's codes. A portfolio needs at least one open position with a matching archive entry. Currency quotes and the benchmark use their respective sources. Dashboard requests use the cached news data and run without access to the delivered API keys. The daily refresh pipeline remains a separate manual operation.

On Ege's machine, the two running previews are on port 8016 (personas) and 8017 (engine). For the engine preview, sign in as the existing `demo` user and select **Arşiv veri örneği** via the portfolio switch. The integration was run with Python 3.13 and the locally installed CPU build of PyTorch.
