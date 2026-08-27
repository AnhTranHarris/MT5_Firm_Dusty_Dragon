window.DUSTY_MOCK = {
  contractVersion: "1",
  generatedAt: "2026-08-27T06:31:42-05:00",
  firm: {
    name: "Dusty Dragon",
    state: "OPERATIONAL",
    balance: 27418.22,
    equity: 27371.11,
    freeMargin: 25182.44,
    pnl24h: 318.72,
    pnlMonthPct: 3.82,
    monthlyTargetPct: 5.0,
    drawdownPct: 1.14,
    openRiskPct: 2.17,
    unresolvedExecutions: 0
  },
  services: [
    ["CAPITAL", "NORMAL"],
    ["EXECUTION", "NORMAL"],
    ["RISK", "CAUTION"],
    ["DATA", "NORMAL"],
    ["RESEARCH", "DEGRADED"],
    ["INFRA", "NORMAL"]
  ],
  desks: [
    { id: "G01", state: "NORMAL", equity: 6172.14, today: 0.44, mtd: 4.32, dd: 0.86, pf: 1.82, sharpe: 1.44, risk: 0.72 },
    { id: "G02", state: "NORMAL", equity: 5841.33, today: 0.81, mtd: 4.08, dd: 1.21, pf: 1.71, sharpe: 1.36, risk: 0.88 },
    { id: "G03", state: "NORMAL", equity: 5104.08, today: 0.12, mtd: 3.31, dd: 1.48, pf: 1.56, sharpe: 1.19, risk: 0.63 },
    { id: "G04", state: "CAUTION", equity: 4978.41, today: -0.31, mtd: 2.12, dd: 5.13, pf: 1.12, sharpe: 0.78, risk: 1.24 },
    { id: "G05", state: "NORMAL", equity: 5275.20, today: 0.21, mtd: 3.72, dd: 1.09, pf: 1.63, sharpe: 1.27, risk: 0.75 },
    { id: "G06", state: "FAULT", equity: 0, today: 0, mtd: 0, dd: 0, pf: 0, sharpe: 0, risk: 0 }
  ],
  incidents: [
    { severity: "CRITICAL", title: "G06 session fault latched", detail: "Broker connectivity recovered; execution remains blocked until a verified session rebuild." },
    { severity: "RISK", title: "USD concentration elevated", detail: "Four desks currently share meaningful USD downside exposure. Three valid opportunities were rejected." },
    { severity: "WATCH", title: "G04 entered CAUTION", detail: "Rolling drawdown reached 5.13%. Desk remains active under reduced new-risk authority." }
  ],
  overnight: [
    ["00:12", "Research batch started"],
    ["00:41", "Kronos forecast batch completed"],
    ["01:03", "EURUSD candidate rejected — portfolio capacity"],
    ["01:17", "G02 entered XAUUSD"],
    ["02:31", "G04 drawdown entered CAUTION"],
    ["03:44", "G02 XAUUSD closed +1.31R"],
    ["04:58", "MT5 G06 disconnect"],
    ["04:59", "G06 session fault LATCHED"],
    ["05:01", "Broker recovered; execution remained BLOCKED"],
    ["05:37", "Holdout batch 14/16 passed"],
    ["06:31", "CEO session opened"]
  ],
  research: {
    completed: 17,
    promoted: 3,
    rejected: 8,
    active: 6,
    challengeDay: 11,
    challengeLength: 30,
    holdoutPass: 14,
    holdoutTotal: 16
  },
  rejected: {
    total: 14,
    deskRisk: 3,
    portfolioCapacity: 4,
    correlation: 2,
    evidence: 2,
    executionUnsafe: 1,
    cost: 2,
    avoidedLoss: 183,
    missedProfit: 91
  }
};