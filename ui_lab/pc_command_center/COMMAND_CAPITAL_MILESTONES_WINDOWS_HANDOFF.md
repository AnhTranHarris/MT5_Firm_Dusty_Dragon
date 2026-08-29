# Dusty Dragon Command Capital Milestones — Windows Handoff

Status: UI-Lab planning/read-model contract. This panel is a quick-reference planning surface, not execution authority and not a promise of returns.

## Purpose

The Command Center left rail uses otherwise-empty space beneath `RESEARCH DELTA` for a compact firm-capital reference:

- daily realized-gain goal;
- weekly realized-gain goal;
- expected trade count to ordinary cumulative realized-gain milestones of $10,000, $50,000, and $100,000;
- a visually separate **FIRM MASTER GAIN GOAL** of $50,000,000 with 1Y / 5Y / 10Y / 20Y planning horizons.

The $50M master goal must never be presented as just another row in the ordinary milestone grid.

## UI-Lab calculations

The mock currently uses the explicit hierarchy daily target (`dailyTargetPct`) as a firm planning reference. Daily realized-gain goal is current firm equity multiplied by that daily rate. Weekly goal is the five-trading-day geometric equivalent of the same rate.

Expected trades use a static dollar-expectancy estimate derived from the mock win rate, average win, and average loss:

```text
expectancyUsdPerTrade = winRate * avgWin - lossRate * abs(avgLoss)
expectedTradesToGoal = cumulativeGainGoal / expectancyUsdPerTrade
```

Round displayed trade count upward because a fractional trade cannot complete a milestone.

For the $50M horizon reference, the target terminal equity is current firm equity plus $50,000,000 cumulative realized trading gain. Required rates are geometric:

```text
requiredAnnualRate = (targetTerminalEquity / currentEquity)^(1 / years) - 1
requiredMonthlyRate = (1 + requiredAnnualRate)^(1 / 12) - 1
```

These are mathematical requirements, not forecasts or approved performance targets.

## Master-goal horizon restrictions

The horizon labels are policy warnings, not execution permissions.

- **1 YEAR — RESTRICTED.** Scenario/research reference only. It may never justify leverage, risk-limit, drawdown-limit, trade-frequency, or execution-policy overrides.
- **5 YEARS — RESTRICTED** when required monthly performance is more than 2× the current firm monthly objective. Requires explicit master-policy review before it can ever become an operating objective. No target-driven risk escalation.
- **10 YEARS — STRETCH** when required monthly performance exceeds the current firm monthly objective but is not above the 2× threshold. It remains a planning scenario; existing risk and drawdown policy remain unchanged.
- **20 YEARS — POLICY RANGE** only when the required monthly rate is mathematically within the current firm monthly objective. This does not make the outcome probable, forecast, or guaranteed.

These labels are intentionally derived from the relationship between required compounded rate and current firm objective. Production may replace the thresholds only through an explicit versioned policy contract.

## Hard restrictions for $50M goal recognition

A $50M master-goal achievement counter must recognize **realized trading gain only**. It must exclude deposits, withdrawals, credits, demo resets, broker corrections, inter-account transfers, and other external capital flows.

The master goal must never:

- authorize larger position size or leverage;
- relax daily/portfolio/desk risk limits;
- relax drawdown or loss limits;
- force trades, minimum trade count, or target-chasing behavior;
- override broker/session/reconciliation safety;
- convert a planning horizon into a deadline;
- count external capital additions as trading gain;
- assume a static edge, constant capacity, or uninterrupted compounding.

If a horizon requires returns outside current policy, the UI must show that conflict rather than silently changing policy.

## Production ownership

In the Windows application, Core should supply an immutable planning read model instead of allowing WebView2 to become authoritative for these calculations. Suggested fields:

```text
snapshotVersion
asOfUtc
firmEquity
dailyTargetPct (nullable)
dailyRealizedGoalUsd (nullable)
weeklyRealizedGoalUsd (nullable)
expectancyUsdPerTrade (nullable)
expectancySampleTrades
expectancyWindowStartUtc
expectancyWindowEndUtc
monthlyObjectivePct (nullable)
standardMilestones[]:
  gainGoalUsd
  expectedTrades (nullable)
masterGoal:
  gainGoalUsd
  recognizedRealizedGainUsd
  expectedTrades (nullable)
  horizons[]:
    years
    requiredMonthlyPct
    requiredAnnualPct
    policyState
    policyReason
provenance
calculationVersion
```

Core owns capital-flow classification and recognized realized-gain accumulation. The UI may format the supplied values but must not reconstruct authoritative gain from equity deltas.

If expectancy is zero, negative, stale, or statistically unavailable, show `UNAVAILABLE`. If objective policy is missing, horizon policy state must be `UNASSESSED`, not inferred.

## Critical semantics

All values are **planning references only**. The $50M value is cumulative realized trading gain, not an account-balance promise, valuation claim, or deadline. Horizon rates describe what compounding mathematics would require from the current starting equity; they do not estimate probability of success.

## Windows QC

Test positive/zero/negative expectancy; missing target/objective policy; deposits and withdrawals around milestone boundaries; large external capital flows; gain reconciliation; 1/5/10/20-year rate calculations; threshold boundaries; stale/mixed snapshots; long numeric values; 100/125/150/200% scaling; forced colors/high contrast; and minimum supported Command Center height.

Engineering target: zero known presentation/contract ambiguity before migration. Literal zero debugging cannot be guaranteed for live MT5/Windows integration.
