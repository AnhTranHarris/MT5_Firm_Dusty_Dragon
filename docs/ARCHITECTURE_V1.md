# Dusty Dragon Software Architecture v1

Status: AUTHORITATIVE REBUILD TARGET

## System mission

Dusty Dragon is a PC-first proprietary trading firm platform that coordinates MT5 execution, independent trading desks, institutional research, replaceable specialist contractors, and recursive organizational growth under one deterministic governance core.

## Core architecture

Human CEO
-> Website (read/observe only)
-> PC Command Center (high-authority human control)
-> Dusty Dragon Core (sovereign runtime authority)
-> Risk / Portfolio / Lifecycle / Capital Governance
-> ApprovedOrder boundary
-> Execution contractor / MT5 gateway

Research contractors (Vibe-type, Kronos-type, Qlib, LEAN, future tools) produce evidence only.

## Process boundaries

1. Dusty Core: native Python application/service.
2. MT5 Gateway: native Windows isolated process/environment.
3. Nautilus or equivalent execution engine: isolated runtime behind Dusty approval boundary.
4. Kronos-type forecasting: separate Python process/environment.
5. Vibe-type research: separate process/environment; MCP/HTTP may be used for research tooling only.
6. Qlib-type research: separate process/environment.
7. LEAN: isolated Docker validation contractor when resources permit.
8. Website API: read-only capability surface.
9. PC Command API: privileged local capability surface.

## Canonical transport/storage

- Control messages: JSON initially; MessagePack may be added for local efficiency.
- Bulk tabular data: Apache Parquet with Arrow-compatible schemas.
- Durable firm state/metadata/audit: SQLite.
- Local service transport: localhost HTTP/IPC initially.
- Heavy contractors: separate OS processes; Docker only where justified.
- All timestamps canonicalized to UTC while preserving broker/server-time metadata.

## Canonical domain objects

Instrument
InstrumentSpec
MarketBar
QuoteTick
TradeTick
AccountSnapshot
PositionSnapshot
OrderIntent
RiskAssessment
ApprovedOrder
OrderEvent
ExecutionFill
ForecastEvidence
ResearchEvidence
BacktestResult
RegimeState
EvidenceProvenance
ContractorJob
ContractorResult
DeskState
CohortState
LayerState
PortfolioState
ChallengeCampaign
KnowledgeRecord
CapitalFlow
AuditEvent
Incident
ExpansionRequest

## Non-negotiable type firewall

ForecastEvidence / ResearchEvidence / BacktestResult
-> may influence OrderIntent
-> cannot create ApprovedOrder

OrderIntent
-> Desk Risk
-> Portfolio Risk
-> Capital Authority
-> ApprovedOrder
-> execution adapter
-> MT5

No contractor has capital_authority=true.

## Contractor manifest contract

Every runtime contractor declares:
- name/version/git SHA
- role/capabilities
- accepted input schema versions
- produced output schema versions
- runtime type/language
- resource class
- timeout/heartbeat policy
- network permission
- market/account data permissions
- broker-access permission
- capital authority (always NONE)

Contractor health states:
STARTING, HEALTHY, DEGRADED, UNAVAILABLE, FAILED, STOPPING.

## Resource Governor

PC-first priority hierarchy:
P0_CRITICAL: risk, MT5 account state, integrity, emergency governance
P1_LIGHT: audit/state writes, monitoring
P2_MODERATE: live/demo desk runtimes, normal execution support
P3_HEAVY: Kronos/Vibe/Qlib research, substantial backtests
P4_EXCLUSIVE: LEAN, large optimization, deep validation

P0 never waits for P3/P4. Heavy research is paused/queued before execution or risk is degraded.

## Data ownership

SQLite = institutional ledger / metadata / governance state.
Parquet = raw and normalized market data, frozen experiment datasets, fills, large backtest/research outputs.

Immutable experiment identity includes:
strategy SHA + dataset SHA + contractor version + policy version + configuration + random seed.

## Financial identity model

Dusty Desk ID is permanent and independent of broker account number.
A desk may have multiple account generations over time.
Demo account expiration/replacement never erases desk lineage or institutional evidence.

Capital flows are recorded independently from trading P&L.

## Lifecycle state machines

DeskLifecycle:
NEW, BOOTSTRAPPING, INTRADAY, HOLD_2D, MULTIDAY, WEEKLY, MULTIWEEK, CAUTION, DEFENSIVE, HALTED, QUARANTINED, REHABILITATING, REQUALIFYING.

CohortLifecycle:
FORMING, FROZEN, TESTING, PASSED, FAILED, INVALID.

LayerLifecycle:
FORMING, ACTIVE, FILLED, BASELINING, QUALIFIED, CHALLENGE_ELIGIBLE, UNDER_CHALLENGE, EXPANSION_ELIGIBLE, RESTRICTED, QUARANTINED.

KnowledgeLifecycle:
OBSERVED, PEER_TESTING, VALIDATED, REJECTED, AGING, STALE.

ChallengeLifecycle:
INELIGIBLE, BASELINING, ELIGIBLE, BLIND_RESEARCH, INFORMED_RESEARCH, FORWARD_TEST, REVIEW, INCUMBENT_WIN, DRAW, CHALLENGER_WIN, VALIDATING, PROMOTION_CANDIDATE, CLOSED.

## Interfaces

Website:
read-only reporting for firm/layer/desk P&L, equity, drawdown, risk, exposure, attribution, research, challenge status, contractor health, broker health, PC health, qualification, and audit history.

PC Command Center:
all website visibility plus privileged actions such as pause/resume/halt, emergency liquidation, firm kill switch, contractor enable/disable, research controls, MT5 account registration, policy-change workflow, challenge/expansion approval workflow, and incident acknowledgement.

Backend authorization must reject capital-sensitive write commands from the website capability surface even if a UI defect attempts them.

## Recursive organization

Layer 0: Demo laboratory/proof cohort.
Layer 1: Live Generalists.
Layer 2: six evidence-selected styles from nine active candidates.
Layer 3: broker-aware style x sector specialists; duplicates permitted with enforced sibling variation.
Future deeper specialization may include symbol-level branches without changing the core recursive model.

Every live layer uses the same PortfolioGovernor interface and recursive expansion law.

## Implementation packages

src/dusty_dragon/
  core/
  domain/
  policies/
  capital/
  risk/
  desks/
  portfolio/
  lifecycle/
  organization/
  challenges/
  knowledge/
  contractors/
  brokers/
  data/
  scheduler/
  interfaces/
  audit/

Tests mirror the domain boundaries and constitutional invariants.
