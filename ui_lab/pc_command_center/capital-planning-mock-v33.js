(() => {
  "use strict";

  /* UI-LAB ONLY. These are explicit planning fixtures so the presentation layer
     never mislabels equity changes or generic Net P&L as recognized realized gain. */
  window.DUSTY_CAPITAL_PLANNING_MOCK = Object.freeze({
    contractVersion:"UI_LAB_CAPITAL_PLANNING_1",
    provenance:"MOCK_CAPITAL_PLANNING_SIMULATED",
    asOfUtc:window.DUSTY_MOCK?.performance?.asOfUtc || "2026-08-29T20:30:00Z",
    recognizedRealizedGainUsd:3297.04,
    monthRecognizedRealizedGainUsd:3297.04,
    milestonePattern:Object.freeze([10_000,50_000,100_000,500_000,1_000_000,5_000_000,10_000_000,50_000_000]),
    monthlyGainGoals:Object.freeze([5_000,10_000,15_000])
  });
})();