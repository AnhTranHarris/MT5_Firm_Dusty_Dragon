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

## Lens-aware rail contract

Investor and Quant deliberately reuse the same four physical diagnostic slots beside `CAPITAL & OBJECTIVES`. Do not implement Quant as a second dashboard appended below Investor.

Investor reading order:

1. Capital Protection
2. Return Quality
3. Liquidity & Exposure
4. Return Attribution

Quant reading order:

1. Absolute Efficiency — first establish whether absolute returns compensate for total/downside risk.
2. Trade Edge — then inspect the execution economics producing those returns.
3. Tail / Diversification — then inspect loss severity, dependence and concentration.
4. Benchmark / Active Risk — finally evaluate relative skill only when a valid benchmark exists.

## Lens color contract

Quant uses one bright-purple semantic accent across the complete analytical workspace: the four Quant rail panels, the persistent `CAPITAL & OBJECTIVES` panel chrome, and the active `QUANT` segmented-control button. This gives the operator an immediate whole-workspace cue that the current interpretation lens is Quant even though the capital chart and selected scope remain shared.

Purple is **presentation/lens metadata only**. It must never encode broker health, desk health, P&L sign, risk state, warning severity, order state, or execution authority. Green/amber/red retain those established operational meanings. Chart-series semantics also remain unchanged when the lens changes: actual return/capital stays green, objective stays amber, as-of stays blue, and risk-reference lines keep their defined semantics. Only container chrome changes to purple.

In Windows forced-colors/high-contrast mode, system colors supersede the purple brand accent. Reduced/no-motion modes must not depend on animation to communicate the active lens.

A lens change replaces rail labels and contents in place while preserving selected Performance scope, chart horizon, snapshot version and Capital & Objectives context. Investor-only notes are hidden in Quant mode rather than duplicated.

## Investor semantics

Headline metrics, Capital & Objectives, Capital Protection, Return Quality, Liquidity & Exposure, Return Attribution, and investor notes all render from the same scope key and snapshot version.

Return Attribution deliberately follows the child level of the selected parent:

- `FIRM` -> exactly four Portfolio contributors;
- any Portfolio -> exactly six Desk contributors;
- a selected Desk remains highlighted while all six sibling desks stay visible.

Production attribution rows are supplied by Core and reconcile to the selected parent scope's authoritative net result.

## Quant semantics

The Quant lens uses the **same scope key** as Investor. Switching lenses must never silently reset scope back to Firm.

Each selectable scope may expose an immutable quant read model with Sharpe, Sortino, recovery factor, expectancy in R, profit factor, average win/loss, fees/net P&L, VaR, Expected Shortfall, correlation diagnostics, sample metadata, optional volatility-target policy, and optional benchmark-relative metrics.

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

## Objectives, benchmarks, and risk limits

The firm absolute-return objective is not automatically a Portfolio or Desk objective. A firm open-risk limit is not silently inherited by child scopes. Likewise, the yellow objective is never a benchmark.

Portfolio/Layer/Desk objective, volatility target, benchmark, and risk-budget utilization remain unset unless Core explicitly supplies the appropriate policy reference for that scope.

## MT5 ingestion

A Desk scope is ultimately backed by one verified MT5 account/terminal financial identity. Dusty Core persists broker-neutral account-equity observations, trade/deal facts, risk state, and reconciled capital flows, then produces investor and quant read models. Portfolio/Layer/Firm models aggregate canonical Desk histories downstream.

Do not pass raw `MetaTrader5.account_info()`, `history_deals_get()`, terminal objects, credentials, or Python namedtuples into WebView2/JavaScript.

## Windows implementation

The WinUI 3 host owns one Performance scope state. WebView2 sends narrow intents such as:

```json
{"type":"performance.scope.select","scopeKey":"PORTFOLIO:P2:DESK:D04"}
{"type":"performance.lens.select","lens":"quant"}
```

The application layer resolves scope against an authorized read service and returns one immutable versioned Performance snapshot. Investor and Quant are presentations of that same selected snapshot. A late response for an older scope/request ID must be discarded. Lens changes must be local/presentation-only and must not refetch MT5 merely to repaint the rail or recolor the shared capital-panel chrome.

Neither message may be interpreted as a broker or trading command.

## QC before migration

Require automated tests for all portfolios/entities; attribution reconciliation; identical scope/snapshot identity across Investor and Quant; lens changes preserving scope and timeframe; lens color never altering chart/risk semantics; missing/retired/parked desks; stale/out-of-order responses; optional objectives/volatility targets/benchmarks; VaR/ES horizon consistency; benchmark-relative metric rejection without benchmark series; Core-side aggregation; UTC/DST; reduced motion; forced colors/high contrast; 100/125/150/200% Windows scaling; and WebView2 schema/version rejection.

The engineering target is zero known contract ambiguity before migration. Literal zero debugging cannot be guaranteed for a real Windows/MT5 integration.
