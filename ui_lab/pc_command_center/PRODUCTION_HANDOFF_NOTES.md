# Dusty Dragon UI Lab — Production Handoff Notes

These notes preserve implementation decisions discovered while prototyping so the lab can later be translated into production code without re-solving the same classes of problems.

## Source hierarchy for the future Windows application

Use sources in this order when implementing the real application:

1. **MetaQuotes / MQL5 official documentation** for terminal initialization, account/session verification, terminal paths, permissions, and portable-mode behavior.
2. **Microsoft Learn / Win32 documentation** for process discovery, registry-based installed-application discovery, hardware inventory, performance counters, process creation, and job/process lifecycle management.
3. **Dusty Dragon's certified backend contracts/tests** for authority, account verification, latched-session semantics, risk, reconciliation, and execution rules.
4. **GitHub repositories/community examples** only as implementation references, never as authority over MetaQuotes/Microsoft contracts.
5. **Reddit/community reports** only as diagnostic leads. Never apply registry/system changes from community posts automatically.

## Verified MetaQuotes / MQL5 implementation breadcrumbs

### Bind Python to an explicit terminal

Official `MetaTrader5.initialize()` supports an explicit terminal executable path and optional `login`, `password`, `server`, `timeout`, and `portable` arguments. MetaQuotes notes that if the path is omitted the module attempts to locate a terminal itself, but the exact search algorithm is not disclosed. **Production Dusty should therefore prefer explicit executable paths after discovery to avoid ambiguous multi-terminal binding.**

Reference:
- https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- https://www.mql5.com/en/book/advanced/python/python_init

Future shape (illustrative only; do not copy credentials into source):

```python
# Production sketch — credentials come from secure runtime storage.
ok = mt5.initialize(
    terminal.exe_path,
    login=account.login,
    server=account.server,
    timeout=60_000,
    portable=terminal.portable,
)
if not ok:
    raise TerminalProvisioningError(mt5.last_error())
```

`initialize()` may launch the selected terminal if required. Treat that as process provisioning, **not authorization to trade**.

### Verify terminal identity after connection

`mt5.terminal_info()` exposes terminal status/settings including connection state, trade permission, build, ping, company/name, terminal `path`, terminal `data_path`, and common data path. Use this to prove that the terminal Dusty connected to is the terminal it intended to connect to.

References:
- https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py
- https://www.mql5.com/en/docs/constants/environment_state/terminalstatus
- https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo/cterminalinfopath
- https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo/cterminalinfodatapath

Production verification must compare observed terminal/account facts with the assigned desk contract before execution eligibility is possible. Important facts include at least:

- executable/terminal path;
- terminal data path;
- terminal build/version;
- connected state;
- broker/company/server identity;
- account identity;
- DEMO vs LIVE environment;
- terminal trade permission / API-disabled state;
- Dusty's own session-latch and authorization state.

### Portable and non-portable instances are different identities

MetaQuotes documents `portable=True` in `initialize()` and exposes `TERMINAL_PATH` / `TERMINAL_DATA_PATH`. An older official MQL5 article also demonstrates that `/portable` changes data-path behavior. Therefore terminal inventory must not deduplicate only on `terminal64.exe` filename. The durable identity should include **normalized executable path + data path + portable mode**, with broker/account identity layered on only after verification.

References:
- https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
- https://www.mql5.com/en/docs/files
- https://www.mql5.com/en/articles/2552

## Verified Microsoft / Windows implementation breadcrumbs

### Discover candidate MT5 installations conservatively

Do not recursively crawl the entire drive on every startup. Build a bounded candidate set from multiple sources, then validate candidates:

1. Known assignments already stored by Dusty.
2. Running processes (`terminal64.exe` / terminal process image paths).
3. Windows application-registration locations where applicable.
4. Windows Installer uninstall registration where applicable.
5. User-approved custom/portable directories.
6. Optional bounded fallback search in common program locations.

Microsoft documents `App Paths` under HKCU/HKLM as a preferred executable registration mechanism and documents MSI uninstall registration under `...CurrentVersion\\Uninstall`. Not every broker installer is guaranteed to use either mechanism, so registry discovery is a **candidate source, not completeness proof**.

