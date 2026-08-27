# Dusty Dragon PC Command Center — UI Lab v1

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

## Interaction model

- Workspace tabs: Command, Trading, Risk, Performance, Research, Lab, System.
- `F2`: Analytical mode — flattens animation and spatial effects.
- `F3`: Spatial mode — restores the JARVIS-inspired presentation.
- Click desk nodes in the Firm Core to focus a desk dossier.
- Click incidents, metrics, and panels to reveal secondary detail.
- Command buttons are intentionally segregated into the PC-only Command Authority zone.

## Design doctrine

1. 3D shows relationships.
2. 2D shows exact numbers.
3. Motion shows change.
4. Color shows state.
5. Geometry shows structure.
6. The audit ledger remains authoritative.

The lab should remain disposable. Production frontend code should not depend on it.