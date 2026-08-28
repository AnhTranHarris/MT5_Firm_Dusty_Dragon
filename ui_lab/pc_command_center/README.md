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
- Both navigation cubes rotate visibly around the Y axis and label their physical faces rather than using a stationary overlay label.
- Click an orbiting desk for its detailed mock performance page; click a center portfolio orb for aggregate performance.
- Command buttons remain segregated in the PC-only Command Authority zone.

## UX audit notes

- 3D is used for topology, navigation, and attention; exact financial values remain 2D.
- The analytical hierarchy tree remains a complete fallback when spatial effects are disabled.
- Orbit velocity decreases by 15% for each successively more distant orbit.
- Presentation state remains separate from trading authority and cannot mutate broker or execution state.
- Obsolete JavaScript revisions were removed from the active lab during the current cleanup pass; retained versioned stylesheets remain because the active stylesheet import chain depends on them.

## Design doctrine

1. 3D shows relationships.
2. 2D shows exact numbers.
3. Motion shows change.
4. Color shows state.
5. Geometry shows structure.
6. The audit ledger remains authoritative.

The lab should remain disposable. Production frontend code should not depend on it.
