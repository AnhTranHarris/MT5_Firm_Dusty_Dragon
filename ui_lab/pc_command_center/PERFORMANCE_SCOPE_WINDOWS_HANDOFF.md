# Dusty Dragon Performance Scope — Windows Handoff

Status: UI-Lab design contract. This note exists to prevent the final Windows application from reverse-engineering mock behavior.

## Scope hierarchy

`CAPITAL & OBJECTIVES` is the **single investor-scope selector** for the Performance workspace:

```text
Firm
Portfolio 1 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 2 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 3 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 4 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
```

The selected scope drives every investor panel: headline metrics, Capital & Objectives, Capital Protection, Return Quality, Liquidity & Exposure, Return Attribution, and investor notes. There must be no second independent investor-scope selector. Scope selection is presentation/read-model state only; it never mutates execution authority, MT5 session state, risk policy, broker state, or ledger state.

## Return Attribution semantics

Attribution deliberately follows a different child level than the other panels:

- `FIRM` selected -> show exactly the four Portfolio contributors.
- any Portfolio selected -> show exactly the six Desk contributors belonging to that Portfolio.
- if a specific Desk is selected in the Portfolio dropdown, attribution still shows all six Portfolio desks and visually identifies the selected desk. This preserves contribution context instead of collapsing attribution to a meaningless one-row chart.
- the attribution header state must identify the active Performance scope, e.g. `PORTFOLIO 2 · LAYER · 6 DESKS` or `PORTFOLIO 2 · DESK 4 · 6 DESKS`.

Production attribution rows must be supplied by Core and reconcile to the selected parent scope's authoritative net result within a documented tolerance. The browser must never invent attribution from percentages.

## Production read-model shape

Every selectable scope must arrive from Dusty Core as an explicit immutable read model. Presentation must never build a Layer by summing browser values and must never query MetaTrader directly.

Recommended identity:

```text
PerformanceScopeKey = FIRM
PerformanceScopeKey = PORTFOLIO:<portfolio_id>:LAYER
PerformanceScopeKey = PORTFOLIO:<portfolio_id>:DESK:<desk_id>
```

Recommended payload fields per scope:

- stable `scope_key`;
- display label;
- `as_of_utc`;
- account/base currency or reporting currency;
- current equity and free margin;
- MTD return and net P&L;
- current and maximum drawdown;
- open risk, gross exposure, net exposure;
- win rate, profit factor, Sharpe, expectancy when authoritative;
- active/total desk count for aggregate scopes;
- high-water mark when authoritative;
- objective policy reference, nullable;
- benchmark policy reference, nullable;
- provenance/reconciliation state;
- dated UTC cumulative-return series or one canonical equity curve from which Core produces horizon slices;
- attribution children with stable child IDs, P&L contribution, and contribution share.

## Aggregation authority

Layer, Portfolio, and Firm aggregates belong in Core. The UI must not treat a simple average of desk returns as authoritative. Production aggregation must account for capital weights, external flows, account currencies, desk inception/retirement, parked desks, changing allocations, and reconciliation status.

The current `performance-scope-mock-v39.js` intentionally generates simulated scope histories, panel metrics, and attribution only so the hierarchy can be evaluated visually. It is test-fixture code and must be deleted when real scope read models exist.

## Objectives and risk limits

The firm objective is not automatically a Portfolio or Desk objective. The yellow absolute-return objective remains visible for Firm. Portfolio/Layer/Desk scopes leave objective and variance unset unless Core explicitly supplies a scope-specific objective.

Likewise, the firm open-risk limit is not silently inherited by Portfolio or Desk panels. Non-Firm scopes may display measured open risk, but a scope-specific risk-budget utilization value requires an explicit Core policy reference.

## MT5 ingestion

A desk scope is ultimately backed by one verified MT5 account/terminal financial identity. Dusty Core persists broker-neutral account-equity observations, trade/deal facts, risk state, and reconciled capital flows, then builds the Desk read model. Portfolio/Layer/Firm read models aggregate those canonical desk histories downstream.

Do not pass raw `MetaTrader5.account_info()`, `history_deals_get()`, terminal objects, credentials, or Python namedtuples into WebView2/JavaScript.

## Windows implementation

The WinUI 3 host should own one Performance scope state. The WebView2 surface sends a narrow intent such as:

```json
{"type":"performance.scope.select","scopeKey":"PORTFOLIO:P2:DESK:D04"}
```

The native/application layer resolves that key against an already-authorized read service and returns one immutable, versioned Performance workspace snapshot containing the selected scope plus parent attribution context. All panels render from that same snapshot version. A late response for a previously selected scope must be discarded by request/snapshot ID so rapid user switching cannot mix panels from different scopes.

The message must never be interpreted as a broker or trading command.

## QC before migration

Require automated tests for:

- all four portfolios and all seven entities per portfolio;
- Firm attribution exactly four Portfolios;
- Portfolio attribution exactly six Desks;
- attribution P&L/share reconciliation to parent scope;
- every visible investor panel carrying the same scope key and snapshot version;
- missing/retired/parked desk read models;
- stale scope snapshots and out-of-order asynchronous responses;
- portfolio membership changes;
- desk inception inside a longer reporting horizon;
- deposits/withdrawals and demo resets;
- mixed account currencies and FX conversion policy;
- objective present vs objective absent;
- scope risk-limit present vs absent;
- benchmark present vs benchmark absent;
- UTC/DST boundaries;
- rapid scope switching while a timeframe transition is active;
- reduced-motion/high-contrast modes;
- 100/125/150/200% Windows display scaling;
- WebView2 message schema/version rejection.

The engineering target is zero known contract ambiguity before migration. Literal zero debugging cannot be guaranteed for a real Windows/MT5 integration.
