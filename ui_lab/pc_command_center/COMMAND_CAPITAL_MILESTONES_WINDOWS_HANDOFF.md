# Dusty Dragon Command Capital Milestones — Windows Handoff

Status: UI-Lab planning/read-model contract. This panel is a quick-reference planning surface, not execution authority and not a promise of returns.

## Purpose

The Command Center left rail uses otherwise-empty space beneath `RESEARCH DELTA` for a compact firm-capital reference:

- daily realized-gain goal;
- weekly realized-gain goal;
- expected trade count to cumulative realized-gain milestones of $10,000, $50,000, $100,000, and $50,000,000.

## UI-Lab calculations

The mock currently uses the explicit hierarchy daily target (`dailyTargetPct`) as a firm planning reference. Daily realized-gain goal is current firm equity multiplied by that daily rate. Weekly goal is the five-trading-day geometric equivalent of the same rate.

Expected trades use a static dollar-expectancy estimate derived from the mock win rate, average win, and average loss:

```text
expectancyUsdPerTrade = winRate * avgWin - lossRate * abs(avgLoss)
expectedTradesToGoal = cumulativeGainGoal / expectancyUsdPerTrade
```

Round the displayed trade count upward because a fractional trade cannot complete a milestone.

## Critical semantics

These values are **planning references only**. They must never:

- authorize larger position size;
- relax a risk gate;
- force trading merely to hit a target;
- be presented as guaranteed or forecast profits;
- infer live realized P&L from equity changes;
- assume the current edge remains constant indefinitely.

The $50M value is a cumulative realized-gain milestone, not an account-balance claim and not a time forecast.

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
milestones[]:
  gainGoalUsd
  expectedTrades (nullable)
provenance
calculationVersion
```

If expectancy is zero, negative, stale, or statistically unavailable, the UI should show `UNAVAILABLE` rather than a nonsensical or infinite trade count.

## Future model improvements

The current static expectancy count intentionally does not model compounding, changing position size, regime changes, fees beyond the current input statistics, capacity constraints, drawdowns, capital additions/withdrawals, or uncertainty. A production forecasting model may add confidence intervals and scenario bands, but only after explicit quantitative review. Keep the simple planning reference visually distinct from any future probabilistic forecast.

## Windows QC

Test positive/zero/negative expectancy; missing target policy; large gain milestones; large and negative dollar P&L values; 100/125/150/200% scaling; forced colors; stale snapshots; mixed-version rejection; and layout at minimum supported Command Center height.

Engineering target: zero known presentation/contract ambiguity before migration. Literal zero debugging cannot be guaranteed for live MT5/Windows integration.
