# PortfolioAI

A local Django investment workspace for fund units, gram-based precious metals, cash, portfolio benchmarking and explainable analytics. The interface supports Turkish and English. The visual direction follows the existing **PortföyAI — Akıllı Portföy Yönetimi** Stitch project, adapted into working Django templates.

## Quick start on Windows

Clone the repository and prepare the virtual environment, SQLite database, synthetic dataset on first use:

```powershell
git clone https://github.com/EgeSoykara/gradproject.git
cd gradproject
.\setup.ps1
.\start.ps1
```

Requires Python 3.13 for the tested configuration. On later runs, use only `.\start.ps1`. The startup script applies pending database migrations before starting the local server. The repository includes the demo generator; setup creates the local database and demo data.

If you have the `EgeSpecial.zip` analysis package, install the full dashboard with `.\setup.ps1 -EngineZip "C:\path\to\EgeSpecial.zip"` and start it with `.\start.ps1`. [Engine setup and example portfolio](UI_README.md#bridge-integration).

Open **http://127.0.0.1:8000**. Sample account:

- Username: `demo`
- Password: `PortfolioDemo!2026`

This account is local, non-admin and intended only for sample data. Alternatively, create an account from the sign-in page. The dashboard offers a learning portfolio or guides you through naming a personal portfolio, adding cash and recording a purchase.

If PowerShell script execution is restricted, run the interpreter directly:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Fresh installation

Requires Python 3.13 for the tested configuration, and an internet connection to download packages once. No Node build step, GPU, Docker, external fonts or chart CDN is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo --create-account
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`setup.ps1` runs the preparation commands in sequence. It never resets an existing demo account password or transaction ledger. The server binds only to this computer. The included configuration is for local development, not public hosting.

## What works

- Account registration, session login/logout and user-isolated portfolios and notes.
- Fund/metal purchases, partial sales, fees, deposits and withdrawals; edit/delete with full-ledger validation and rollback.
- Weighted average cost, realized/unrealized P&L, TRY cash and TRY/USD/EUR/GBP valuation.
- Historical value chart, allocation chart and time-weighted return; same-currency S&P 500, NASDAQ 100 and Bitcoin comparisons.
- A single robustness score per portfolio, data dates and sources, and an Expert view with volatility, drawdown, Sharpe, correlation and historical scenarios when the required history is available.
- GRU fund outlooks and FinTurkBERT news sentiment in the archive-connected dashboard.
- Source-linked imported headlines, private notes and CSV ledger export.
- Atomic market CSV/JSON import with an administrator upload page and a run history, TEFAS and Yahoo historical adapters, optional GoldAPI/NewsAPI/X integrations, and a normalized JSON API adapter.

## Data modes and current integration status

**Learning portfolios use synthetic data**, including fictional `DEMO-*` fund symbols. Their stress returns and model statistics demonstrate computation, not actual market behavior. There is no silent fallback from real to synthetic data.

Yahoo's adapter successfully imported a three-day sample of benchmark prices and currency rates during verification. TEFAS returned no observations for the tested fund/date range; the adapter reports that condition without replacing the cache. GoldAPI, NewsAPI and X require your future keys and were tested with fixtures, not live credentials. Metal history can be imported as TRY per gram through CSV/JSON; GoldAPI synchronization stores dated spot snapshots.

For meaningful real-data analysis, import complete price and FX history covering the transaction dates. Three days of connection-test data is insufficient for model training or stress testing.

## Adding keys later

Copy `.env.example` to `.env`, fill only the services you use and restart the server. Do not put keys in Python files. See [data-provider setup](docs/DATA_PROVIDERS.md) for schemas, example commands and source limitations.

```powershell
.\.venv\Scripts\python.exe manage.py fetch_history yahoo --start 2025-01-01
.\.venv\Scripts\python.exe manage.py fetch_history tefas --symbol AAK --start 2025-01-01
.\.venv\Scripts\python.exe manage.py sync_data metals
.\.venv\Scripts\python.exe manage.py sync_data news
.\.venv\Scripts\python.exe manage.py sync_data social
.\.venv\Scripts\python.exe manage.py import_data path\to\prices.csv
```

These commands run explicitly, outside web requests. Nothing schedules background network access automatically. They can later be invoked by Windows Task Scheduler using this virtual environment and project working directory.

To register additional assets or use the shared-data upload form:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Open `/admin/` with your own administrator account. Ordinary users cannot alter the shared market-data store through the upload endpoint.

## Back up and restore the workspace

Create a new SQLite backup file, with the app running or stopped.

~~~powershell
.\.venv\Scripts\python.exe manage.py backup_workspace "$env:USERPROFILE\Documents\portfolioai-backup.sqlite3"
~~~

The backup contains accounts, portfolios, transactions, notes and stored market data. Store it privately and use a new filename each time. To restore, stop the server, move the current database and any SQLite sidecar files to a separate folder, copy the backup into the project as db.sqlite3, then start the server. Keep the previous database until you verify that your portfolios open.

Keep the analysis ZIP and any model weights and provider configuration you use in your own private storage. The database backup covers only the SQLite workspace.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m ruff check .
```

The automated tests use provider and analysis fixtures. External requests are blocked during the suite.


## Documentation

- [Release checklist](docs/RELEASE_CHECKLIST.md) — completion status and verification steps.
- [Agreed scope](CONTRACT.md) — original Turkish working agreement, updated with the user's decisions.
- [Software requirements](docs/SRS.md) — English requirements and acceptance traceability.
- [Architecture and financial methods](docs/ARCHITECTURE.md).
- [Data providers](docs/DATA_PROVIDERS.md).
- [Validation report](docs/TEST_REPORT.md) and [archived prototype results](docs/archive/MODEL_RESULTS.md).
- [Final project report](docs/FINAL_REPORT.md).

## Boundaries

The app does not execute orders or store bank credentials. Metals use general reference values, not bank spreads. Cash is held in TRY; foreign-currency transaction amounts are converted at the recorded historical rate. There is no tax accounting, settlement engine, fund corporate-action engine, email password recovery, production deployment or ISO certification. Return conventions, data freshness limits and backtest assumptions are documented and visible in the UI.

Back up `db.sqlite3` while the application is stopped. Keep `.env`, `.local-secret`, the database and generated model files out of version control. Retain source data separately if you need exact reproducibility of a real-data research run.
