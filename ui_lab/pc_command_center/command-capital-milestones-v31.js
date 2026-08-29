(() => {
  "use strict";

  const data=window.DUSTY_MOCK, planning=window.DUSTY_CAPITAL_PLANNING_MOCK;
  const leftStack=document.querySelector("#command .left-stack");
  if(!data||!planning||!leftStack)return;
  const stats=new Map((data.performance?.stats||[]).map(([label,value])=>[label,value]));
  const numberFrom=value=>{if(typeof value==="number")return Number.isFinite(value)?value:null;const parsed=Number(String(value??"").replace(/[^0-9.+-]/g,""));return Number.isFinite(parsed)?parsed:null;};
  const money=value=>value==null?"—":Number(value).toLocaleString(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0});
  const compactMoney=value=>{if(value==null)return"—";const n=Number(value);if(Math.abs(n)>=1e6)return`$${(n/1e6).toFixed(n%1e6===0?0:1)}M`;if(Math.abs(n)>=1e3)return`$${(n/1e3).toFixed(n%1e3===0?0:1)}K`;return money(n);};
  const integer=value=>value==null?"—":Math.max(0,Math.ceil(Number(value))).toLocaleString();
  const percent=(value,digits=2)=>value==null?"—":`${Number(value).toFixed(digits)}%`;
  const equity=numberFrom(data.firm?.equity), dailyTargetPct=numberFrom(data.hierarchy?.dailyTargetPct)??0.23, monthlyObjectivePct=numberFrom(data.firm?.monthlyTargetPct)??5;
  const dailyRate=dailyTargetPct/100, weeklyRate=Math.pow(1+dailyRate,5)-1, dailyGoal=equity==null?null:equity*dailyRate, weeklyGoal=equity==null?null:equity*weeklyRate;
  const winRate=numberFrom(stats.get("Win rate")), avgWin=numberFrom(stats.get("Avg Win")), avgLoss=Math.abs(numberFrom(stats.get("Avg Loss"))??0);
  const expectancyDollars=winRate==null||avgWin==null||avgLoss==null?null:(winRate/100)*avgWin-(1-winRate/100)*avgLoss;
  const recognizedGain=numberFrom(planning.recognizedRealizedGainUsd)??0, quarterGain=numberFrom(planning.quarterRecognizedRealizedGainUsd)??0;
  const milestonePattern=[...(planning.milestonePattern||[])].map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
  const tradesForGain=gain=>expectancyDollars!=null&&expectancyDollars>0?Math.max(0,gain)/expectancyDollars:null;
  const remainingTo=(target,current)=>Math.max(0,Number(target)-Number(current||0));

  const upcomingMilestones=milestonePattern.filter(amount=>amount>recognizedGain).slice(0,3);
  const milestoneRows=upcomingMilestones.map(amount=>({amount,remaining:remainingTo(amount,recognizedGain),expectedTrades:tradesForGain(remainingTo(amount,recognizedGain))}));

  const weeklySeries=[...(planning.weeklyIncomeGoalSeries||[])].map(Number).filter(v=>Number.isFinite(v)&&v>0);
  const activeTier=Math.max(0,Math.min(weeklySeries.length-1,Number(planning.activeWeeklyIncomeTierIndex)||0));
  const weeks=Math.max(1,Number(planning.completedTradingWeeksInQuarter)||1);
  const quarterWeeklyAverage=quarterGain/weeks;
  const activeWeeklyGoal=weeklySeries[activeTier]??null;
  const nextWeeklyGoals=weeklySeries.slice(activeTier,activeTier+3);
  const weeklyRows=nextWeeklyGoals.map((amount,index)=>({amount,active:index===0,remaining:remainingTo(amount,quarterWeeklyAverage),expectedTrades:tradesForGain(remainingTo(amount,quarterWeeklyAverage))}));
  const quarterTierQualified=activeWeeklyGoal!=null&&quarterWeeklyAverage>=activeWeeklyGoal;
  const nextQuarterGoal=weeklySeries[Math.min(activeTier+(quarterTierQualified?1:0),weeklySeries.length-1)]??activeWeeklyGoal;

  const baseMaster=numberFrom(planning.masterGoalBaseUsd)??50_000_000, masterIncrement=numberFrom(planning.masterGoalIncrementUsd)??25_000_000;
  const reachedAt=planning.masterGoalReachedAtUtc?new Date(planning.masterGoalReachedAtUtc):null, asOf=new Date(planning.asOfUtc);
  const maintenanceMs=(numberFrom(planning.masterGoalMaintenanceYearsRequired)??1)*365.2425*24*60*60*1000;
  const maintained=reachedAt instanceof Date&&!Number.isNaN(reachedAt.valueOf())&&asOf.valueOf()-reachedAt.valueOf()>=maintenanceMs&&recognizedGain>=baseMaster;
  const masterGoal=maintained?baseMaster+masterIncrement:baseMaster;

  function horizonModel(years){if(equity==null||equity<=0)return{years,monthlyPct:null,annualPct:null,status:"UNAVAILABLE",tone:"unavailable"};const terminalEquity=equity+masterGoal,annualRate=Math.pow(terminalEquity/equity,1/years)-1,monthlyRate=Math.pow(1+annualRate,1/12)-1,monthlyPct=monthlyRate*100,annualPct=annualRate*100;if(years===1)return{years,monthlyPct,annualPct,status:"RESTRICTED",tone:"restricted"};if(monthlyPct>monthlyObjectivePct*2)return{years,monthlyPct,annualPct,status:"RESTRICTED",tone:"restricted"};if(monthlyPct>monthlyObjectivePct)return{years,monthlyPct,annualPct,status:"STRETCH",tone:"stretch"};return{years,monthlyPct,annualPct,status:"POLICY RANGE",tone:"aligned"};}
  const horizons=[1,5,10,20].map(horizonModel);

  const panel=document.createElement("article");panel.className="panel compact capital-milestones-panel";panel.innerHTML=`
    <header><span>CAPITAL MILESTONES</span><span>PLANNING REFERENCE</span></header>
    <div class="capital-goal-strip"><div><small>DAILY REALIZED GOAL</small><strong>${money(dailyGoal)}</strong><span>${dailyTargetPct.toFixed(2)}% of current equity</span></div><div><small>WEEKLY REALIZED GOAL</small><strong>${money(weeklyGoal)}</strong><span>5-day geometric reference</span></div></div>
    <div class="capital-trade-model"><div class="capital-model-head"><span>NEXT CUMULATIVE GAIN MILESTONES</span><b>${expectancyDollars>0?`${money(expectancyDollars)} / trade`:"UNAVAILABLE"}</b></div><div class="capital-goal-grid capital-standard-goals">${milestoneRows.length?milestoneRows.map(goal=>`<div class="capital-goal-row"><span>${compactMoney(goal.amount)}</span><strong>${integer(goal.expectedTrades)}</strong><small>trades · ${compactMoney(goal.remaining)} left</small></div>`).join(""):`<div class="capital-goal-row milestone-complete"><span>LADDER</span><strong>MET</strong><small>master-goal logic continues below</small></div>`}</div><div class="capital-progress-note">Recognized cumulative realized gain: <b>${money(recognizedGain)}</b>.</div></div>
    <div class="capital-month-model"><div class="capital-model-head"><span>AVERAGE WEEKLY INCOME GOALS</span><b>QUARTERLY REVIEW</b></div><div class="capital-month-grid">${weeklyRows.map(goal=>`<div class="capital-month-row ${goal.active?"active":""}"><span>${compactMoney(goal.amount)}/WK</span><strong>${goal.remaining<=0?"MET":integer(goal.expectedTrades)}</strong><small>${goal.remaining<=0?"avg reached":`trades · ${compactMoney(goal.remaining)} avg gap`}</small></div>`).join("")}</div><div class="capital-progress-note">Quarter average: <b>${money(quarterWeeklyAverage)}/wk</b> across ${weeks} completed trading week${weeks===1?"":"s"}. Next-quarter tier: <b>${compactMoney(nextQuarterGoal)}/wk</b>.</div></div>
    <section class="capital-master-goal" aria-label="Firm master gain goal"><div class="capital-master-head"><span>FIRM MASTER GAIN GOAL</span><strong>${money(masterGoal)}</strong><small>${maintained?`prior ${compactMoney(baseMaster)} goal maintained 1Y · +${compactMoney(masterIncrement)} ratchet applied`:`${integer(tradesForGain(remainingTo(masterGoal,recognizedGain)))} trades @ current static expectancy`}</small></div><div class="capital-master-horizons">${horizons.map(item=>`<div class="capital-horizon ${item.tone}"><div><b>${item.years}Y</b><em>${item.status}</em></div><strong>${percent(item.monthlyPct)} / mo</strong><small>${percent(item.annualPct,1)} annualized</small></div>`).join("")}</div></section>
    <p class="capital-model-note">Planning reference only. Weekly income tiers change at quarterly review; master goal ratchets by $25M after the active goal is reached and maintained for one additional year.</p>`;
  leftStack.append(panel);
  window.DUSTY_COMMAND_CAPITAL_MILESTONES=Object.freeze({version:"3.4",dailyTargetPct,dailyGoal,weeklyGoal,expectancyDollars,recognizedGain,quarterWeeklyAverage,activeWeeklyGoal,nextQuarterGoal,quarterTierQualified,masterGoal:Object.freeze({gainGoalUsd:masterGoal,baseGoalUsd:baseMaster,incrementUsd:masterIncrement,maintained,horizons})});
})();