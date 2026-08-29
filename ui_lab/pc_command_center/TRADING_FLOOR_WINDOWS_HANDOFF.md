# Dusty Dragon Trading Floor — Windows Handoff

Status: UI-Lab design contract for the eventual WinUI 3/WebView2 application.

## Analytical hierarchy density

The analytical hierarchy is not a decorative fallback. It should consume most of the Trading Floor working area and expose useful desk/layer telemetry without requiring a drill-down.

Each visible Desk row may show, at minimum:

- canonical operational state using the same Trading Floor vocabulary/colors;
- current realized P&L for the active trading day;
- current day return;
- progress versus the explicit daily target/reference policy.

Each Layer header may show the corresponding aggregate:

- combined realized P&L across eligible child desks;
- capital-weighted day return across eligible child desks;
- progress versus the same explicit daily target/reference.

The UI must not calculate authoritative realized P&L from equity deltas, open-position P&L, or MT5 account balance changes. Production Core must provide reconciled realized P&L from closed-deal/ledger facts with capital flows classified separately.

The UI-Lab field `realizedPnlToday` is therefore an explicit simulated read-model fixture. It exists only to test information density and must be replaced by a Core-owned value during Windows migration.

## No-motion / analytical layout contract

No-motion is a **true 2D Trading Floor layout**, not the 3D spatial scene with the canvas merely hidden.

When analytical/no-motion mode is active:

- remove the orbital canvas and all spatial navigation chrome;
- remove the spatial-only dossier/footer row from the Trading Floor grid;
- remove the orbit hint, layer navigator, space-grid decoration, and rotating cube controls;
- let the hierarchy consume the complete Trading Floor body below the panel header;
- preserve one-screen five-layer structure with no vertical scrollbar;
- increase primary hierarchy typography using the space reclaimed from spatial-only UI;
- reduce padding/gaps before shrinking primary desk/layer text;
- keep desk identity + operational state as the primary line and realized/day/target telemetry as one compact secondary line.

The WinUI implementation should therefore have separate presentation layouts or templates for Spatial and Analytical/No-Motion modes. Do not preserve invisible spatial geometry, fixed orbital padding, or dossier height in the 2D template.

Mode changes are presentation-only. Switching to 2D must not change selected desk/layer, read-model snapshot, MT5 session state, risk state, or execution authority.

## Daily target semantics

`dailyTargetPct` is a policy/reference value, not permission to increase risk and not a benchmark. A Desk or Layer that is behind target remains subject to exactly the same execution/risk authority as one that is ahead. If production does not define a daily target for a scope, the UI must show `UNSET` rather than inherit or fabricate one.

## Aggregation authority

Production Layer aggregation belongs in Core. The mock currently demonstrates the intended display using child data, but WinUI/WebView2 must receive a versioned immutable Layer summary from the application layer. The browser/UI must not become the authoritative aggregator.

Required production fields should include at least:

```text
scopeKey
snapshotVersion
asOfUtc
operationalState
realizedPnlToday
returnTodayPct
dailyTargetPct (nullable)
dailyTargetProgressPct (nullable)
childCount
activeChildCount
provenance
```

Desk and Layer values shown together must come from the same snapshot/version to prevent mixed-time hierarchy views.

## Layout contract

At ordinary desktop widths, preserve all five hierarchy columns in one fixed Trading Floor viewport. Child rows should expand vertically to use the available height. The analytical tree should increase information density by using empty space, not by retaining spatial-mode geometry or reducing typography until labels overlap.

At constrained heights, reduce padding/gaps before reducing primary-value font size. No vertical page/panel scrolling is permitted for the primary Trading Floor hierarchy.

## Windows QC

Before production migration, test 100/125/150/200% Windows scaling, forced colors/high contrast, long broker/desk names, negative and five/six-figure P&L, target values above/below/at zero, unprovisioned and parked desks, partial layers, stale snapshots, late snapshot rejection, layer totals that reconcile exactly to Core, and transitions between spatial and true 2D/no-motion layouts without state loss.

Engineering target: zero known presentation/contract ambiguity before Windows migration. Literal zero debugging cannot be guaranteed for real MT5/Windows integration.
