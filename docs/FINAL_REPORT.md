# AI Assisted Portfolio Management System

## Abstract

PortfolioAI is a local Python and Django application that brings fund units, precious-metal quantities and cash into a single portfolio workspace. It supports transaction accounting, multiple reporting currencies, interactive charts, benchmark comparisons, historical risk analysis, GRU fund outlooks, source-aware news and FinTurkBERT sentiment, and private planning notes. The implementation follows the supplied graduation proposal and the subsequent agreement to use a Turkish/English interface, local execution, general metal reference prices and API credentials that can be added later.

The delivered system operates with an explicitly labeled synthetic learning dataset. It also includes historical Yahoo and TEFAS adapters, CSV/JSON imports, a normalized market API interface and optional GoldAPI, NewsAPI and X integrations. Live access remains dependent on each source's availability and credentials. Automated checks and browser verification establish the software workflow; synthetic forecasts do not establish financial predictive performance.

## Problem and objectives

Investors who hold fund units and gram-denominated metals need a consistent view of quantities, costs, reporting currencies and risk. A change in total value can reflect an investment return, a currency movement or a cash contribution. The application makes those distinctions through an explicit transaction ledger and historical calculations. Its analytical features help a user inspect assumptions and compare scenarios rather than rely on an unexplained score.

The project has four practical objectives: maintain reliable portfolio accounting, expose data provenance and freshness, provide comparable performance and risk views, and implement a replaceable model with reproducible evaluation. Source integration and research notes support those objectives.

## Requirements and implementation

The English SRS maps the proposal's requirements to functions and acceptance evidence. Accounts and portfolios use Django authentication and owner-scoped queries. Transactions maintain Decimal quantities, prices, fees and historical conversion rates. The application replays the ledger after a write and rejects changes that invalidate later cash or holdings. Weighted average cost handles partial sales and realized profit.

Market observations are dated and separated by dataset. A valuation can use a prior observation for no more than seven calendar days and never uses a future price for an earlier date. TRY is the cash base; USD, EUR and GBP are reporting currencies. General metal prices are TRY per gram. GoldAPI snapshots convert USD per troy ounce using the recorded exchange rate and the troy-ounce-to-gram factor.

The dashboard shows portfolio value, available cash, profit/loss, allocation and historical value. The benchmark screen rebases portfolio and selected benchmarks to 100 over a common period and currency. Time-weighted return removes recorded external cash flows under a stated end-of-day convention. The UI follows the existing Stitch project's restrained navy, green and light-surface design and adapts it for narrow screens.

## Analytical methods

Portfolio volatility uses daily sample standard deviation annualized by sqrt(252). Sharpe uses a visible zero risk-free-rate assumption. Maximum drawdown measures the largest peak-to-trough wealth decline. Correlation uses aligned returns in the selected reporting currency. Resilience is a documented heuristic combining volatility, drawdown and concentration; it is not a learned probability of loss.

Historical stress windows freeze the selected allocation and replay asset endpoint returns from the pandemic and 2022 tightening periods. A portfolio created after those windows is therefore a hypothetical exposure analysis. Synthetic demo prices are labeled and do not claim to reproduce actual crash losses.

The archive engine supplies GRU fund outlooks and uses FinTurkBERT to classify news items related to portfolio themes. Django displays the supplied results in the portfolio dashboard. Imported headline titles, sources and timestamps remain available in the market brief. Private notes are stored locally.


## Validation results

The [release checklist](RELEASE_CHECKLIST.md) records the current automated and local acceptance checks. The suite runs with network access blocked. Earlier synthetic model results remain in the [prototype archive](archive/MODEL_RESULTS.md).


## Security and operational choices

The app uses Django password hashing, CSRF protection, escaped templates and owner-filtered record access. Shared market uploads require staff access. Keys are read from environment variables and kept out of source and rendered pages. Provider exceptions avoid recording credential-bearing URLs. No bank credentials are stored or orders executed.

These controls address relevant security themes from the proposal's ISO/IEC 27001 reference; the project does not claim certification. The chosen operating environment is a local development server and SQLite. Public hosting, encrypted database storage and broader operational controls would require a separate scope.

## Deliverables

| Proposal deliverable | Delivered artifact |
| --- | --- |
| Data integration and preprocessing | Provider services, import/fetch/sync commands, dated prices/FX, schema validation and provenance |
| Portfolio management core | Models, Decimal ledger, valuation/history services and transaction forms |
| Interactive dashboard | Working Django templates, Turkish/English responsive UI and locally bundled Plotly |
| Benchmarking and comparative analysis | Same-period/currency normalized portfolio, S&P 500, NASDAQ 100 and Bitcoin views |
| AI analytics engine | GRU and FinTurkBERT through the local engine, plus risk/stress/correlation statistics |
| Testing and validation report | Automated suite and [current acceptance checks](RELEASE_CHECKLIST.md) |
| Final report | This document, with SRS, architecture, provider guide, README and agreed contract |

## Limitations and further work

The application uses daily observations and does not simulate fund settlement, taxes, corporate actions or bank execution spreads. Forecast confidence intervals are not calibrated. The illustrative backtest omits slippage and assumes close execution. Social analysis covers a limited sample and can misread irony and financial jargon. Provider schemas and access plans can change.

The next evidence-based improvement is a complete real-price/FX dataset with preserved provenance, followed by model and baseline evaluation on that dataset. Maintain a record of the model evaluation window, the chronological split and the comparison baseline.

## Reproducibility and references

The README documents installation, launch, sample access, administrator creation, imports, model training and verification commands. Locked dependencies and generated metric JSON files support repeatability. The demo extension preserves historical values; exact real-data experiments also require retaining the original observations.

- Source requirements: `Graduation Projects Proposal Form_ H. Altıncay.docx`.
- [Django 5.2 documentation](https://docs.djangoproject.com/en/5.2/).
- [scikit-learn time-series splitting](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
- Provider documentation and tested boundaries are linked in `DATA_PROVIDERS.md`.
