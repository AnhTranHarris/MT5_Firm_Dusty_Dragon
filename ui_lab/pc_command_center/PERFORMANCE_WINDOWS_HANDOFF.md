# Dusty Dragon Performance UI — Windows / MT5 Handoff Contract

Status: design-time contract for the UI Lab. This document exists so the final Windows application can reuse the same semantics instead of reverse-engineering the mock.

## Why quarterly, annual, and five-year were blank

Performance v3.5 deliberately stopped fabricating longer-horizon actual returns from MTD/WTD values. The mock only contained `performance.returns`, which represented the monthly demonstration series, so the correct UI response was to leave unsupported horizons empty. v3.7 restores all four mock horizons with **explicit dated simulated series** in `performance-mock-history.js`; none is derived from another horizon.

Production must preserve that rule: missing history is missing history. Never synthesize quarterly, fiscal-year, or five-year actual returns from a shorter-period scalar merely to populate a chart.

## Canonical UI performance payload

The presentation layer consumes dated UTC cumulative-return points, not raw MetaTrader objects:

```json
{
  "asOfUtc": "2026-08-28T21:44:00Z",
  "historyProvenance": "BROKER_RECONCILED",
  "horizonSeries": {
    "month": [
      {"atUtc": "...Z", "cumulativeReturnPct": 0.0}
    ],
    "quarter": [],
    "year": [],
    "fiveYear": []
  }
}
```

Rules:

1. `asOfUtc` is authoritative and timezone-aware UTC. The UI must not substitute the PC's wall clock for broker/account reporting truth.
2. Every point timestamp is UTC and strictly increasing.
3. No point may be later than `asOfUtc`.
4. Each horizon is calculated independently from the canonical account-equity history and capital-flow ledger.
5. The final point for the active reporting horizon must reconcile to the firm's corresponding performance summary.
6. Data provenance must be explicit (`MOCK_SIMULATED`, `BROKER_RECONCILED`, etc.).
7. The UI may interpolate only for visual transitions between already-authoritative read models. Interpolation is never persisted as performance data.

## MT5 acquisition boundary

MetaQuotes documents `account_info()` as the source for current account fields including balance, equity, current profit, margin, and free margin. Production should sample the assigned terminal/account after the existing terminal/session verification has passed.

Use `history_deals_get(date_from, date_to)` for broker deal history and related reconciliation. Do not use market-price bars (`copy_rates_*`) as a substitute for account performance history. Price bars describe instruments, not the account's capital curve.

MetaQuotes states that MT5 timestamps/history are UTC and that Python datetime inputs should be created in UTC. Dusty therefore normalizes all broker timestamps to timezone-aware UTC at the adapter boundary.

Official references:

- https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py

## Correct performance construction

A trustworthy capital curve requires two persisted event classes:

- periodic **equity observations** from the verified account (`balance`, `equity`, observation UTC timestamp);
- separately classified **external capital flows** such as deposit, withdrawal, broker adjustment, demo reset/compression.

External cash flows must not appear as trading return. `dusty_dragon.performance.build_time_weighted_curve()` provides the first broker-neutral implementation boundary. It chains sub-period returns after removing external flow from ending equity for that interval.

This is intentionally downstream of MT5. The UI never performs this accounting in JavaScript.

### Why account snapshots are required

Deal history alone can reconstruct realized transactions but does not provide the complete historical path of unrealized account equity between trades. If Dusty wants an investor-grade equity curve, the production collector must persist equity snapshots at a bounded cadence. The exact cadence is a policy decision; it should be frequent enough for useful drawdown/performance reporting but not tied to animation frame rate.

## Horizon construction

The read service derives horizon slices from one canonical persisted curve:

- Monthly: first calendar day through `asOfUtc`.
- Quarterly: Dusty's fiscal quarter (Oct-Dec, Jan-Mar, Apr-Jun, Jul-Sep) through `asOfUtc`.
- Annual: Dusty's management fiscal year, Oct 1-Sep 30, through `asOfUtc`.
- Five year: current fiscal year plus four preceding fiscal years, through `asOfUtc`.

The horizon endpoint is the same canonical as-of observation; only the start boundary changes. Do not maintain four independent ledgers.

## Multi-terminal aggregation

Each MT5 terminal/account remains a separate financial identity. Production flow:

```text
verified MT5 terminal/account
    -> account snapshots + deal/capital-flow reconciliation
    -> desk canonical equity curve
    -> desk performance read model
    -> layer/firm aggregation service
    -> immutable UI payload
    -> Windows presentation
```

Firm aggregation must be produced by Dusty Core, not by summing arbitrary browser state. Desks can have different account currencies in the future; if that is allowed, conversion policy and FX timestamp/source must be explicit before firm-level dollar aggregation is valid.

## Windows application translation

Preferred migration path: WinUI 3 shell + WebView2 for the already-proven HTML/CSS visualization, with native services owning MT5/process/system integration. Microsoft documents WebView2 as the supported Edge/Chromium embedding control for WinUI 3 and its web/native messaging channel.

Architecture:

```text
WinUI 3 host
  ├─ native MT5/session service
  ├─ performance/read-model service
  ├─ SQLite/event persistence
  ├─ risk/execution authority (separate)
  └─ WebView2 presentation
       └─ receives immutable JSON snapshots only
```

Rules for the WebView2 boundary:

1. UI thread owns WebView2; do not block it with MT5 polling, SQLite, or performance calculation.
2. Background services calculate and validate read models, then marshal immutable snapshots to the UI thread.
3. Restrict navigation to local/trusted app content.
4. Validate every web/native message; never expose generic filesystem/process/broker APIs to JavaScript.
5. Keep broker credentials and MT5 objects out of WebView2.
6. Preserve the current no-motion/high-contrast accessibility states as presentation settings, not backend modes.
7. Use an explicit payload contract version so native and web presentation can reject incompatible messages rather than fail silently.

Microsoft references:

- https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/webview2
- https://learn.microsoft.com/en-us/microsoft-edge/webview2/

## QC required before Windows conversion

Zero debugging cannot be guaranteed for any real platform migration. The target is **zero known contract ambiguity** and automated detection of predictable failures. Before migration, require:

- Python tests for flow-adjusted performance construction;
- JS syntax checks;
- UI performance-contract validation;
- fixtures for deposit/withdrawal/demo-reset behavior;
- fixtures for missing MT5 history, stale account snapshots, terminal disconnect, and broker reconnection;
- DST/timezone tests proving UTC boundaries;
- account-currency tests;
- reconciliation tests between firm headline returns and horizon endpoints;
- WebView2 message-schema tests;
- screenshot/visual-regression tests at target Windows scaling factors (100%, 125%, 150%, 200%);
- reduced-motion and Windows forced-colors/high-contrast tests;
- failure-injection testing before any LIVE execution capability is considered.

## UI Lab files that are intentionally temporary

- `mock-data.js`: broad fixture data.
- `performance-mock-history.js`: explicit simulated history fixture only.
- `performance-timeframe-v37.js`: presentation consumer of the canonical dated-series shape.

When the Windows app is connected to Dusty Core, remove the mock-history script entirely. Do not convert its numbers into seed production history.
