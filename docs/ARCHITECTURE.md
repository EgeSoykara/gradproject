# Architecture and calculation methods

## Application layers

`config/` contains Django settings and entry points. `portfolio/models.py` stores accounts' portfolios, transactions, notes, shared assets/prices/FX, news, sync logs and model runs. `forms.py` handles user input; `views.py` scopes each personal record to its owner. Templates and `static/app.css` implement the English UI. `static/vendor/plotly.min.js` is a locally bundled dependency.

Services separate responsibilities:

- `ledger.py`: Decimal weighted-average accounting and atomic full-history validation.
- `valuation.py`: dated market lookup, FX conversion, holdings and daily value/TWR histories.
- `analytics.py`: risk, concentration, correlation and hypothetical historical replay.
- `dashboard/services.py`: hands the active archive portfolio to the local analysis package.
- `providers.py`: validation, normalized imports, authenticated news/social/metals/API adapters.
- `public_sources.py`: optional Yahoo and TEFAS historical adapters.
- `demo.py`: fictional funds, synthetic prices/rates, posts and a personal sample portfolio.

Management commands prepare data and train models independently of HTTP requests. There is no web-triggered training and no implicit recurring job. All incoming market data passes through a single validation/import contract.

## Data relationships

User → portfolios → transactions and notes. Transactions optionally reference an asset. Asset → dated prices and model runs. Prices, FX, news and model runs have explicit dataset identity. Unique constraints prevent duplicate asset/date/dataset or currency/date/dataset observations. Portfolio data is personal; market data is shared and can only be uploaded through a staff account or local CLI.

## Accounting

Cash is denominated in TRY. A foreign-currency trade/cash amount is multiplied by a stored `fx_to_try` snapshot for its transaction date. A purchase increases cost by quantity × unit price + fee, converted into TRY. A partial sale releases proportional weighted average cost; proceeds less fee and released cost become realized P&L. Purchases and sales move cash. Deposits/withdrawals change both cash and net contributions.

Entries replay by date and database ID; same-date insertion order matters. Negative cash or selling more units than currently held invalidates the entire write. Updating or deleting a historical transaction validates subsequent entries and rolls back on failure. Re-entering an edited transaction recalculates its historical FX snapshot from the selected dataset.

Current holdings equal quantity × latest allowed quote × quote-currency/TRY rate. Target-currency display divides TRY values by TRY per target unit. Cost and realized P&L are also translated at the chosen valuation date, so these are reporting equivalents, not separate foreign-currency tax books. Total P&L is current total value minus net contributed TRY capital, translated at the valuation date.

## History and comparison

The historical series includes business days, all actual transaction dates and the selected end date. No future price fills an earlier date. Prior observations can be carried forward for no more than seven calendar days. Missing data prevents a complete valuation instead of becoming zero.

For each observation, external cash flow F is translated at that day's FX. The daily time-weighted factor is `(end_value − F) / previous_value`, using an **end-of-day external-flow convention**. The first funded observation starts at index 100. This approximation does not capture intraday timing; fees on the opening date appear in value/P&L but are outside the displayed return index's starting point. Selected-range comparisons rebase the first available observation to 100. Zero-capital intervals contribute a neutral factor; withdrawal-to-zero and later restart therefore do not imply a continuously invested account.

Benchmarks use the exact same dates and reporting currency. Yahoo series are unadjusted price returns; dividend reinvestment is not implied. Imported series may have other conventions, which their provenance must state. A shorter selected range still requires enough pre-range data to reconstruct earlier holdings.

## Risk and stress

Annual volatility is sample standard deviation × sqrt(252). Sharpe uses mean daily return × 252 divided by annual volatility, with an explicit annual risk-free assumption of zero. Zero volatility yields no Sharpe value. Drawdown uses a cumulative wealth path including its initial level. At least 30 return observations are required.

Resilience v1 is a bounded heuristic with 40% volatility, 40% drawdown and 20% diversification. The first two normalize against 60%; diversification is one minus the sum of squared weights, including cash. It is not calibrated to default, loss or recovery probabilities. Correlations use daily returns aligned in the selected reporting currency for up to 253 price observations per held asset.

Stress windows are 19 February–23 March 2020 and 3 January–12 October 2022. Current/selected-date weights are frozen and multiplied by each asset's historical endpoint return in the selected reporting currency; TRY cash's FX return is included. This is hypothetical exposure replay. Synthetic paths reproduce no actual historical market loss and are labeled accordingly.

## Analysis engine

For an archive-connected portfolio, Django passes positions, dated transactions and display preferences to the local engine. The archive's GRU supplies fund outlooks. FinTurkBERT scores eligible news items from the engine's local cache. The dashboard presents those results alongside deterministic portfolio statistics. The market brief displays imported headlines with their sources and timestamps.

## Security and operating boundary

Django hashes passwords, checks CSRF, escapes HTML, uses ORM queries and HTTP-only session cookies. Personal-object routes filter by authenticated owner. Notes are never transmitted to data providers. Source URLs accept HTTP(S) only; tokens stay in environment variables and request headers. Network failures avoid logging credentials. The archive engine reads weights from the separately installed package. The bridge clears credentials for paid sources when rendering the dashboard, and tests reject network calls.

ISO/IEC 27001 themes are addressed through access control, asset/provenance tracking, credential separation and backup guidance. This does not constitute certification. The local configuration intentionally uses HTTP on loopback and Django's development server. Public deployment would require a separate security and operations design. The database is not encrypted at rest; local OS account protection and backups remain relevant.
