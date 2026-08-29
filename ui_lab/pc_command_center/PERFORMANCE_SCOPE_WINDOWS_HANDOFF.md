# Dusty Dragon Performance Scope — Windows Handoff

Status: UI-Lab design contract. This note exists to prevent the final Windows application from reverse-engineering mock behavior.

## Scope hierarchy

`CAPITAL & OBJECTIVES` owns an independent chart scope selector:

```text
Firm
Portfolio 1 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 2 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 3 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
Portfolio 4 -> Layer | Desk 1 | Desk 2 | Desk 3 | Desk 4 | Desk 5 | Desk 6
```

The selector is local to the graph. It must not mutate execution authority, MT5 session state, risk policy, broker state, ledger state, or the rest of the Performance dashboard.

## Production read-model shape

Every selectable scope must arrive from Dusty Core as an explicit immutable read model. The presentation layer must never build a Layer by summing browser values and must never query MetaTrader directly.

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
- current equity;
- current drawdown;
- high-water mark when authoritative;
- objective policy reference, nullable;
- benchmark policy reference, nullable;
- provenance/reconciliation state;
- dated UTC cumulative-return series or one canonical equity curve from which Core produces horizon slices.

## Aggregation authority

Layer and Portfolio aggregates belong in Core. The UI must not treat a simple average of desk returns as authoritative. Production aggregation must account for capital weights, external flows, account currencies, desk inception/retirement, parked desks, and changing allocations.

The current `performance-scope-mock-v38.js` intentionally generates simulated scope histories only so the hierarchy can be evaluated visually. It is test fixture code and must be deleted when real scope read models exist.

## Objectives

The firm objective is not automatically a desk objective. In v3.8 the yellow absolute-return objective remains visible for Firm. Portfolio/Layer/Desk scopes show actual history but leave the objective unset unless an explicit scope-specific objective is supplied. Production must preserve this rule; never inherit a target merely because it produces a prettier chart.

## MT5 ingestion

A desk scope is ultimately backed by one verified MT5 account/terminal identity. Dusty Core should persist broker-neutral account-equity observations and reconciled capital flows, then build the desk curve. Portfolio/Layer/Firm curves aggregate those canonical desk histories downstream.

Do not pass raw `MetaTrader5.account_info()`, `history_deals_get()`, terminal objects, credentials, or Python namedtuples into WebView2/JavaScript.

## Windows implementation

The WinUI 3 host should expose scope selection as presentation state only. The WebView2 surface sends a narrow intent such as:

```json
{"type":"performance.scope.select","scopeKey":"PORTFOLIO:P2:DESK:D04"}
```

The native/application layer resolves that key against an already-authorized read service and returns an immutable versioned snapshot. The message must never be interpreted as a broker or trading command.

## QC before migration

Require automated tests for:

- all four portfolios and all seven entities per portfolio;
- missing/retired/parked desk read models;
- stale scope snapshots;
- portfolio membership changes;
- desk inception inside a longer reporting horizon;
- deposits/withdrawals and demo resets;
- mixed account currencies and FX conversion policy;
- objective present vs objective absent;
- benchmark present vs benchmark absent;
- UTC/DST boundaries;
- rapid scope switching while a timeframe transition is active;
- reduced-motion/high-contrast modes;
- 100/125/150/200% Windows display scaling;
- WebView2 message schema/version rejection.

The engineering target is zero known contract ambiguity before migration. Literal zero debugging cannot be guaranteed for a real Windows/MT5 integration.
