# Dusty Dragon Executable Policy / Test Matrix v1

This matrix converts the Financial Constitution into release-blocking behavior. Items marked IMPLEMENTED are already represented by tests in the clean rebuild. Items marked NEXT become tests before their runtime subsystem is introduced.

| ID | Constitutional invariant | Expected result | Status |
|---|---|---|---|
| C001 | A cohort earns credit only when every admitted desk passes | One FAIL or INVALID => zero cohort credit | IMPLEMENTED |
| C002 | Layer-0 counted desk must reach at least MULTIDAY | Lower graduation => zero cohort credit | IMPLEMENTED |
| C003 | Live expansion requires every existing desk independently >= $5,000 for 7 valid closes | $4,999.99 on any qualifying close blocks/reset eligibility | IMPLEMENTED |
| C004 | Aggregate equity cannot subsidize an under-threshold desk | $7K + $3K does not qualify two desks | IMPLEMENTED |
| C005 | Halted/quarantined/incident desk cannot sponsor expansion | Expansion denied | IMPLEMENTED |
| C006 | Order needs Desk Risk PASS and Portfolio Risk PASS | Either gate fails => no ApprovedOrder | IMPLEMENTED |
| C007 | Sunday demo compression is external flow | 75% target calculated separately from trading P&L | IMPLEMENTED |
| C008 | Demo account replacement does not restart bootstrap age | Persistent desk lineage retains forward-day count | NEXT |
| C009 | Demo risk widening applies only to selected non-catastrophic forward limits | Catastrophic/evidence/governance limits unchanged | NEXT |
| C010 | Historical backtests never use demo 110% risk exemption | Standard funded policy used | NEXT |
| C011 | Broker minimum lot may not force upward risk violation | Return NO_TRADE when min lot exceeds risk budget | NEXT |
| C012 | Capital transfers between desks are prohibited | Any transfer command rejected and audited | NEXT |
| C013 | External deposits/withdrawals never alter trading P&L | CapitalFlow and TradingPnL remain separate | NEXT |
| C014 | Portfolio rejection cannot contaminate strategy-quality stats | VALID_SIGNAL + PORTFOLIO_CAPACITY_REJECTED | NEXT |
| C015 | Portfolio target 5% cannot alter risk limits or force trades | No policy path from target shortfall to risk escalation | NEXT |
| C016 | Desk 25% stretch target cannot alter risk limits or force trades | No catch-up/leverage path | NEXT |
| C017 | Catastrophic desk loss causes quarantine and revokes graduation | Reset authority to Level 0 after rehabilitation | NEXT |
| C018 | Idiosyncratic desk failure does not automatically quarantine healthy siblings | Failed desk isolated | NEXT |
| C019 | Systemic correlated failure can escalate layer/firm state | Cause-aware escalation | NEXT |
| C020 | Research evidence cannot create ApprovedOrder | Type/capability boundary denies direct conversion | NEXT |
| C021 | Website capability surface cannot issue capital-sensitive writes | Authorization denied even if request is forged | NEXT |
| C022 | PC Command Center requires privileged local authorization | Unauthorized command denied/audited | NEXT |
| C023 | Layer 0 is sole formal challenge authority | Other layers denied | NEXT |
| C024 | Full live layer receives 7-day baseline before challenge | Early campaign creation denied | NEXT |
| C025 | Formal challenge lasts 30 valid trading days | Incomplete evidence cannot win | NEXT |
| C026 | Different-layer challenge obeys 90-trading-day interval | Scheduler denies premature switch | NEXT |
| C027 | Raw-return-only challenger cannot win through excessive risk | Hard gates execute before weighted score | NEXT |
| C028 | Challenge win never auto-deploys production change | Creates PromotionCandidate only | NEXT |
| C029 | Layer-2 top-six ranking alone is insufficient | Candidate must exceed quality floor + Layer-0 validation | NEXT |
| C030 | Scalping remains hardware-deferred until capability policy changes | Not active candidate on current hardware profile | NEXT |
| C031 | Layer-3 selection derives from Broker Opportunity Map | Unsupported sector cannot be invented | NEXT |
| C032 | Duplicate Layer-3 siblings require >=20% meaningful variation | Insufficient structural/behavioral variation rejected | NEXT |
| C033 | Functional duplicates are not treated as diversification | High behavior overlap triggers duplicate state | NEXT |
| C034 | Hardware pressure reduces concurrency, not six-proof rigor | Required pass count remains 6 | NEXT |
| C035 | P0 safety work cannot be starved by P3/P4 research | Resource Governor preempts/throttles research | NEXT |
| C036 | Experiment reproduction identity is immutable | Strategy SHA + dataset SHA + contractor + policy + config + seed stored | NEXT |
| C037 | Knowledge requires independent reproduction before VALIDATED | Self-validation denied | NEXT |
| C038 | Stale knowledge loses normal decision authority but remains historical | Retrieval policy filters stale authority | NEXT |
| C039 | MT5 account ID is not permanent desk identity | Account rotation preserves Dusty desk lineage | NEXT |
| C040 | Contractors are version-pinned; runtime never floats on latest | Unapproved version denied | NEXT |

## Release rule

A subsystem may not move from design into production-capable code until all matrix rows applicable to that subsystem are executable tests and green in CI.

Capital-safety and authority tests are release blockers and cannot be marked xfail, skipped, or downgraded solely to make a release pass.
