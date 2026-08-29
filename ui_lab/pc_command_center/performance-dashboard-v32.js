(() => {
  "use strict";

  /*
   * PERFORMANCE UI v3.2 — investor + institutional quant measurement surface.
   * ------------------------------------------------------------------------
   * The investor lens measures capital, protection, liquidity and attribution.
   * The quant lens is intentionally different: it evaluates absolute efficiency,
   * trade-edge quality, tail/diversification risk, and benchmark-relative skill.
   *
   * QUANT SEMANTICS
   * - Absolute-return objective is NOT a benchmark and is NOT a forecast.
   * - Volatility target is a portfolio-construction policy variable. It must not be
   *   invented from cumulative return data; UI Lab leaves it UNSET until Core owns
   *   a periodic return series and an explicit volatility-budget policy.
   * - Sharpe = excess absolute return / total volatility.
   * - Information ratio = active return / tracking error and is meaningful only
   *   after an appropriate benchmark has been specified in advance.
   * - Tracking error = annualized standard deviation of benchmark-relative returns.
   * - Alpha/beta require a benchmark return series/regression; absent benchmark,
   *   they remain unavailable rather than being synthesized.
   * - Expected Shortfall complements VaR by measuring average loss beyond VaR.
   * - ES/VaR is shown as a tail-amplification diagnostic, not as a risk limit.
   * - Trade expectancy, payoff, profit factor and win rate describe execution edge;
   *   none substitutes for portfolio-level Sharpe, drawdown, or benchmark skill.
   *
   * Production boundary: view state never mutates MT5, broker, ledger, execution,
   * risk limits, benchmark policy, volatility target, or objective policy.
   */

  const data = window.DUSTY_MOCK;
  const root = document.querySelector("#performance .performance-layout");
  if (!data || !root) return;

  const desks = data.desks || [];
  const perf = data.performance || {};
  const risk = data.riskStats || {};
  const policy = data.performancePolicy || {};
  const hierarchy = data.hierarchy || {layers: []};
  const stats = new Map((perf.stats || []).map(([label, value]) => [label, value]));

  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  const stat = label => numberFrom(stats.get(label));
  const money = (value, digits = 0) => value == null ? "—" : Number(value).toLocaleString(undefined, {style:"currency",currency:"USD",maximumFractionDigits:digits});
  const pct = (value, digits = 2, signed = true) => value == null ? "—" : `${signed && Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(digits)}%`;
  const ratio = (value, digits = 2) => value == null ? "—" : Number(value).toFixed(digits);
  const safeDivide = (a, b) => a == null || b == null || Math.abs(b) < 1e-12 ? null : a / b;
  const openingCapital = (equity, returnPct) => equity == null || returnPct == null || returnPct <= -100 ? null : equity / (1 + returnPct / 100);

  const monthlyObjective = Number(policy.objective?.monthlyEffectivePct ?? data.firm?.monthlyTargetPct ?? 5);
  const openRiskLimit = Number(policy.risk?.openRiskLimitPct ?? 5);
  const drawdownWatch = Number(policy.risk?.drawdownWatchPct ?? 5);
  const riskHorizon = Number(policy.risk?.horizonDays ?? 1);
  const esConfidence = Number(policy.risk?.expectedShortfallConfidencePct ?? 95);
  const benchmarkState = policy.benchmark?.status || "UNSELECTED";
  const benchmarkLabel = policy.benchmark?.label || "NO STRATEGY BENCHMARK SELECTED";
  const volTarget = numberFrom(policy.quant?.targetVolatilityPct);

  let lens = "investor";
  let scope = "firm";
  let layer = 1;
  let desk = desks[0]?.id || "G01";
  let chartExpanded = false;

  root.innerHTML = `
    <article class="panel perf-commandbar">
      <div class="perf-titleblock"><span class="eyebrow">PERFORMANCE</span><strong id="perfScopeTitle">DUSTY DRAGON · FIRM</strong><small id="perfScopeNote">Investor view · measured return, protection, liquidity and attribution.</small></div>
      <div class="perf-controls">
        <div class="segmented" aria-label="Performance lens"><button data-lens="investor" class="active">INVESTOR</button><button data-lens="quant">QUANT</button></div>
        <select id="perfScope" aria-label="Performance scope"><option value="firm">FIRM</option><option value="layer">PORTFOLIO / LAYER</option><option value="desk">DESK</option></select>
        <select id="perfEntity" aria-label="Selected portfolio or desk" hidden></select>
      </div>
    </article>
    <section class="perf-headline" id="perfHeadline" aria-label="Investor headline metrics"></section>
    <article class="panel perf-capital" id="perfChartPanel">
      <header><span>CAPITAL & OBJECTIVES</span><span class="perf-chart-actions"><span>REALIZED vs OBJECTIVE</span><button id="perfExpandChart" type="button" aria-expanded="false">EXPAND ↗</button></span></header>
      <div id="perfGrowthChart" class="perf-growth-chart"></div>
      <div id="perfChartReadout" class="perf-chart-readout"></div>
    </article>
    <article class="panel perf-protection"><header><span>CAPITAL PROTECTION</span><span id="perfProtectionState">POLICY SNAPSHOT</span></header><div id="perfProtection" class="perf-card-grid"></div></article>
    <article class="panel perf-quality"><header><span>RETURN QUALITY</span><span id="perfQualityState">OBSERVED METRICS</span></header><div id="perfQuality" class="perf-card-grid"></div></article>
    <article class="panel perf-exposure"><header><span>LIQUIDITY & EXPOSURE</span><span id="perfExposureState">FIRM FOOTPRINT</span></header><div id="perfExposure" class="perf-card-grid"></div></article>
    <article class="panel perf-contributors"><header><span>RETURN ATTRIBUTION</span><span id="perfContributionScope">RECONCILED BY DESK</span></header><div id="perfContributors"></div></article>
    <article class="panel perf-investor-notes"><header><span>INVESTOR READOUT</span><span id="perfInvestorState">MEASURED / POLICY-AWARE</span></header><div id="perfInvestorNotes"></div></article>
    <article class="panel perf-quant" id="perfQuant" hidden>
      <header><span>QUANT RESEARCH / PERFORMANCE DIAGNOSTICS</span><span id="perfQuantState">ABSOLUTE + RELATIVE + TAIL + EDGE</span></header>
      <div id="perfQuantGrid" class="perf-quant-grid"></div>
    </article>`;

  const $ = selector => root.querySelector(selector);
  const lensButtons = [...root.querySelectorAll("[data-lens]")];
  const metric = (label, value, sub = "", tone = "") => `<div class="perf-kpi ${tone}"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`;
  const quantSection = (title, note, metrics) => `<section class="perf-quant-section"><header><b>${title}</b><span>${note}</span></header><div>${metrics.join("")}</div></section>`;

  function layerName(n) { return hierarchy.layers?.find(item => item.layer === n)?.name || `Layer ${n}`; }
  function selectedDesk() { return desks.find(item => item.id === desk) || desks[0] || {}; }

  function firmMetrics() {
    return {
      available:true,title:"DUSTY DRAGON · FIRM",note:`Measured firm result · benchmark ${benchmarkState.toLowerCase()} · objective remains separate.`,
      equity:numberFrom(data.firm?.equity),freeMargin:numberFrom(data.firm?.freeMargin),ret:numberFrom(data.firm?.pnlMonthPct),pnl:stat("Net P&L"),
      currentDd:numberFrom(data.firm?.drawdownPct),maxDd:stat("Max DD"),openRisk:numberFrom(data.firm?.openRiskPct),win:stat("Win rate"),pf:stat("Profit Factor"),
      sharpe:stat("Sharpe"),sortino:stat("Sortino"),recovery:stat("Recovery Factor"),expectancy:stat("Expectancy"),avgWin:stat("Avg Win"),avgLoss:stat("Avg Loss"),fees:stat("Fees / swap"),
      unresolved:numberFrom(data.firm?.unresolvedExecutions) ?? 0,activeDesks:desks.filter(d => !["FAULT","UNBOUND"].includes(d.state)).length,totalDesks:desks.length
    };
  }

  function deskMetrics() {
    const d = selectedDesk();
    const equity = numberFrom(d.equity);
    const ret = numberFrom(d.mtd);
    const opening = openingCapital(equity, ret);
    return {
      available:true,title:`${d.id} · DESK`,note:`Desk read model · ${d.state || "UNKNOWN"}. Missing quant statistics remain unavailable.`,
      equity,freeMargin:null,ret,pnl:opening == null ? null : equity-opening,currentDd:numberFrom(d.dd),maxDd:numberFrom(d.dd),openRisk:numberFrom(d.risk),
      win:null,pf:numberFrom(d.pf),sharpe:numberFrom(d.sharpe),sortino:null,recovery:null,expectancy:null,avgWin:null,avgLoss:null,fees:null,unresolved:null,
      activeDesks:["FAULT","UNBOUND"].includes(d.state) ? 0 : 1,totalDesks:1
    };
  }

  function entityMetrics() {
    if (scope === "desk") return deskMetrics();
    if (scope === "layer") return {available:false,title:`L${layer} · ${layerName(layer).toUpperCase()}`,note:"No authoritative Layer aggregate read model exists; quant metrics are not synthesized."};
    return firmMetrics();
  }

  function populateEntity() {
    const entity = $("#perfEntity");
    if (scope === "firm") { entity.hidden = true; return; }
    entity.hidden = false;
    entity.innerHTML = scope === "layer"
      ? [0,1,2,3,4].map(n => `<option value="${n}" ${n===layer?"selected":""}>L${n} · ${layerName(n)}</option>`).join("")
      : desks.map(d => `<option value="${d.id}" ${d.id===desk?"selected":""}>${d.id} · ${d.state}</option>`).join("");
  }

  function renderQuantUnavailable() {
    $("#perfQuantGrid").innerHTML = [
      quantSection("ABSOLUTE EFFICIENCY","risk-adjusted absolute return",[metric("SHARPE","—","aggregate unavailable"),metric("SORTINO","—","aggregate unavailable"),metric("RECOVERY","—","aggregate unavailable"),metric("VOL TARGET","—","policy unavailable")]),
      quantSection("TRADE EDGE","execution-level economics",[metric("EXPECTANCY","—","aggregate unavailable"),metric("PAYOFF","—","aggregate unavailable"),metric("PROFIT FACTOR","—","aggregate unavailable"),metric("COST DRAG","—","aggregate unavailable")]),
      quantSection("TAIL / DIVERSIFICATION","loss shape and dependence",[metric("VaR 95","—","aggregate unavailable"),metric(`ES ${esConfidence}`,"—","aggregate unavailable"),metric("ES / VaR","—","aggregate unavailable"),metric("MAX PAIR CORR","—","aggregate unavailable")]),
      quantSection("BENCHMARK / ACTIVE RISK","relative skill",[metric("BENCHMARK","—","no aggregate benchmark"),metric("ALPHA / BETA","—","benchmark series required"),metric("TRACKING ERROR","—","benchmark series required"),metric("INFORMATION RATIO","—","benchmark series required")])
    ].join("");
    $("#perfQuantState").textContent = "NO AGGREGATE QUANT READ MODEL";
  }

  function renderQuant(m) {
    const payoff = m.avgWin != null && m.avgLoss != null ? safeDivide(Math.abs(m.avgWin),Math.abs(m.avgLoss)) : null;
    const grossPreCost = m.pnl != null && m.fees != null ? m.pnl-m.fees : null;
    const costDrag = grossPreCost != null && grossPreCost > 0 && m.fees != null ? Math.abs(m.fees)/grossPreCost*100 : null;
    const var95 = scope === "firm" ? numberFrom(risk.var95) : null;
    const es = scope === "firm" ? numberFrom(risk.expectedShortfall) : null;
    const tailAmp = safeDivide(es,var95);
    const maxCorr = scope === "firm" ? numberFrom(risk.maxPairCorrelation) : null;
    const benchmarkReady = scope === "firm" && benchmarkState === "SELECTED" && Array.isArray(policy.benchmark?.returns) && policy.benchmark.returns.length > 1;

    $("#perfQuantGrid").innerHTML = [
      quantSection("ABSOLUTE EFFICIENCY","portfolio reward per unit of total/downside risk",[
        metric("SHARPE",ratio(m.sharpe),m.sharpe==null?"not reported":"reported absolute risk-adjusted return"),
        metric("SORTINO",ratio(m.sortino),m.sortino==null?"not reported":"reported downside-risk-adjusted return"),
        metric("RECOVERY",ratio(m.recovery),m.recovery==null?"not reported":"reported return / drawdown recovery factor"),
        metric("VOL TARGET",volTarget==null?"UNSET":pct(volTarget,1,false),volTarget==null?"define only with explicit quant risk policy":"annualized portfolio volatility budget")
      ]),
      quantSection("TRADE EDGE","trade economics; not a substitute for portfolio efficiency",[
        metric("EXPECTANCY",m.expectancy==null?"—":`${m.expectancy>=0?"+":""}${m.expectancy.toFixed(2)}R`,m.expectancy==null?"not reported":"mean expected R per trade"),
        metric("PAYOFF",ratio(payoff),payoff==null?"requires avg win / avg loss":"|avg win| / |avg loss|"),
        metric("PROFIT FACTOR",ratio(m.pf),m.pf==null?"not reported":"gross profit / gross loss"),
        metric("COST DRAG",pct(costDrag,2,false),costDrag==null?"requires net P&L and costs":"|fees + swap| / pre-cost trading P&L")
      ]),
      quantSection("TAIL / DIVERSIFICATION","loss severity and cross-book dependence",[
        metric("VaR 95",pct(var95,2,false),var95==null?"scope model unavailable":`${riskHorizon}D 95% loss threshold estimate`),
        metric(`EXPECTED SHORTFALL ${esConfidence}`,pct(es,2,false),es==null?"scope model unavailable":`${riskHorizon}D average loss beyond VaR threshold`),
        metric("ES / VaR",ratio(tailAmp),tailAmp==null?"requires VaR + ES":"tail amplification beyond VaR threshold"),
        metric("MAX PAIR CORR",ratio(maxCorr),maxCorr==null?"scope model unavailable":"largest reported pairwise desk/strategy correlation")
      ]),
      quantSection("BENCHMARK / ACTIVE RISK","relative skill requires a pre-specified appropriate benchmark",[
        metric("BENCHMARK",benchmarkState,benchmarkReady?benchmarkLabel:"objective is not used as benchmark"),
        metric("ALPHA / BETA","—",benchmarkReady?"regression series not yet exposed":"benchmark return series required"),
        metric("TRACKING ERROR","—",benchmarkReady?"active-return series not yet exposed":"annualized σ(portfolio − benchmark)"),
        metric("INFORMATION RATIO","—",benchmarkReady?"active-return series not yet exposed":"mean active return / tracking error")
      ])
    ].join("");
    $("#perfQuantState").textContent = benchmarkReady ? "ABSOLUTE + BENCHMARK-RELATIVE" : "ABSOLUTE / TAIL · BENCHMARK UNSELECTED";
  }

  function renderUnavailable(m) {
    $("#perfHeadline").innerHTML = ["EQUITY","MTD RETURN","NET P&L","MAX DRAWDOWN","OBJECTIVE STATUS"].map(label=>metric(label,"—","authoritative aggregate unavailable")).join("");
    $("#perfProtection").innerHTML = ["CURRENT DRAWDOWN","MAX DRAWDOWN","OPEN RISK","RISK BUDGET USED"].map(label=>metric(label,"—","aggregate unavailable")).join("");
    $("#perfQuality").innerHTML = ["WIN RATE","PROFIT FACTOR","SHARPE","EXPECTANCY"].map(label=>metric(label,"—","aggregate unavailable")).join("");
    $("#perfExposure").innerHTML = ["FREE MARGIN","MARGIN UTILIZATION","GROSS EXPOSURE","NET EXPOSURE"].map(label=>metric(label,"—","aggregate unavailable")).join("");
    $("#perfContributors").innerHTML = metric("ATTRIBUTION UNAVAILABLE","—","Layer constituent P&L is not exposed by the current read model.");
    renderQuantUnavailable();
    $("#perfProtectionState").textContent = "NO AGGREGATE READ MODEL";
    $("#perfQualityState").textContent = "NO AGGREGATE READ MODEL";
    $("#perfExposureState").textContent = "NO AGGREGATE READ MODEL";
    $("#perfContributionScope").textContent = `L${layer} · UNAVAILABLE`;
  }

  function render() {
    const m = entityMetrics();
    $("#perfScopeTitle").textContent = m.title;
    $("#perfScopeNote").textContent = lens === "quant" ? `${m.note} Quant lens separates absolute efficiency from benchmark-relative skill.` : m.note;
    $("#perfQuant").hidden = lens !== "quant";
    document.body.classList.toggle("perf-quant-active",lens === "quant");
    if (!m.available) { renderUnavailable(m); return; }

    const objectiveProgress = scope === "firm" ? safeDivide(m.ret,monthlyObjective) : null;
    const marginRatio = safeDivide(m.freeMargin,m.equity);
    const marginUtilization = marginRatio == null ? null : Math.max(0,1-marginRatio)*100;
    const riskUsed = safeDivide(m.openRisk,openRiskLimit);
    const riskHeadroom = m.openRisk == null ? null : Math.max(0,openRiskLimit-m.openRisk);

    $("#perfHeadline").innerHTML = [
      metric("EQUITY",money(m.equity),"current marked capital"),metric("MTD RETURN",pct(m.ret),scope==="firm"?"measured firm return":"reported desk return",m.ret>=0?"positive":"negative"),
      metric("NET P&L",money(m.pnl,2),scope==="firm"?"reported net result":"derived from equity and MTD return",m.pnl>=0?"positive":"negative"),metric("MAX DRAWDOWN",pct(m.maxDd,2,false),"worst peak-to-trough decline",m.maxDd!=null&&m.maxDd<drawdownWatch?"positive":"caution"),
      scope==="firm"?`<div class="perf-kpi perf-goal"><span>MONTH-END OBJECTIVE</span><strong>${objectiveProgress==null?"—":`${Math.max(0,objectiveProgress*100).toFixed(0)}%`}</strong><small>${pct(m.ret)} of ${monthlyObjective.toFixed(2)}%</small><div class="perf-progress"><i style="width:${Math.max(0,Math.min(100,(objectiveProgress||0)*100))}%"></i></div></div>`:metric("OBJECTIVE STATUS","—","no desk-specific objective policy")
    ].join("");

    $("#perfProtection").innerHTML = [
      metric("CURRENT DRAWDOWN",pct(m.currentDd,2,false),"current equity below high-water mark",m.currentDd!=null&&m.currentDd<drawdownWatch?"positive":"caution"),metric("MAX DRAWDOWN",pct(m.maxDd,2,false),"worst observed peak-to-trough decline"),
      metric("OPEN RISK",pct(m.openRisk,2,false),"current capital at stop-defined risk"),metric("RISK BUDGET USED",riskUsed==null?"—":`${(riskUsed*100).toFixed(0)}%`,riskHeadroom==null?"policy unavailable":`${riskHeadroom.toFixed(2)} pts headroom to ${openRiskLimit.toFixed(2)}% limit`,riskUsed!=null&&riskUsed<=1?"positive":"negative")
    ].join("");
    $("#perfProtectionState").textContent = m.openRisk!=null&&m.openRisk<=openRiskLimit&&(m.unresolved==null||m.unresolved===0)?"WITHIN DEFINED LIMITS":"REVIEW";

    $("#perfQuality").innerHTML = [metric("WIN RATE",pct(m.win,1,false),m.win==null?"not reported":"profitable / closed trades"),metric("PROFIT FACTOR",ratio(m.pf),"gross profit / gross loss"),metric("SHARPE",ratio(m.sharpe),"reported total-risk-adjusted return"),metric("EXPECTANCY",m.expectancy==null?"—":`${m.expectancy>=0?"+":""}${m.expectancy.toFixed(2)}R`,m.expectancy==null?"not reported":"expected R per trade")].join("");
    $("#perfQualityState").textContent = "OBSERVED · NO SYNTHETIC SCORES";

    $("#perfExposure").innerHTML = [metric("FREE MARGIN",money(m.freeMargin),marginRatio==null?"not reported":`${(marginRatio*100).toFixed(1)}% of equity available`),metric("MARGIN UTILIZATION",marginUtilization==null?"—":`${marginUtilization.toFixed(1)}%`,"1 − free margin / equity"),metric("GROSS EXPOSURE",scope==="firm"?pct(numberFrom(risk.grossExposure),1,false):"—",scope==="firm"?"absolute notional footprint / equity":"desk exposure not reported"),metric("NET EXPOSURE",scope==="firm"?pct(numberFrom(risk.netExposure),1,false):"—",scope==="firm"?"signed directional footprint / equity":"desk exposure not reported")].join("");
    $("#perfExposureState").textContent = scope==="firm"?`${m.activeDesks}/${m.totalDesks} DESKS ACTIVE`:"DESK LIQUIDITY PARTIAL";

    if (scope === "firm") {
      const contribution = perf.deskAttribution || [];
      const total = contribution.reduce((sum,item)=>sum+Number(item.pnl||0),0);
      const denominator = Math.abs(total)>1e-9?total:1;
      const maxShare = Math.max(1,...contribution.map(item=>Math.abs(Number(item.pnl||0)/denominator*100)));
      $("#perfContributors").innerHTML = contribution.map(item=>{const share=Number(item.pnl||0)/denominator*100;return `<div class="perf-contrib ${item.pnl<0?"negative":""}"><b>${item.id}</b><div><i style="width:${Math.max(4,Math.abs(share)/maxShare*100)}%"></i></div><span>${money(item.pnl)} · ${share.toFixed(1)}%</span></div>`;}).join("");
      const reconciliation = m.pnl==null?null:total-m.pnl;
      $("#perfContributionScope").textContent = reconciliation!=null&&Math.abs(reconciliation)<.01?"RECONCILED TO NET P&L":"RECONCILIATION REVIEW";
    } else {
      $("#perfContributors").innerHTML = `<div class="perf-contrib"><b>${selectedDesk().id}</b><div><i style="width:100%"></i></div><span>${money(m.pnl)} · 100%</span></div>`;
      $("#perfContributionScope").textContent = `${desk} · SINGLE DESK`;
    }

    $("#perfInvestorNotes").innerHTML = `<div class="investor-note"><b>RETURN MEASUREMENT</b><span>${pct(m.ret)} month-to-date; ${pct(m.maxDd,2,false)} maximum drawdown.</span></div><div class="investor-note"><b>OBJECTIVE ≠ BENCHMARK</b><span>${scope==="firm"?`${monthlyObjective.toFixed(2)}% is the effective monthly absolute-return objective. Benchmark: ${benchmarkState}.`:"No scope-specific objective/benchmark asserted without policy data."}</span></div><div class="investor-note"><b>RISK BUDGET</b><span>${riskUsed==null?"Scope-level risk budget unavailable.":`${(riskUsed*100).toFixed(0)}% of the ${openRiskLimit.toFixed(2)}% open-risk limit is used.`}</span></div>`;
    $("#perfInvestorState").textContent = "MEASURED / POLICY-AWARE";
    renderQuant(m);
  }

  function setChartExpanded(expanded) {
    chartExpanded=Boolean(expanded);$("#perfChartPanel").classList.toggle("expanded",chartExpanded);$("#perfExpandChart").setAttribute("aria-expanded",String(chartExpanded));$("#perfExpandChart").textContent=chartExpanded?"CLOSE ×":"EXPAND ↗";window.dispatchEvent(new CustomEvent("dusty:performance-chart-resize"));
  }

  lensButtons.forEach(button=>button.addEventListener("click",()=>{lens=button.dataset.lens;lensButtons.forEach(item=>item.classList.toggle("active",item===button));render();}));
  $("#perfScope").addEventListener("change",event=>{scope=event.target.value;populateEntity();render();});
  $("#perfEntity").addEventListener("change",event=>{if(scope==="layer")layer=Number(event.target.value);else desk=event.target.value;render();});
  $("#perfExpandChart").addEventListener("click",()=>setChartExpanded(!chartExpanded));
  document.addEventListener("keydown",event=>{if(event.key==="Escape"&&chartExpanded)setChartExpanded(false);});

  populateEntity();
  render();
})();