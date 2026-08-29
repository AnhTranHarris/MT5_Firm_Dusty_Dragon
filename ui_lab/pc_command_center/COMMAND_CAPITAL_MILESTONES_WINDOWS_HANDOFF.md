# Dusty Dragon Command Capital Milestones — Windows Handoff

Status: UI-Lab planning/read-model contract. This panel is a quick-reference planning surface, not execution authority and not a promise of returns.

## Command left-rail priority

The left rail is intentionally ordered by operator value:

1. **FIRM EVENT TIMELINE** — only the five most recent events classified by Core as materially affecting a Desk's trading/execution/risk state.
2. **RESEARCH DELTA** — compact research throughput/status.
3. **CAPITAL MILESTONES** — the remaining vertical area, optimized for comfortable human reading.

Timeline and Research Delta line spacing should be compact but never overlapping. Reclaim padding/leading there before reducing milestone typography.

The UI-Lab timeline still uses fixture-text matching because legacy events are plain `[time, message]` arrays. Production must use explicit event metadata (`scopeType`, `scopeId`, `category`, `severity`, `operatorImpact`, `occurredAtUtc`, `snapshotVersion`). The five-row limit is presentation only; full audit history remains immutable in Core/persistence.

## Capital milestone surfaces

The Command Center shows:

- daily realized-gain goal;
- weekly realized-gain goal;
- the next three **rolling cumulative realized-gain milestones**;
- monthly realized-gain goals of **$5,000, $10,000, and $15,000**, with remaining expected trades from current recognized MTD realized gain;
- a separate **FIRM MASTER GAIN GOAL** of $50,000,000 with 1Y / 5Y / 10Y / 20Y planning horizons.

## Rolling milestone ladder

The current explicit UI-Lab ladder is:

```text
$10K -> $50K -> $100K -> $500K -> $1M -> $5M -> $10M -> $50M
```

The UI always shows the next three unachieved milestones. Once Core's recognized cumulative realized gain meets or exceeds a milestone, that milestone disappears and the next ladder value moves into the quick view. The ladder is explicit and bounded; the UI must never invent a larger target after $50M.

The $50M endpoint remains separately governed as the master goal even when it also becomes the next rolling milestone.

## Monthly realized-gain goals

The monthly quick line is fixed at $5K / $10K / $15K in the current mock contract. For each target:

```text
remainingMonthlyGain = max(0, monthlyGoal - recognizedMonthRealizedGain)
expectedTradesRemaining = remainingMonthlyGain / expectancyUsdPerTrade
```

When `remainingMonthlyGain == 0`, display `MET`, not a negative or zero-trade estimate. Production policy may change these monthly targets only through an explicit versioned configuration/read model.

## UI-Lab planning fixture

`capital-planning-mock-v33.js` is explicit simulated planning data. It exists so the UI does **not** infer recognized realized gain from equity changes or generic Net P&L. It provides:

- recognized cumulative realized trading gain;
- recognized MTD realized trading gain;
- milestone ladder;
- monthly gain goals.

Delete/replace this fixture when Core supplies the production planning snapshot.

## Trade expectancy reference

The mock uses static dollar expectancy from win rate, average win, and average loss:

```text
expectancyUsdPerTrade = winRate * avgWin - lossRate * abs(avgLoss)
expectedTradesToGoal = remainingRealizedGain / expectancyUsdPerTrade
```

Round displayed trade count upward. If expectancy is zero, negative, stale, or unavailable, show `UNAVAILABLE` rather than an infinite or misleading count.

Trade-count estimates are planning references only. They must never force trading frequency, authorize larger size, or relax risk gates.

## Daily / weekly goals

The mock uses explicit `dailyTargetPct`. Daily realized-gain goal is current firm equity × daily rate. Weekly goal is the five-trading-day geometric equivalent. These are planning references, not execution quotas.

## $50M horizon mathematics

Target terminal equity is current equity + $50,000,000 recognized realized trading gain:

```text
requiredAnnualRate = (targetTerminalEquity / currentEquity)^(1 / years) - 1
requiredMonthlyRate = (1 + requiredAnnualRate)^(1 / 12) - 1
```

These are mathematical requirements, not forecasts.

## Master-goal horizon restrictions

- **1 YEAR — RESTRICTED.** Scenario/research reference only; no leverage, risk, drawdown, trade-frequency, or execution-policy override.
- **5 YEARS — RESTRICTED** when required monthly performance is more than 2× the current firm monthly objective. Explicit master-policy review required.
- **10 YEARS — STRETCH** when required monthly performance exceeds the current objective but is not above the 2× threshold.
- **20 YEARS — POLICY RANGE** only when the required monthly rate is within the current firm objective. This does not imply probability or guarantee.

## Hard recognition restrictions

Recognized gain must be **realized trading gain only**. Exclude deposits, withdrawals, credits, demo resets, broker corrections, inter-account transfers, and other external capital flows.

Neither ordinary milestones, monthly goals, nor the master goal may authorize larger position size/leverage, relax risk/drawdown limits, force minimum trade count, override broker/session/reconciliation safety, convert planning horizons into deadlines, or count external capital as trading gain.

## Production read model

Core should supply one immutable planning snapshot, for example:

```text
snapshotVersion
asOfUtc
firmEquity
recognizedCumulativeRealizedGainUsd
recognizedMonthRealizedGainUsd
dailyTargetPct (nullable)
dailyRealizedGoalUsd (nullable)
weeklyRealizedGoalUsd (nullable)
expectancyUsdPerTrade (nullable)
expectancySampleTrades
expectancyWindowStartUtc
expectancyWindowEndUtc
monthlyObjectivePct (nullable)
rollingMilestoneLadder[]
monthlyGainGoals[]
nextMilestones[]:
  gainGoalUsd
  remainingGainUsd
  expectedTradesRemaining (nullable)
masterGoal:
  gainGoalUsd
  recognizedRealizedGainUsd
  expectedTradesRemaining (nullable)
  horizons[]:
    years
    requiredMonthlyPct
    requiredAnnualPct
    policyState
    policyReason
provenance
calculationVersion
```

Core owns capital-flow classification, realized-gain recognition, milestone advancement, and production expectancy. WebView2 formats immutable values and must not reconstruct authoritative gain from equity deltas.

## Windows QC

Test: newest-five event ordering; full audit retention; compact non-overlapping timeline/research spacing; milestone transitions exactly at 10K/50K/100K/500K/1M/5M/10M/50M; monthly goal states below/at/above 5K/10K/15K; positive/zero/negative expectancy; deposits/withdrawals around boundaries; stale/mixed snapshots; master horizon calculations; 100/125/150/200% scaling; forced colors/high contrast; and minimum supported Command Center height.

Engineering target: zero known presentation/contract ambiguity before migration. Literal zero debugging cannot be guaranteed for live MT5/Windows integration.
