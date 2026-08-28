# Dusty Dragon UI Lab — Production Handoff Notes

These notes preserve implementation decisions discovered while prototyping so the lab can later be translated into production code without re-solving the same classes of problems.

## Frontend / GitHub findings retained

- GitHub recommends using CI to provide confidence through automated tests and making the intended use of maintained actions/components clear. Dusty already keeps the UI lab under `dev/**`, so every committed prototype slice continues through the repository's normal CI rather than bypassing QC.
  - https://docs.github.com/en/actions/how-tos/create-and-publish-actions/release-and-maintain-actions
- GitHub recommends decoupling independently maintained reusable actions/components where appropriate. For Dusty, the analogous production principle is separation of hardware inventory, terminal discovery, capacity policy, presentation state, and broker/execution authority rather than one monolithic UI process.
  - https://docs.github.com/en/actions/how-tos/create-and-publish-actions/manage-custom-actions
- Community frontend guidance consistently favors clear separation of view state, business rules, external/network integration, and tests. The UI lab therefore exposes a tiny capacity API instead of allowing provisioning code to reach inside the capacity panel's DOM implementation.
- Community canvas implementations repeatedly warn against rendering hidden surfaces and rebuilding DOM on every animation frame. Dusty's animation governor already reduces hidden/background Trading Floor cadence and should remain part of the production performance doctrine.

## MT5 provisioning contract discovered during UX design

1. One active Dusty desk = one broker MT5 account = one running terminal instance.
2. First launch may operate normally with one valid Demo desk. Missing D02-D06 are `NOT PROVISIONED`, not failures.
3. Layer-0 eligibility for Layer 1 requires six independently qualifying Demo proofs. Those proofs may be accumulated sequentially when hardware or Demo-account availability prevents six concurrent terminals.
4. MT5 discovery and MT5 assignment are separate operations.
5. Production discovery must run through a constrained local Windows service/helper. A browser UI must not receive arbitrary filesystem authority.
6. A discovered terminal is not trusted merely because `terminal64.exe` exists. Inventory should eventually include executable path, terminal data path, process identity, broker/server, account identity, environment, assignment state, and last-seen state.
7. Human assignment means "attempt provisioning" only. Dusty's existing verification path must still validate account identity, server, DEMO/LIVE environment, permissions, session state, and all execution prerequisites.
8. Auto capacity activates `min(provisioned eligible desks, proven-safe PC capacity)`. Powerful hardware never manufactures missing desks.
9. Capacity contraction sheds newest/deepest desks first. Established/core desks have priority.
10. A desk with open positions, unresolved execution, pending reconciliation, or other broker obligations cannot be terminated for capacity reasons. It enters `DRAINING`; new exposure may be blocked, but the MT5 instance remains until obligations are safe.
11. `CAPACITY-PARKED` preserves the desk's identity, performance history, lineage, evidence, broker configuration, and institutional memory. It is not deletion or failure.
12. Machine capacity metrics estimate what can be supervised concurrently. They never authorize a trade or bypass risk/portfolio controls.

## Production capacity telemetry target

Replace mock coefficients with rolling empirical telemetry. Recommended inputs include CPU saturation/per-core pressure, RAM working set, paging, disk latency, MT5 responsiveness, data-feed latency, broker heartbeat latency, execution/reconciliation queue latency, database-write latency, GUI pressure, network stability, and thermal throttling. Prefer p95/p99 and multi-day/weekly evidence over one instantaneous reading.

## Important boundary

This file is an engineering handoff note, not an implementation of real MT5 discovery. Before live integration, verify Windows/MetaTrader-specific discovery semantics against authoritative platform documentation and add dedicated tests. The current HTML lab performs no filesystem, MT5, broker, or network calls.
