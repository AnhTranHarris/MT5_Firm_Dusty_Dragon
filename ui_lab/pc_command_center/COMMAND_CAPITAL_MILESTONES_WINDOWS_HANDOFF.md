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
This replaces the previous monthly $5K/$10K/$15K interpretation. The planning concept is average recognized realized trading income **per completed trading week**, evaluated over a quarter.

Initial series:
```text
$5K/wk -> $10K/wk -> $15K/wk -> $20K/wk -> $25K/wk -> $30K/wk ->
$40K/wk -> $50K/wk -> $75K/wk -> $100K/wk
```
The first three values preserve the user's original 5K/10K/15K pattern. The UI displays the active tier plus the next two reference tiers.

During a quarter:
```text
quarterWeeklyAverage = recognizedQuarterRealizedGain / completedTradingWeeksInQuarter
```
Targets **do not change intra-quarter**. At the quarter boundary, if the completed quarter's weekly average meets or exceeds the active tier, the next quarter advances **one tier**. A very strong quarter does not skip multiple tiers. If the active tier is not met, the next quarter retains the same tier. Production Core owns the quarter boundary, completed-week count, recognized gain, and tier state; WebView2 only formats the snapshot.

This makes the goal a stable quarterly planning reference rather than a target that moves every week.

## Trade expectancy reference
Expected-trade counts remain a planning aid:
```text
expectancyUsdPerTrade = winRate * avgWin - lossRate * abs(avgLoss)
expectedTradesToGoal = remainingGain / expectancyUsdPerTrade
```
If expectancy is non-positive, stale, or unavailable, Core returns the count as unavailable.

## Daily / weekly reference goals
The existing daily target percentage and five-day geometric weekly reference remain separate from the quarterly average-income ladder. Do not conflate the two concepts.

## Firm Master Gain Goal ratchet
Initial master recognized realized-gain goal: **$50M**.

After Core verifies that the active master goal has been reached, it records `masterGoalReachedAtUtc`. The active master goal does **not** increase immediately. The firm must remain at or above that recognized realized-gain watermark for one additional year. Once that maintenance period completes, the next active master goal increases by **$25M**:
```text
$50M -> $75M -> $100M -> $125M -> ...
```
The same rule repeats for every subsequent master level: reach the active goal, maintain it for one additional year, then ratchet by $25M. Production should store the active master goal and its reached/maintenance timestamps explicitly rather than infer historical maintenance from the current value alone.

The 1Y/5Y/10Y/20Y horizon math is recalculated against the current active master goal. The UI does not display a verbose master-goal warning paragraph; this is understood as a general planning-goal surface. Risk/execution governance remains enforced elsewhere by Core regardless of whether warning prose is visible.

## Recognition semantics
Only Core-recognized realized trading gain should advance cumulative milestones, quarterly weekly-income averages, or the master goal. Capital-flow classification remains a Core/ledger responsibility. This rule belongs in the contract and audit layer rather than occupying Command Center screen space.

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
  horizons[]
provenance
calculationVersion
```

## Windows QC
Test quarter boundaries, partial first/last trading weeks, zero completed weeks, tier met/not met, no multi-tier skipping, top tier behavior, stale snapshots, realized-gain reconciliation, master goal reached but not maintained, maintenance exactly one year, falling below watermark during maintenance, $25M repeated ratchets, horizon recalculation, positive/zero/negative expectancy, DPI 100/125/150/200%, forced colors/high contrast, and minimum Command Center height.

Engineering target: zero known presentation/contract ambiguity before migration. Literal zero debugging cannot be guaranteed for live MT5/Windows integration.