References:
- https://learn.microsoft.com/en-us/windows/win32/shell/app-registration
- https://learn.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key

Never trust a registry string alone. Canonicalize the path, verify the file exists, inspect version/signature metadata where useful, and then prove the terminal through MetaQuotes APIs before assignment becomes READY.

### Inspect running MT5 processes without destructive control

Microsoft `Get-Process` / `System.Diagnostics.Process` exposes PID, working set, accumulated CPU time, start time, executable/module information, etc. A production native helper can use Win32/.NET directly rather than spawning PowerShell repeatedly.

Reference:
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-process

Recommended durable runtime key:

```text
TerminalInstanceKey = normalized_exe_path + normalized_data_path + portable_flag
RuntimeProcessKey    = TerminalInstanceKey + PID + process_start_time
```

Never use PID alone as durable identity because PIDs are reused.

### Hardware/system telemetry

Microsoft exposes Windows performance information through performance counters/PDH and memory APIs. `Win32_VideoController` can inventory display adapters, but Microsoft warns some properties can be inaccurate on non-WDDM hardware. Static hardware identity and live telemetry therefore need separate collectors.

References:
- https://learn.microsoft.com/en-us/windows/win32/perfctrs/collecting-performance-data
- https://learn.microsoft.com/en-us/windows/win32/perfctrs/performance-counters-functions
- https://learn.microsoft.com/en-us/windows/win32/memory/memory-performance-information
- https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-videocontroller

Do **not** poll heavy WMI/CIM queries at animation/UI cadence. Static inventory can refresh rarely; live CPU/RAM/disk/process counters should use efficient sampled telemetry with rolling p50/p95/p99 statistics.

### Process creation / lifecycle

If the native application eventually launches terminals itself, use an explicit executable path and quoted/structured command arguments. Microsoft documents ambiguity/security concerns around executable path parsing in `CreateProcess`. A higher-level Windows process API is acceptable if it preserves explicit-path semantics.

Reference:
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessa

Windows Job Objects may be useful for grouping processes started by Dusty and observing lifecycle/resource behavior, but do **not** use a job object's bulk termination capability as a capacity-shedding shortcut. A trading terminal can only be released after the desk is broker-safe and Dusty's reconciliation/session state allows it.

Reference:
- https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects

## GitHub/community findings retained

- Keep production hardware inventory, terminal discovery, capacity policy, presentation state, and broker/execution authority as separate modules/services. The current UI-lab capacity/provisioning split deliberately prototypes that boundary.
- Public GitHub code search shows multiple projects explicitly passing terminal paths to `mt5.initialize()` and using separate/portable installations. These are useful examples to inspect during implementation, but they are not substitutes for MetaQuotes documentation.
- Search example retained: `mt5.initialize(path portable terminal64` returned projects such as `bbstrader` and Windows/portable MT5 utilities. Re-evaluate current code at implementation time rather than vendoring snippets blindly.
- Continue requiring CI on `dev/**`; frontend/native additions should gain their own tests instead of relying only on the existing Python backend suite.

## Reddit/community findings retained — diagnostic only

Community experience agrees that separate MT5 installations/directories are commonly used for simultaneous accounts. A MetaTrader subreddit thread describes users installing additional MT5 instances into distinct folders. This supports the UX assumption that multiple discoverable terminal instances are realistic, but it is **not** an official capacity guarantee.

Reference:
- https://www.reddit.com/r/metatrader/comments/1denbb4/

A 2025 Reddit report describes an apparent ~18-terminal ceiling on one Windows Server setup and attributes it to desktop-heap pressure, including a manual `SharedSection` registry change. Treat this only as a troubleshooting hypothesis if a future machine shows a similar symptom. **Dusty must never automatically modify desktop-heap registry values or promise a fixed MT5-instance maximum.** Capacity is empirical and machine/session specific.

Reference:
- https://www.reddit.com/r/metatrader/comments/1nwqad6/

Python/Windows community reports also note that repeatedly creating WMI/OpenHardwareMonitor connections can itself create meaningful monitoring overhead. This reinforces Dusty's design: cache collectors, sample at bounded intervals, and make the monitoring subsystem part of the resource budget.

