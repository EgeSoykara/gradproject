# Software requirements specification

Version 1.0 · 1 October 2026

## 1 Introduction

PortfolioAI implements the supplied **AI-Assisted Portfolio Management System** graduation proposal using Python and Django. Its purpose is educational portfolio accounting, visualization and data-driven decision support on a standard personal computer. The user approved English UI/documentation, local execution, general metal reference prices, future API-key configuration and a replaceable lightweight model. No fixed delivery date was requested.

This document follows the introduction, overall description and specific-requirements structure requested under IEEE 830-1998 in the proposal. It does not claim third-party standards certification.

## 2 Overall description

The system is a browser application served on 127.0.0.1, with a local SQLite database. Individual users maintain their own portfolios, transaction ledgers and notes. A local administrator maintains shared asset metadata and market data. Public/API connectors and training run as explicit management commands, outside page requests.

An account may have multiple portfolios. Each portfolio uses either market data or a synthetic learning dataset. Data cannot silently cross those boundaries. There are no bank account connections, stored bank credentials, order execution or automatic trades.

Users require a desktop browser; responsive layouts also support narrow displays. Initial installation requires internet access for Python packages. The learning workspace operates offline after installation. Real-data functionality depends on provider access and sufficient historical coverage.

## 3 Specific functional requirements

| ID | Requirement | Implementation | Acceptance evidence |
| --- | --- | --- | --- |
| F01 | Register/login/logout and isolate user workspaces | Django auth; owner-filtered views | Anonymous redirects, registration and owner-access tests |
| F02 | Record, edit and delete buy/sell/cash entries | Transaction forms; atomic Decimal ledger replay | Weighted cost, partial sale, fees, insufficient cash, oversell and rollback tests |
| F03 | Value funds, gram metals and cash in TRY/USD/EUR/GBP | MarketBook and snapshot service | FX conversion, dated prices, no future/cross-dataset fallback tests |
| F04 | Collect, validate and retain historical market data | CSV/JSON, Yahoo, TEFAS, normalized API, GoldAPI | Import atomicity/idempotence; adapter fixtures; Yahoo live smoke test |
| F05 | Display portfolio value, allocation and history | Django templates; locally bundled Plotly | Browser dashboard inspection and populated-page checks |
| F06 | Compare against S&P 500/NASDAQ 100/Bitcoin | Same-currency normalized benchmark series | Cash-flow return tests and USD browser comparison |
| F07 | Explain robustness and historical stress behavior | Volatility, drawdown, Sharpe, concentration, correlations and replay | Known-path drawdown test; two visible synthetic stress windows |
| F08 | Train a lightweight model and evaluate it chronologically | Replaceable sklearn estimator; purged holdout and TimeSeriesSplit | Feature causality test, trained artifacts and model-results report |
| F09 | Present source-linked news and social sentiment | NewsAPI/X/import adapters and VADER | Provider fixtures, URL validation and labeled sentiment fixture |
| F10 | Create/edit/delete private planning notes | Owner-scoped Django ModelForms | Isolation and escaping tests; browser create/edit flow |

The original proposal's LSTM reference is treated as an example, consistent with the user's approval to begin with a lightweight model. The default is a small random forest, not a language-model API. The resilience score is explicitly a heuristic rather than a trained crash-probability model.

## 4 Nonfunctional requirements

| ID | Requirement | Mechanism / qualification |
| --- | --- | --- |
| N01 | Run on consumer hardware | CPU model, bounded tree depth, SQLite, no GPU dependency |
| N02 | Protect personal records | Django authentication, CSRF middleware, owner-scoped queries, escaped templates |
| N03 | Avoid embedded secrets | Environment variables and ignored local secret file |
| N04 | Preserve financial precision | Decimal quantities, prices, fees, FX and ledger operations |
| N05 | Make provenance visible | Dataset banners, source/date metadata, errors and model dataset labels |
| N06 | Handle unavailable providers | Explicit failures, transactional imports, cached observations retained |
| N07 | Support reproducibility | Locked packages, deterministic model seed, metric JSON and command documentation |
| N08 | Follow Python conventions | Ruff formatting and import/static checks; PEP 8-oriented style |
| N09 | Work without an internet connection in demo mode | Local scripts, database and Plotly bundle; no CDN dependencies |

## 5 Acceptance mapping to the contract

K01: documented setup, migrations and smoke checks. K02: owner isolation tests. K03: Decimal ledger tests. K04: historical conversion tests. K05: import and provider fixtures plus the explicitly documented live verification boundary. K06: value/TWR/benchmark tests and UI. K07: metrics and two stress windows. K08: trained model artifacts and chronological evaluation. K09: source/time/sample transparency and configured-key boundary. K10: notes, responsive screens and error/empty states. K11: source, installation guide, this SRS, validation/model reports and final report.

The user's key-deferral decision changes K05/K09 from universal live-provider success to working adapters, explicit sample mode and documented credential-dependent verification. TEFAS remains dependent on public-service availability. No unavailable connection is represented as a successful live integration.

## 6 Out of scope and future extensions

Bank credentials and execution, real-time trading guarantees, exact bank spreads, tax/settlement/corporate-action processing, LSTM by default, production hosting, real email delivery, exhaustive social coverage and independent ISO/IEC 27001 certification are outside this iteration. A future change must update requirements, method assumptions, tests and acceptance evidence together.
