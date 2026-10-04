# Data providers and import contract

## Dataset separation

Each price, rate, news item and model run belongs to `demo` or `live`. A portfolio selects exactly one dataset. The live path never falls back to demonstration records. Imports are transactional; a malformed observation rolls back the whole batch. The identity key is asset/currency + date + dataset, so repeated imports update observations rather than duplicate them.

Daily values are not described as tick-level real-time data. The holdings table displays the observation date. Valuation uses the most recent observation on or before the requested date and rejects values older than seven calendar days. Historical FX coverage must accompany prices. A retained cache remains available after a sync failure, subject to the same freshness rule.

## Available adapters

| Source | Command | Configuration | Verification |
| --- | --- | --- | --- |
| Yahoo via yfinance | `fetch_history yahoo --start YYYY-MM-DD` | No application key | Actual three-day request succeeded for all six series |
| TEFAS via pytefas | `fetch_history tefas --symbol AAK --start YYYY-MM-DD` | No application key | Tested range returned no data; success not verified |
| GoldAPI spot metals | `sync_data metals` | `GOLD_API_TOKEN` | Response/normalization fixtures; live credentials pending |
| NewsAPI | `sync_data news` | `NEWS_API_KEY` | Response/normalization fixture; live credentials pending |
| X recent search | `sync_data social` | `X_BEARER_TOKEN`, optional `X_QUERY` | Response/normalization fixture; live credentials pending |
| Normalized market API | `sync_data market` | HTTPS `MARKET_API_URL`, optional bearer `MARKET_API_KEY` | Import and error-path fixtures |
| Local CSV/JSON | `import_data file` | None | Atomicity, schema and idempotence tests |

Yahoo symbols: `^GSPC` → SP500, `^NDX` → NASDAQ100, `BTC-USD` → BTC, `TRY=X` → USD/TRY, `EURTRY=X` → EUR/TRY, `GBPTRY=X` → GBP/TRY. Benchmark prices are unadjusted daily closes. The default end date is yesterday to avoid knowingly labeling an in-progress session as a final daily close. Data access remains subject to the upstream service's terms and availability.

TEFAS requests investment funds (`YAT`) and imports matching fund codes, names and prices. The library handles date chunks. No browser challenge bypass is implemented. If the service rejects a request or returns no data, use a permitted export or a separately licensed provider through the normalized interface. Official publication frequency and fund settlement are not simulated as intraday trading.

GoldAPI requests XAU, XAG and XPT in USD per troy ounce. The adapter divides by **31.1034768** and multiplies by the stored USD/TRY rate on or before the quote's UTC date, yielding TRY per gram. FX must already be present. These are spot snapshots, not guaranteed daily closing prices or executable bank quotes. Multi-year metal history should use an appropriate licensed export through CSV/JSON. The source label records the spot conversion.

NewsAPI requests at most 50 recent English articles. X requests at most 50 recent matching English posts; no pagination or claim of exhaustive coverage is made. Saved timestamps and source links remain visible. VADER is a lexical English baseline, with compound-score thresholds ±0.05. Imported posts can substitute for API access without pretending to be a live stream.

## Market CSV

```csv
type,symbol,date,value
price,XAU,2026-09-30,6000.00
fx,USD,2026-09-30,45.00
fx,EUR,2026-09-30,50.00
fx,GBP,2026-09-30,59.00
```

The numbers above are **schema examples, not market observations**. Do not use them as actual quotes. `price` refers to the asset's catalog currency and unit. All metal catalog entries use TRY per gram. Register real TEFAS symbols with kind `fund`, currency `TRY`, unit `units`, using Django admin or the TEFAS adapter. Fictional DEMO symbols are rejected for live imports. FX value means TRY per one unit of the named currency. TRY is implicit at 1.

```powershell
.\.venv\Scripts\python.exe manage.py import_data prices.csv
```

The staff-only web upload accepts the same CSV, up to 5 MB. Large histories should use the command line.

## Normalized market JSON

An HTTPS service at `MARKET_API_URL` must return this structure. It is a provider-neutral interface, not a universal API-key field for arbitrary vendors. A vendor with another schema needs a mapping adapter.

```json
{
  "prices": [{"symbol": "XAU", "date": "2026-09-30", "close": "6000.00"}],
  "rates": [{"currency": "USD", "date": "2026-09-30", "try_per_unit": "45.00"}]
}
```

Numbers are illustrative only. Values must be finite and positive, with at most eight stored decimal places. Future dates are rejected. `import_data prices.json` uses the same schema.

## News and social JSON

```json
[
  {
    "id": "your-source-record-id",
    "title": "Your permitted source text",
    "url": "https://example.com/source",
    "source": "Your dataset name",
    "published_at": "2026-09-30T10:00:00Z"
  }
]
```

Use `import_data posts.json --kind social` or `--kind news`. The URL is optional for local samples. HTTP(S) URLs only; text remains escaped in templates. Provider tokens are sent only in HTTP headers. Error logs store generic failure reasons, not credential-bearing request URLs.

## Primary documentation

- [yfinance download interface](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- [pytefas developer documentation](https://github.com/mirzazad/pytefas)
- [GoldAPI official request and response example](https://github.com/goldapi-io/gold-api-examples-js)
- [NewsAPI everything endpoint](https://newsapi.org/docs/endpoints/everything)
- [X official recent search example](https://github.com/xdevplatform/docs/blob/main/x-api/posts/search/quickstart/recent-search.mdx)

Integration documentation was checked on 1 October 2026. Service availability, access plans and response schemas can change independently of this application.
