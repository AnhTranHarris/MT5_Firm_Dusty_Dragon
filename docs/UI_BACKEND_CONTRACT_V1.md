# Dusty Dragon UI Backend Contract v1

Status: **Frozen for UI design**

This contract separates presentation from trading authority. The website and PC application may display the same firm truth, but only the PC application receives narrowly scoped operational controls. Neither presentation layer owns capital authority.

## 1. Shared read boundary

Both interfaces consume `FirmExecutionReadService`.

The service composes broker-neutral desk status providers into immutable layer and firm snapshots and can emit a JSON-safe payload. Presentation code must not read MetaTrader5 objects, SQLite connections, repositories, transports, or authorization leases directly.

Every firm payload includes `contract_version: "1"`. Layers are ordered numerically and desks inside a layer are ordered by `desk_id`, so frontend rendering does not depend on runtime/provider registration order.

### Desk operational fields

`DemoExecutionStatus` currently exposes:

- desk/account/broker identity
- account environment
- observation timestamp
- balance, equity, and free margin
- MT5 session open/fault state and fault reason
- whether native demo-write capability was enabled at stack construction
- unresolved execution count
- derived `execution_ready`

`execution_ready` is an operational safety signal, not a profitability score. A desk with attractive P&L remains not ready when its terminal session is faulted or an execution outcome is unresolved.

### Layer and firm aggregates

`LayerExecutionStatus` and `FirmExecutionStatus` expose reporting sums and operational counts. Balance/equity/free-margin sums are reporting values only and never imply capital transfer, netting, or shared buying power between desks.

## 2. Website interface authority

The website is read-only.

Allowed dependency:

`FirmExecutionReadService -> FirmExecutionStatus / JSON-safe payload`

Forbidden website dependencies include:

- `DemoOperatorService`
- `DemoLeaseExecutionService`
- authorization repositories or leases
- MT5 runtime/session/write modules
- `ExecutionTransport`
- broker write methods
- any LIVE execution enablement

The website may visualize status, performance, risk, alerts, and drill-down information supplied by read models, but it cannot issue operational or trading commands.

## 3. PC interface authority

The PC application may consume the same read service and additionally use `DemoOperatorService`.

The v1 operator command set is deliberately limited to:

- `SHUTDOWN_EXECUTION`
- `REQUEST_SESSION_REBUILD`

A rebuild request closes the current stack and signals that the host must construct a new verified stack. It does not auto-reconnect or clear a latched session fault in place.

There is no command to:

- enable LIVE execution
- enable native broker writes
- place a trade
- create an `ApprovedOrder`
- issue or consume an authorization lease
- override risk, portfolio, reconciliation, broker-health, or pending-execution vetoes

## 4. Trading authority remains below the UI

The capital-sensitive path remains owned by Dusty Core:

`OrderIntent -> sovereign authorization -> audit -> short-lived single-use lease -> session validation -> demo execution gates -> MT5 validation/preflight -> broker submission -> audit -> reconciliation`

UI code may request approved operational actions through application services, but must never bypass or reimplement that path.

## 5. MT5 session failure semantics

An MT5 demo session binds to one expected login and independently verifies DEMO environment and trading permissions. The first observed terminal/account fault latches the session unhealthy and closes it. Recovery requires a new `MT5DemoSession` and full revalidation.

The UI should therefore present latched faults as requiring rebuild/recovery, not as transient warnings that disappear automatically.

## 6. Performance analytics extension

The operational contract is ready for UI design. Additional Myfxbook/ForexFactory-style performance and quant analytics should be added as new read-model fields/services backed by real historical data; presentation code must not calculate authoritative trading metrics from incomplete client-side data.

The UI design session may now define the required performance panels, time horizons, charts, tables, alerts, and drill-down dimensions. Those requirements can then extend the read side without changing execution authority.

## 7. Versioning rule

Changes that expand UI authority, expose broker/runtime objects, weaken DEMO-only execution controls, alter the meaning of `execution_ready`, or make a breaking payload change require an explicit contract-version change and constitutional QC review.
