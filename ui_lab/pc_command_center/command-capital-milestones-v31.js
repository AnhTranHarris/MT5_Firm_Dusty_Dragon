(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const planning = window.DUSTY_CAPITAL_PLANNING_MOCK;
  const leftStack = document.querySelector("#command .left-stack");
  if (!data || !planning || !leftStack) return;

  const stats = new Map((data.performance?.stats || []).map(([label,value]) => [label,value]));
  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g,""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  const money = value => value == null ? "—" : Number(value).toLocaleString(undefined, {style:"currency",currency:"USD",maximumFractionDigits:0});
  const compactMoney = value => {
    if (value == null) return "—";
    const n=Number(value);
    if (Math.abs(n)>=1_000_000) return `$${(n/1_000_000).toFixed(n%1_000_000===0?0:1)}M`;
    if (Math.abs(n)>=1_000) return `$${(n/1_000).toFixed(n%1_000===0?0:1)}K`;
    return money(n);
  };
  const integer = value => value == null ? "—" : Math.max(0,Math.ceil(Number(value))).toLocaleString();
  const percent = (value,digits=2) => value == null ? "—" : `${Number(value).toFixed(digits)}%`;

  const equity = numberFrom(data.firm?.equity);
  const dailyTargetPct = numberFrom(data.hierarchy?.dailyTargetPct) ?? 0.23;
  const monthlyObjectivePct = numberFrom(data.firm?.monthlyTargetPct) ?? 5;
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

  const recognizedGain = numberFrom(planning.recognizedRealizedGainUsd) ?? 0;
  const monthGain = numberFrom(planning.monthRecognizedRealizedGainUsd) ?? 0;
  const milestonePattern = [...(planning.milestonePattern || [])].map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
  const monthlyGainGoals = [...(planning.monthlyGainGoals || [])].map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
  const masterGoal = 50_000_000;

  const tradesForGain = gain => expectancyDollars != null && expectancyDollars > 0 ? Math.max(0,gain) / expectancyDollars : null;
  const remainingTo = (target,current) => Math.max(0,Number(target)-Number(current||0));

  // Always surface the next three ordinary milestones. Once one is recognized as
  // achieved, the quick-view automatically advances through the established
  // 10K -> 50K -> 100K -> 500K -> 1M -> 5M -> 10M -> 50M pattern.
  const upcomingMilestones = milestonePattern.filter(amount => amount > recognizedGain && amount < masterGoal).slice(0,3);
  while (upcomingMilestones.length < 3) {
    const last = upcomingMilestones.at(-1) ?? milestonePattern.filter(x => x < masterGoal).at(-1) ?? 10_000_000;
    const candidate = Math.min(masterGoal, last * (last / 10_000 % 10 === 1 ? 5 : 2));
    if (candidate <= last || candidate >= masterGoal) break;
    upcomingMilestones.push(candidate);
  }

  const milestoneRows = upcomingMilestones.map(amount => {
    const remaining=remainingTo(amount,recognizedGain);
    return {amount,remaining,expectedTrades:tradesForGain(remaining)};
  });
  const monthlyRows = monthlyGainGoals.map(amount => {
    const remaining=remainingTo(amount,monthGain);
    return {amount,remaining,expectedTrades:tradesForGain(remaining),met:remaining<=0};
  });

  function horizonModel(years) {
    if (equity == null || equity <= 0) return { years, monthlyPct:null, annualPct:null, status:"UNAVAILABLE", tone:"unavailable", restriction:"Current firm equity required." };
    const terminalEquity = equity + masterGoal;
    const annualRate = Math.pow(terminalEquity / equity, 1 / years) - 1;
    const monthlyRate = Math.pow(1 + annualRate, 1 / 12) - 1;
    const monthlyPct = monthlyRate * 100;
    const annualPct = annualRate * 100;
    if (years === 1) return { years, monthlyPct, annualPct, status:"RESTRICTED", tone:"restricted", restriction:"Scenario only · no risk/leverage override." };
    if (monthlyPct > monthlyObjectivePct * 2) return { years, monthlyPct, annualPct, status:"RESTRICTED", tone:"restricted", restriction:"Master-policy review · no target-driven risk escalation." };
    if (monthlyPct > monthlyObjectivePct) return { years, monthlyPct, annualPct, status:"STRETCH", tone:"stretch", restriction:"Above current firm objective · risk policy unchanged." };
    return { years, monthlyPct, annualPct, status:"POLICY RANGE", tone:"aligned", restriction:"Mathematically inside current objective; never guaranteed." };
  }
  const horizons = [1,5,10,20].map(horizonModel);

  const panel = document.createElement("article");
  panel.className = "panel compact capital-milestones-panel";
  panel.innerHTML = `
    <header><span>CAPITAL MILESTONES</span><span>PLANNING REFERENCE</span></header>
    <div class="capital-goal-strip">
      <div><small>DAILY REALIZED GOAL</small><strong>${money(dailyGoal)}</strong><span>${dailyTargetPct.toFixed(2)}% of current equity</span></div>
      <div><small>WEEKLY REALIZED GOAL</small><strong>${money(weeklyGoal)}</strong><span>5-day geometric reference</span></div>
    </div>

    <div class="capital-trade-model">
      <div class="capital-model-head"><span>NEXT CUMULATIVE GAIN MILESTONES</span><b>${expectancyDollars != null && expectancyDollars > 0 ? `${money(expectancyDollars)} / trade` : "UNAVAILABLE"}</b></div>
      <div class="capital-goal-grid capital-standard-goals">
        ${milestoneRows.map(goal => `<div class="capital-goal-row"><span>${compactMoney(goal.amount)}</span><strong>${integer(goal.expectedTrades)}</strong><small>trades · ${compactMoney(goal.remaining)} left</small></div>`).join("")}
      </div>
      <div class="capital-progress-note">Recognized cumulative realized gain: <b>${money(recognizedGain)}</b>. Completed milestones roll forward automatically.</div>
    </div>

    <div class="capital-month-model">
      <div class="capital-model-head"><span>MONTHLY REALIZED GAIN GOALS</span><b>${money(monthGain)} MTD</b></div>
      <div class="capital-month-grid">
        ${monthlyRows.map(goal => `<div class="capital-month-row ${goal.met?"met":""}"><span>${compactMoney(goal.amount)}</span><strong>${goal.met?"MET":integer(goal.expectedTrades)}</strong><small>${goal.met?"goal reached":`trades · ${compactMoney(goal.remaining)} left`}</small></div>`).join("")}
      </div>
    </div>

    <section class="capital-master-goal" aria-label="Fifty million dollar firm master goal">
      <div class="capital-master-head"><span>FIRM MASTER GAIN GOAL</span><strong>$50,000,000</strong><small>${integer(tradesForGain(remainingTo(masterGoal,recognizedGain)))} trades @ current static expectancy</small></div>
      <div class="capital-master-horizons">
        ${horizons.map(item => `<div class="capital-horizon ${item.tone}"><div><b>${item.years}Y</b><em>${item.status}</em></div><strong>${percent(item.monthlyPct)} / mo</strong><small>${percent(item.annualPct,1)} annualized</small><p>${item.restriction}</p></div>`).join("")}
      </div>
      <p class="capital-master-rule"><b>MASTER-GOAL RESTRICTIONS:</b> no target-driven leverage increase, no relaxed drawdown/risk limits, no forced trade frequency, and deposits/withdrawals do not count as realized trading gain.</p>
    </section>
    <p class="capital-model-note">Planning math only. Trade counts use current static expectancy and recognized realized-gain fixtures; they are not forecasts, promises, or execution authority.</p>`;

  leftStack.append(panel);

  window.DUSTY_COMMAND_CAPITAL_MILESTONES = Object.freeze({
    version:"3.3",
    dailyTargetPct,dailyGoal,weeklyGoal,expectancyDollars,monthlyObjectivePct,
    recognizedGain,monthGain,
    upcomingMilestones:milestoneRows,
    monthlyGainGoals:monthlyRows,
    masterGoal:Object.freeze({ gainGoalUsd:masterGoal, expectedTrades:tradesForGain(remainingTo(masterGoal,recognizedGain)), horizons })
  });
})();