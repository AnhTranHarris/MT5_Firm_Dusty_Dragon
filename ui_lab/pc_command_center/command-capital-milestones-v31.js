(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const leftStack = document.querySelector("#command .left-stack");
  if (!data || !leftStack) return;

  const stats = new Map((data.performance?.stats || []).map(([label,value]) => [label,value]));
  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g,""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  const money = value => value == null ? "—" : Number(value).toLocaleString(undefined, {
    style:"currency", currency:"USD", maximumFractionDigits:0
  });
  const integer = value => value == null ? "—" : Math.ceil(Number(value)).toLocaleString();

  const equity = numberFrom(data.firm?.equity);
  const dailyTargetPct = numberFrom(data.hierarchy?.dailyTargetPct) ?? 0.23;
  const dailyRate = dailyTargetPct / 100;
  const weeklyRate = Math.pow(1 + dailyRate, 5) - 1;
  const dailyGoal = equity == null ? null : equity * dailyRate;
  const weeklyGoal = equity == null ? null : equity * weeklyRate;

  const winRate = numberFrom(stats.get("Win rate"));
  const avgWin = numberFrom(stats.get("Avg Win"));
  const avgLoss = Math.abs(numberFrom(stats.get("Avg Loss")) ?? 0);
  const expectancyDollars = winRate == null || avgWin == null || avgLoss == null
    ? null
    : (winRate / 100) * avgWin - (1 - winRate / 100) * avgLoss;

  const goals = [
    { label:"$10K", amount:10_000 },
    { label:"$50K", amount:50_000 },
    { label:"$100K", amount:100_000 },
    { label:"$50M", amount:50_000_000 }
  ];

  const tradesFor = amount => expectancyDollars != null && expectancyDollars > 0
    ? amount / expectancyDollars
    : null;

  const panel = document.createElement("article");
  panel.className = "panel compact capital-milestones-panel";
  panel.innerHTML = `
    <header><span>CAPITAL MILESTONES</span><span>PLANNING REFERENCE</span></header>
    <div class="capital-goal-strip">
      <div><small>DAILY REALIZED GOAL</small><strong>${money(dailyGoal)}</strong><span>${dailyTargetPct.toFixed(2)}% of current equity</span></div>
      <div><small>WEEKLY REALIZED GOAL</small><strong>${money(weeklyGoal)}</strong><span>5-day geometric reference</span></div>
    </div>
    <div class="capital-trade-model">
      <div class="capital-model-head">
        <span>EXPECTED TRADES TO CUMULATIVE GAIN</span>
        <b>${expectancyDollars != null && expectancyDollars > 0 ? `${money(expectancyDollars)} / trade` : "UNAVAILABLE"}</b>
      </div>
      <div class="capital-goal-grid">
        ${goals.map(goal => `<div class="capital-goal-row"><span>${goal.label}</span><strong>${integer(tradesFor(goal.amount))}</strong><small>trades</small></div>`).join("")}
      </div>
    </div>
    <p class="capital-model-note">Static expectancy model only. It does not assume compounding, position-size growth, changing edge, fees beyond the current mock inputs, or permission to increase risk.</p>`;

  leftStack.append(panel);

  window.DUSTY_COMMAND_CAPITAL_MILESTONES = Object.freeze({
    version:"3.1",
    dailyTargetPct,
    dailyGoal,
    weeklyGoal,
    expectancyDollars,
    goals:goals.map(goal => ({...goal, expectedTrades:tradesFor(goal.amount)}))
  });
})();