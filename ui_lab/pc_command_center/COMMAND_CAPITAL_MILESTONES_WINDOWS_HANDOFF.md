# Dusty Dragon Command Capital Milestones — Windows Handoff

Status: UI-Lab planning/read-model contract. This panel is a quick-reference planning surface, not execution authority.

## Command left-rail priority
1. **FIRM EVENT TIMELINE** — five newest major Desk-impact events.
2. **RESEARCH DELTA** — compact research throughput/status.
3. **CAPITAL MILESTONES** — remaining vertical area for readable planning references.

Timeline/Research spacing may compress before financial typography. System-wide typography is governed by `SYSTEM_PANEL_TYPOGRAPHY_WINDOWS_HANDOFF.md`.

## Capital milestone surfaces
The Command Center shows daily/weekly realized references, the next three rolling cumulative realized-gain milestones, **average weekly income goals reviewed quarterly**, and a ratcheting **FIRM MASTER GAIN GOAL**.

## Rolling cumulative milestone ladder
Initial UI-Lab ladder:
```text
$10K -> $50K -> $100K -> $500K -> $1M -> $5M -> $10M -> $50M
```
The UI shows the next three unachieved values. Core owns recognized realized gain and advancement.

## Average weekly income goals — quarterly cadence
The planning concept is average recognized realized trading income **per completed trading week**, evaluated over a quarter.

Initial series:
```text
$5K/wk -> $10K/wk -> $15K/wk -> $20K/wk -> $25K/wk -> $30K/wk ->
$40K/wk -> $50K/wk -> $75K/wk -> $100K/wk
```
During a quarter:
```text
quarterWeeklyAverage = recognizedQuarterRealizedGain / completedTradingWeeksInQuarter
```
Targets do not change intra-quarter. At the quarter boundary, a qualified quarter advances exactly one tier; otherwise the same tier remains active.

## Trade expectancy reference
```text
expectancyUsdPerTrade = winRate * avgWin - lossRate * abs(avgLoss)
expectedTradesToGoal = remainingGain / expectancyUsdPerTrade
```
If expectancy is non-positive, stale, or unavailable, Core returns the count as unavailable.

## Daily / weekly reference goals
The existing daily target percentage and five-day geometric weekly reference remain separate from the quarterly average-income ladder.

## Firm Master Gain Goal ratchet
Initial master recognized realized-gain goal: **$50M**. After Core verifies that the active master goal has been reached and maintained at/above that watermark for one additional year, the next active master goal increases by **$25M**:
```text
$50M -> $75M -> $100M -> $125M -> ...
```
The rule repeats for every subsequent master level.

## Master-goal horizon requirements
Each 1Y / 5Y / 10Y / 20Y cell shows three complementary planning rates for the current active master goal:

```text
requiredAnnualRate = (targetTerminalEquity / currentEquity)^(1 / years) - 1
requiredMonthlyRate = (1 + requiredAnnualRate)^(1 / 12) - 1
requiredWeeklyRate = (1 + requiredAnnualRate)^(1 / 52) - 1
averageWeeklyGainUsd = remainingRecognizedGainToMaster / (years * 52)
```

`requiredWeeklyRate` is the compounded weekly return rate mathematically consistent with the horizon. `averageWeeklyGainUsd` is a simple average realized-gain pace showing how many recognized dollars per week would need to be added, on average, over that horizon. They are intentionally shown together because they answer different operator questions: rate-of-growth versus dollar-income pace.

When the master goal ratchets upward, all four horizon cells must recalculate both weekly values against the new active goal. Production Core should supply these figures in the immutable planning snapshot; WebView2 should not authoritatively recompute them.

The UI does not display a verbose master-goal warning paragraph. Risk/execution governance remains enforced elsewhere by Core.

## Recognition semantics
Only Core-recognized realized trading gain should advance cumulative milestones, quarterly weekly-income averages, or the master goal. Capital-flow classification remains a Core/ledger responsibility.

## Production read model
Core should supply one immutable planning snapshot containing at minimum:
```text
snapshotVersion
asOfUtc
firmEquity
recognizedCumulativeRealizedGainUsd
recognizedQuarterRealizedGainUsd
completedTradingWeeksInQuarter
quarterId
quarterReviewState
weeklyIncomeGoalSeries[]
activeWeeklyIncomeTierIndex
activeWeeklyIncomeGoalUsd
quarterWeeklyAverageUsd
nextQuarterWeeklyIncomeGoalUsd
expectancyUsdPerTrade (nullable)
rollingMilestoneLadder[]
nextMilestones[]
masterGoal:
  activeGainGoalUsd
  incrementUsd
  reachedAtUtc (nullable)
  maintenanceYearsRequired
  maintenanceSatisfied
  nextGainGoalUsd
  horizons[]:
    years
    requiredWeeklyPct
    averageWeeklyGainUsd
    requiredMonthlyPct
    requiredAnnualPct
    policyState
provenance
calculationVersion
```

## Windows QC
Test quarter boundaries, tier met/not met, no multi-tier skipping, stale snapshots, realized-gain reconciliation, master goal reached but not maintained, maintenance exactly one year, falling below watermark during maintenance, repeated $25M ratchets, weekly/monthly/annual horizon math, dollar-per-week horizon pace, horizon recalculation after a ratchet, positive/zero/negative expectancy, DPI 100/125/150/200%, forced colors/high contrast, and minimum Command Center height.

Engineering target: zero known presentation/contract ambiguity before migration. Literal zero debugging cannot be guaranteed for live MT5/Windows integration.