References:
- https://www.reddit.com/r/learnpython/comments/gkxp4q/
- https://www.reddit.com/r/learnpython/comments/iocc3q/

## MT5 provisioning contract discovered during UX design

1. One active Dusty desk = one broker MT5 account = one running terminal instance.
2. First launch may operate normally with one valid Demo desk. Missing D02-D06 are `NOT PROVISIONED`, not failures.
3. Layer-0 eligibility for Layer 1 requires six independently qualifying Demo proofs. Those proofs may be accumulated sequentially when hardware or Demo-account availability prevents six concurrent terminals.
4. MT5 discovery and MT5 assignment are separate operations.
5. Production discovery must run through a constrained local Windows service/helper. A browser UI must not receive arbitrary filesystem authority.
6. A discovered terminal is not trusted merely because `terminal64.exe` exists. Inventory must include executable path and resolved terminal data path; process, broker/server, account, environment, assignment, verification, and last-seen state are layered on as evidence becomes available.
7. Human assignment means **attempt provisioning** only. Existing verification must still validate account identity, server, DEMO/LIVE environment, permissions, session state, and all execution prerequisites.
8. Auto capacity activates `min(provisioned eligible desks, proven-safe PC capacity)`. Powerful hardware never manufactures missing desks.
9. Capacity contraction sheds newest/deepest desks first. Established/core desks have priority.
10. A desk with open positions, unresolved execution, pending reconciliation, or other broker obligations cannot be terminated for capacity reasons. It enters `DRAINING`; new exposure may be blocked, but the MT5 instance remains until obligations are safe.
11. `CAPACITY-PARKED` preserves desk identity, performance history, lineage, evidence, broker configuration, and institutional memory. It is not deletion or failure.
12. Machine-capacity metrics estimate what can be supervised concurrently. They never authorize a trade or bypass risk/portfolio controls.
13. Terminal discovery may be automatic; assignment remains human-confirmed until a later explicitly reviewed policy says otherwise.
14. Never infer DEMO/LIVE solely from installation folder names, broker branding, or account-number format. Use authoritative connected-account/session facts.

## Suggested production module boundaries

```text
windows_inventory/
  static_hardware.py        # rare-refresh CPU/GPU/RAM/storage/OS inventory
  performance_sampler.py    # bounded live CPU/RAM/disk/network/process telemetry

mt5_inventory/
  candidate_discovery.py    # registry/process/known/custom-path candidates
  terminal_probe.py         # explicit mt5.initialize(path=...), terminal_info()
  terminal_registry.py      # durable TerminalInstanceKey + assignment state

capacity/
  sampler.py                # rolling observations
  model.py                  # empirical safe envelope, hysteresis, reserve
  desk_scheduler.py         # oldest/core-first activate, newest/deepest shed
  drain_coordinator.py      # blocks release until broker/execution obligations safe

provisioning/
  requests.py               # desk requires terminal/account
  verification.py           # broker/account/env/permissions/session contract
  assignment.py             # human-confirmed mapping, no execution authority

ui/
  system_viewmodel.py       # read-only snapshots + narrowly scoped user intents
```

Keep credentials completely outside these inventory/view-model objects.

## Production capacity telemetry target

Replace mock coefficients with rolling empirical telemetry. Recommended inputs include CPU saturation/per-core pressure, RAM working set, paging, disk latency, MT5 process responsiveness, data-feed latency, broker heartbeat latency, execution/reconciliation queue latency, database-write latency, GUI pressure, network stability, and thermal throttling. Prefer p95/p99 and multi-day/weekly evidence over one instantaneous reading.

Capacity learning should use **hysteresis**: do not activate/park desks every time a metric crosses one threshold for one sample. Require sustained evidence and preserve a meaningful reserve. A weekly proven-safe ceiling can rise cautiously after stable evidence and fall more quickly when latency/pressure violations occur.

## Important boundary

This file is an engineering handoff note, not an implementation of real MT5 discovery. Before live integration, re-check the linked documentation for current semantics, then add dedicated Windows integration tests, multi-terminal MT5 tests, and failure-injection tests. The current HTML lab performs no filesystem, MT5, broker, registry, process-control, or network calls.