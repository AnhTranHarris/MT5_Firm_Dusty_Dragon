# Dusty Dragon Performance Scope — Windows Handoff

Status: UI-Lab design contract. This note exists to prevent the final Windows application from reverse-engineering mock behavior.

## Scope hierarchy

`CAPITAL & OBJECTIVES` is the **single Performance-scope selector** for both Investor and Quant lenses:

```text
Firm
Portfolio 1 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 2 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 3 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 4 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
```

The selected scope drives every investor panel and every quant diagnostic. There must be no second independent scope authority. Scope selection is presentation/read-model state only; it never mutates execution authority, MT5 session state, risk policy, broker state, or ledger state.

## Investor semantics

Headline metrics, Capital & Objectives, Capital Protection, Return Quality, Liquidity & Exposure, Return Attribution, and investor notes all render from the same scope key and snapshot version.

Return Attribution deliberately follows the child level of the selected parent:

- `FIRM` -> exactly four Portfolio contributors;
- any Portfolio -> exactly six Desk contributors;
- a selected Desk remains highlighted while all six sibling desks stay visible.

Production attribution rows are supplied by Core and reconcile to the selected parent scope's authoritative net result.

## Quant semantics

The Quant lens uses the **same scope key** as Investor. Switching lenses must never silently reset scope back to Firm.

Each selectable scope may expose an immutable quant read model with:

- Sharpe;
- Sortino;
- recovery factor;
- expectancy in R;
- profit factor;
- average win / average loss;
- fees and net P&L for cost-drag calculation;
- VaR and Expected Shortfall with explicit confidence/horizon metadata;
- pair/factor correlation diagnostics;
- trade/sample count;
- explicit volatility-target policy reference, nullable;
- explicit benchmark policy/read-model reference, nullable;
- alpha, beta, tracking error, and information ratio only when benchmark-relative series exist;
- provenance, calculation version, sample interval, and `as_of_utc`.

Quant calculations belong in Core. The UI may perform only transparent display transforms such as `ES / VaR`, `|avg win| / |avg loss|`, or formatting of already-authoritative inputs. It must not infer Sortino from Sharpe, Recovery from Profit Factor, or benchmark-relative statistics from the absolute-return objective.

The current `performance-quant-scope-mock-v40.js` is UI-Lab-only simulated data. It must be removed when Core exposes real quant read models.

## Production read-model identity

```text
PerformanceScopeKey = FIRM
PerformanceScopeKey = PORTFOLIO:<portfolio_id>:LAYER
PerformanceScopeKey = PORTFOLIO:<portfolio_id>:DESK:<desk_id>
```

A production workspace snapshot should contain the selected scope's investor and quant models together, plus parent attribution context, all under one snapshot/version ID. This prevents mixed-scope rendering.

## Aggregation authority

Layer, Portfolio, and Firm aggregates belong in Core. The UI must not average desk returns, risk statistics, Sharpe ratios, VaR, Expected Shortfall, or correlations into authoritative aggregates. Production aggregation must use the correct capital weights, return series, sample windows, capital flows, currencies, desk lifecycle, and covariance structure.

The UI-Lab fixtures intentionally simulate aggregate values only to exercise interaction and layout.

## Objectives, benchmarks, and risk limits

The firm absolute-return objective is not automatically a Portfolio or Desk objective. A firm open-risk limit is not silently inherited by child scopes. Likewise, the yellow objective is never a benchmark.

Portfolio/Layer/Desk objective, volatility target, benchmark, and risk-budget utilization remain unset unless Core explicitly supplies the appropriate policy reference for that scope.

## MT5 ingestion

A Desk scope is ultimately backed by one verified MT5 account/terminal financial identity. Dusty Core persists broker-neutral account-equity observations, trade/deal facts, risk state, and reconciled capital flows, then produces investor and quant read models. Portfolio/Layer/Firm models aggregate canonical Desk histories downstream.

Do not pass raw `MetaTrader5.account_info()`, `history_deals_get()`, terminal objects, credentials, or Python namedtuples into WebView2/JavaScript.

## Windows implementation

The WinUI 3 host owns one Performance scope state. WebView2 sends a narrow intent such as:

```json
{"type":"performance.scope.select","scopeKey":"PORTFOLIO:P2:DESK:D04"}
```

The application layer resolves the key against an authorized read service and returns one immutable versioned Performance snapshot. Investor and Quant lenses are two presentations of that same selected snapshot. A late response for an older scope/request ID must be discarded.

Lens changes are presentation-only:

```json
{"type":"performance.lens.select","lens":"quant"}
```

Neither message may be interpreted as a broker or trading command.

## QC before migration

Require automated tests for:

- all four portfolios and all seven entities per portfolio;
- Firm attribution exactly four Portfolios;
- Portfolio attribution exactly six Desks;
- every visible Investor and Quant panel carrying the same scope key and snapshot version;
- lens changes preserving selected scope;
- missing/retired/parked desk read models;
- stale and out-of-order asynchronous responses;
- objective/volatility target/benchmark present vs absent;
- VaR/ES confidence and horizon consistency;
- benchmark-relative metrics rejected when benchmark series are absent;
- aggregation calculated in Core rather than presentation;
- UTC/DST boundaries;
- reduced-motion/high-contrast modes;
- 100/125/150/200% Windows display scaling;
- WebView2 message schema/version rejection.

The engineering target is zero known contract ambiguity before migration. Literal zero debugging cannot be guaranteed for a real Windows/MT5 integration.
