# Dusty Dragon PC Command Center — UI Lab

This directory is an intentionally isolated, static UX laboratory for the Dusty Dragon PC interface.

## Purpose

- Refine layout, visual hierarchy, navigation, interaction, and JARVIS-inspired spatial concepts before production frontend work.
- Exercise the frozen UI Backend Contract v1 conceptually without coupling this prototype to MT5, SQLite, execution transports, authorization leases, or broker credentials.
- Discover which additional authoritative server-side analytics are actually worth implementing.

## Safety / authority boundary

This prototype uses local mock data only. It has no backend client, no network calls, no broker integration, and no trading authority.

The only command concepts represented are the two commands currently permitted by the frozen PC UI contract:

- `SHUTDOWN_EXECUTION`
- `REQUEST_SESSION_REBUILD`

In this laboratory they only open confirmation dialogs and append a local mock audit event. They do not call Dusty Core.

## Run

Open `index.html` directly in a modern browser. No build step and no runtime dependencies are required.

## Current interaction model

- Workspace tabs: Command, Trading, Risk, Performance, Research, Layer 0 Lab, System.
- `F2`: Analytical mode — replaces the spatial Trading Floor with a hierarchy tree.
- `F3`: Spatial mode — restores the JARVIS-inspired 3D Trading Floor.
- Dusty Dragon Core is the root solar system. DEMO and L1-L4 are its orbiting portfolio layers.
- Inside a production layer, the portfolio is the center orb and six seeded desks orbit it.
- A gold Saturn-like orb with subtle green rings is the next-layer bridge; the rings use front/back occlusion so they wrap around the gold sphere rather than reading as a flat ellipse.
- The top-left CORE cube returns to the Dusty Dragon Core system.
- The top-right DEMO cube opens the hidden Demo solar system.
- CORE and DEMO rotate independently around the Y axis at deliberately different slow periods. Hover changes face glow only; it never changes the 3D transform hierarchy.
- OS reduced-motion preference no longer silently freezes Spatial mode. Spatial mode retains only an ultra-slow orientation cue; `F2` remains the explicit zero-spatial-motion fallback.
- Click an orbiting desk for its detailed mock performance page; click a center portfolio orb for aggregate performance.
- Command buttons remain segregated in the PC-only Command Authority zone.

## Trading workspace

The Trading workspace includes a quantitative **Trading Lens** that can switch among:

- Firm — analytical aggregation of all active desks.
- Portfolio — Demo, Generalist, Trading Style, Sector, or Symbol portfolio scope.
- Desk — seeded individual desk scope across the hierarchy.

The selected lens exposes mock balance/equity, 24-hour P&L, MTD return, maximum drawdown, profit factor, Sharpe, open risk, margin utilization, gross exposure, open positions, win rate, expectancy, broker/account/environment context, and filtered positions/decision telemetry. These are UX placeholders only; production values must come from authoritative historical and execution data.

## UX audit notes

- 3D is used for topology, navigation, and attention; exact financial values remain 2D.
- The analytical hierarchy tree remains a complete fallback when spatial effects are disabled.
- Orbit velocity decreases by 15% for each successively more distant orbit.
- Presentation state remains separate from trading authority and cannot mutate broker or execution state.
- The generic button hover shadow is explicitly disabled for spatial cubes; only cube-face outlines/glow respond to hover.
- Obsolete JavaScript revisions and the superseded cube stylesheet were removed during cleanup. The retained stylesheet chain is still active and must not be deleted until the lab is flattened into canonical production assets.

## Design doctrine

1. 3D shows relationships.
2. 2D shows exact numbers.
3. Motion shows change.
4. Color shows state.
5. Geometry shows structure.
6. The audit ledger remains authoritative.

The lab should remain disposable. Production frontend code should not depend on it.
