(() => {
  "use strict";

  /* UI-LAB ONLY. Explicit planning fixtures keep planning targets separate from
     equity movement and generic Net P&L. Production values belong to Core. */
  window.DUSTY_CAPITAL_PLANNING_MOCK = Object.freeze({
    contractVersion:"UI_LAB_CAPITAL_PLANNING_2",
    provenance:"MOCK_CAPITAL_PLANNING_SIMULATED",
    asOfUtc:window.DUSTY_MOCK?.performance?.asOfUtc || "2026-08-29T20:30:00Z",
    recognizedRealizedGainUsd:3297.04,
    monthRecognizedRealizedGainUsd:3297.04,
    quarterRecognizedRealizedGainUsd:3297.04,
    milestonePattern:Object.freeze([10_000,50_000,100_000,500_000,1_000_000,5_000_000,10_000_000,50_000_000]),

    /* Average weekly realized-income goals are reviewed only at quarter
       boundaries. The next quarter advances one tier only after the current
       quarter's realized weekly average meets the active tier. */
    weeklyIncomeGoalSeries:Object.freeze([5_000,10_000,15_000,20_000,25_000,30_000,40_000,50_000,75_000,100_000]),
    activeWeeklyIncomeTierIndex:0,
    completedTradingWeeksInQuarter:1,
    quarterReviewCadence:"QUARTERLY",

    /* Master goal ratchets by $25M only after the active master goal has first
       been reached and then remained at/above that recognized realized-gain
       watermark for one additional year. */
    masterGoalBaseUsd:50_000_000,
    masterGoalIncrementUsd:25_000_000,
    masterGoalReachedAtUtc:null,
    masterGoalMaintenanceYearsRequired:1
  });
})();