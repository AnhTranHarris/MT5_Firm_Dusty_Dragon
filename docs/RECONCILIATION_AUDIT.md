# Constitution Reconciliation Audit

Scope: legacy implementation branches vs Dusty Dragon Financial Constitution v1.

Status labels: KEEP_CONCEPT, REWRITE, DEPRECATE, REMOVE, MIGRATE_LATER.

## Executive conclusion

The legacy implementation is preserved as historical engineering evidence but is not the policy source of truth. The rebuild starts from `main` because the default branch contains only the initial README, while the substantial legacy system exists on development/feature branches.

The legacy code has useful algorithms and tests, but it mixes earlier assumptions with newer components. Reusing modules wholesale would risk silent constitutional conflicts. Algorithms may be selectively ported only after contract tests prove compliance with the new v1 domain boundaries.

## Confirmed legacy conflicts

### Corporate expansion threshold
Legacy roadmap behavior encoded a materially different sponsorship model, including approximately $500,000 sustained/average-equity concepts. Current constitution replaces this with the Live Desk Capital Chain Gate: every existing live desk must independently maintain >= $5,000 closing equity for seven consecutive valid trading days, remain healthy, and pass portfolio/system checks before a Sunday expansion request.

Disposition: REMOVE old threshold logic; REWRITE expansion from v1 policy.

### Fixed style hierarchy
Legacy implementation used a predetermined style set that included Scalping and breadth-first style/sector/symbol assumptions.

Current constitution: nine active style candidates compete for six Layer-2 slots; Scalping is hardware-deferred; selection is empirical and must pass Layer-0 validation. Layer 3 is broker-dependent and may contain qualified duplicate sectors with enforced sibling variation.

Disposition: REMOVE fixed taxonomy from runtime logic; REWRITE as data-driven candidate registry.

### Portfolio semantics
Legacy portfolio/firm analytics can be useful, but current v1 constitution explicitly prohibits capital sharing and defines portfolio state as an analytical/risk overlay only.

Disposition: KEEP_CONCEPT calculations only; REWRITE ownership/authority contracts.

## Legacy subsystem disposition

### analytics/capital_growth.py
Potential value: return/growth calculations.
Disposition: KEEP_CONCEPT; port only after definitions distinguish realized P&L, unrealized P&L, and external capital flows.

### analytics/performance.py
Potential value: risk-adjusted metrics.
Disposition: KEEP_CONCEPT; rebuild formulas under canonical result schemas and explicit missing-data handling.

### analytics/firm_health.py
Potential value: health aggregation.
Disposition: REWRITE. New design requires cause-aware Desk -> Layer -> Firm -> Infrastructure propagation, not a single generic health score.

### backtest/campaign_evaluator.py
Potential value: repeated experiment evaluation.
Disposition: KEEP_CONCEPT; port behind immutable dataset/provenance contract and holdout firewall.

### backtest/walk_forward.py
Potential value: walk-forward validation.
Disposition: KEEP_CONCEPT; port later with frozen dataset hashes and versioned policy references.

### backtest/weekend_protocol.py
Potential value: scheduled deep research.
Disposition: REWRITE around current nightly/Saturday research constitution, Resource Governor priorities, and anti-overfitting partitions.

### brokers/contracts.py
Potential value: broker-neutral typed contracts.
Disposition: KEEP_CONCEPT; rebuild into v1 canonical Instrument, InstrumentSpec, QuoteTick, MarketBar, AccountSnapshot, PositionSnapshot, OrderEvent, ExecutionFill.

### brokers/mt5_adapter.py
Potential value: MT5 connectivity and normalization.
Disposition: MIGRATE_LATER. Do not copy until canonical schemas, broker truth/reconciliation rules, and ApprovedOrder boundary are implemented.

### brokers/volume.py
Potential value: conservative volume rounding.
Disposition: KEEP_CONCEPT; rewrite so broker minimum lot can never force an upward risk violation.

### intelligence/kronos_bridge.py and kronos_forecast.py
Potential value: contractor integration and forecast evidence.
Disposition: MIGRATE_LATER. Kronos remains evidence-only and must conform to ContractorManifest + ForecastEvidence v1.

### intelligence/research_signal.py
Potential value: research evidence translation.
Disposition: REWRITE. Research can influence OrderIntent but may never create ApprovedOrder.

### knowledge/institutional.py
Potential value: persistent observations, validation, provenance, freshness.
Disposition: KEEP_CONCEPT / MIGRATE_LATER. Preserve the principle that observations require independent reproduction and authority can age/stale.

### knowledge/research_bridge.py, verification_handler.py, verification_work.py
Potential value: reproducible evidence routing.
Disposition: KEEP_CONCEPT; port after new KnowledgeLifecycle and durable job contracts exist.

### learning/challenger_evaluator.py
Potential value: incumbent/challenger comparison.
Disposition: REWRITE using v1 Layer-0-only challenge authority, seven-day baseline, 30-day campaign, 90-day different-layer interval, hard gates before weighted scoring, and no auto-promotion.

### learning/holding_maturity.py
Potential value: holding-period graduation.
Disposition: REWRITE from Desk Graduation v1. Holding authority is additive and risk-first position sizing remains independent.

### learning/promotion_gate.py
Potential value: promotion workflow.
Disposition: REWRITE. New promotion gates require immutable policy versions and explicit human/firm authority boundaries.

### learning/strategy_lineage.py
Potential value: lineage/provenance.
Disposition: KEEP_CONCEPT; integrate into immutable strategy/evidence records.

### organization/*
Potential value: recursive organization and expansion notices.
Disposition: REWRITE. Legacy fixed hierarchy/financial thresholds conflict with current Layer-2 competition, Layer-3 broker-aware selection, six-desk portfolio qualification, and Live Desk Capital Chain Gate.

### legacy configuration
Disposition: REMOVE as authority. All consequential thresholds move to versioned policy files.

### legacy tests
Disposition: MIGRATE_SELECTIVELY. Tests that prove generic math/data correctness may be ported. Tests asserting superseded policy values/hierarchy must not be retained as expected behavior.

## New source-of-truth order

1. `docs/CONSTITUTION.md`
2. versioned files under `policies/`
3. typed domain models and state machines
4. executable constitutional tests
5. runtime implementation
6. selectively ported legacy algorithms after compatibility tests

If runtime code conflicts with the Constitution or active policy version, runtime code is wrong.

## Rebuild rule

No legacy source file is copied wholesale into the clean branch. Each desired capability must be reintroduced through a narrow v1 interface, with tests proving authority, accounting, reproducibility, and failure behavior before migration.
