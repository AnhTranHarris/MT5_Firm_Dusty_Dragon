(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  if (!data?.performance) return;

  /*
   * UI-LAB PERFORMANCE HISTORY
   * --------------------------
   * These are explicit simulated history points for UX validation only.
   * They are not reconstructed from MTD/WTD values and are not forecasts.
   * Production replaces this entire file with the canonical performance read model.
   */
  data.performance.asOfUtc = "2026-08-28T21:44:00Z";
  data.performance.historyProvenance = "MOCK_SIMULATED";
  data.performance.horizonSeries = {
    month: [
      { atUtc: "2026-08-01T00:00:00Z", cumulativeReturnPct: 0.00 },
      { atUtc: "2026-08-04T21:00:00Z", cumulativeReturnPct: 1.20 },
      { atUtc: "2026-08-07T21:00:00Z", cumulativeReturnPct: 1.80 },
      { atUtc: "2026-08-10T21:00:00Z", cumulativeReturnPct: 1.40 },
      { atUtc: "2026-08-13T21:00:00Z", cumulativeReturnPct: 2.60 },
      { atUtc: "2026-08-16T21:00:00Z", cumulativeReturnPct: 2.10 },
      { atUtc: "2026-08-19T21:00:00Z", cumulativeReturnPct: 3.00 },
      { atUtc: "2026-08-22T21:00:00Z", cumulativeReturnPct: 2.70 },
      { atUtc: "2026-08-25T21:00:00Z", cumulativeReturnPct: 3.50 },
      { atUtc: "2026-08-27T21:00:00Z", cumulativeReturnPct: 3.10 },
      { atUtc: "2026-08-28T21:44:00Z", cumulativeReturnPct: 3.82 }
    ],
    quarter: [
      { atUtc: "2026-07-01T00:00:00Z", cumulativeReturnPct: 0.00 },
      { atUtc: "2026-07-08T21:00:00Z", cumulativeReturnPct: 1.10 },
      { atUtc: "2026-07-15T21:00:00Z", cumulativeReturnPct: 2.05 },
      { atUtc: "2026-07-22T21:00:00Z", cumulativeReturnPct: 2.92 },
      { atUtc: "2026-07-31T21:00:00Z", cumulativeReturnPct: 4.08 },
      { atUtc: "2026-08-07T21:00:00Z", cumulativeReturnPct: 5.21 },
      { atUtc: "2026-08-14T21:00:00Z", cumulativeReturnPct: 5.88 },
      { atUtc: "2026-08-21T21:00:00Z", cumulativeReturnPct: 7.14 },
      { atUtc: "2026-08-28T21:44:00Z", cumulativeReturnPct: 8.06 }
    ],
    year: [
      { atUtc: "2025-10-01T00:00:00Z", cumulativeReturnPct: 0.00 },
      { atUtc: "2025-10-31T21:00:00Z", cumulativeReturnPct: 2.85 },
      { atUtc: "2025-11-30T21:00:00Z", cumulativeReturnPct: 5.42 },
      { atUtc: "2025-12-31T21:00:00Z", cumulativeReturnPct: 8.91 },
      { atUtc: "2026-01-31T21:00:00Z", cumulativeReturnPct: 11.37 },
      { atUtc: "2026-02-28T21:00:00Z", cumulativeReturnPct: 13.84 },
      { atUtc: "2026-03-31T21:00:00Z", cumulativeReturnPct: 17.26 },
      { atUtc: "2026-04-30T21:00:00Z", cumulativeReturnPct: 20.08 },
      { atUtc: "2026-05-31T21:00:00Z", cumulativeReturnPct: 24.31 },
      { atUtc: "2026-06-30T21:00:00Z", cumulativeReturnPct: 28.77 },
      { atUtc: "2026-07-31T21:00:00Z", cumulativeReturnPct: 32.60 },
      { atUtc: "2026-08-28T21:44:00Z", cumulativeReturnPct: 37.60 }
    ],
    fiveYear: [
      { atUtc: "2021-10-01T00:00:00Z", cumulativeReturnPct: 0.00 },
      { atUtc: "2022-03-31T21:00:00Z", cumulativeReturnPct: 8.40 },
      { atUtc: "2022-09-30T21:00:00Z", cumulativeReturnPct: 18.20 },
      { atUtc: "2023-03-31T21:00:00Z", cumulativeReturnPct: 31.60 },
      { atUtc: "2023-09-30T21:00:00Z", cumulativeReturnPct: 47.90 },
      { atUtc: "2024-03-31T21:00:00Z", cumulativeReturnPct: 61.50 },
      { atUtc: "2024-09-30T21:00:00Z", cumulativeReturnPct: 82.70 },
      { atUtc: "2025-03-31T21:00:00Z", cumulativeReturnPct: 109.40 },
      { atUtc: "2025-09-30T21:00:00Z", cumulativeReturnPct: 143.80 },
      { atUtc: "2026-03-31T21:00:00Z", cumulativeReturnPct: 179.30 },
      { atUtc: "2026-08-28T21:44:00Z", cumulativeReturnPct: 214.60 }
    ]
  };
})();
