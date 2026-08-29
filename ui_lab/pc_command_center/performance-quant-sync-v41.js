(() => {
  "use strict";

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  const scopeMock = window.DUSTY_PERFORMANCE_SCOPE_MOCK;
  const quantMock = window.DUSTY_QUANT_SCOPE_MOCK;
  if (!root || !data || !scopeMock || !quantMock) return;

  const $ = selector => root.querySelector(selector);
  const policy = data.performancePolicy || {};
  const benchmarkPolicy = policy.benchmark || {};
  const quantPolicy = policy.quant || {};
  const investorSnapshot = new Map();

  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const n = Number(String(value ?? "").replace(/[^0-9.+-]/g,""));
    return Number.isFinite(n) ? n : null;
  };
  const pct = (value,digits=2) => value==null?"—":`${Number(value).toFixed(digits)}%`;
  const ratio = (value,digits=2) => value==null?"—":Number(value).toFixed(digits);
  const safeDivide = (a,b) => a==null||b==null||Math.abs(Number(b))<1e-12?null:Number(a)/Number(b);
  const metric = (label,value,sub="") => `<div class="perf-kpi"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`;

  const slots = {
    absolute:{panel:".perf-protection",body:"#perfProtection",title:"ABSOLUTE EFFICIENCY",state:"RISK-ADJUSTED RETURN"},
    trade:{panel:".perf-quality",body:"#perfQuality",title:"TRADE EDGE",state:"EXECUTION ECONOMICS"},
    tail:{panel:".perf-exposure",body:"#perfExposure",title:"TAIL / DIVERSIFICATION",state:"LOSS SHAPE / DEPENDENCE"},
    benchmark:{panel:".perf-contributors",body:"#perfContributors",title:"BENCHMARK / ACTIVE RISK",state:"RELATIVE SKILL"}
  };

  function selection() {
    const active = root.querySelector("[data-capital-scope].active");
    const portfolio = Number(active?.dataset.capitalScope || 0);
    const entity = portfolio===0 ? "firm" : root.querySelector("#perfCapitalEntity")?.value || "layer";
    return {portfolio,entity};
  }

  function model(sel) {
    if (sel.portfolio===0) return {scopeLabel:"DUSTY DRAGON · FIRM",contextLabel:"FIRM",quant:quantMock.firm};
    const portfolio = scopeMock.portfolios?.[sel.portfolio];
    const entity = portfolio?.entities?.[sel.entity];
    const quant = sel.entity==="layer" ? quantMock.portfolios?.[sel.portfolio]?.layer : quantMock.portfolios?.[sel.portfolio]?.desks?.[sel.entity];
    return portfolio&&entity&&quant ? {scopeLabel:`PORTFOLIO ${sel.portfolio} · ${entity.label}`,contextLabel:`P${sel.portfolio} · ${entity.label}`,quant} : null;
  }

  function captureInvestor() {
    Object.values(slots).forEach(slot => {
      const panel = $(slot.panel);
      if (!panel || investorSnapshot.has(slot.panel)) return;
      investorSnapshot.set(slot.panel, {
        title:panel.querySelector("[data-panel-title]")?.textContent || "",
        state:panel.querySelector("[data-panel-state]")?.textContent || "",
        body:$(slot.body)?.innerHTML || ""
      });
    });
  }

  function restoreInvestor() {
    investorSnapshot.forEach((saved,panelSelector) => {
      const panel = $(panelSelector);
      const slot = Object.values(slots).find(item => item.panel===panelSelector);
      if (!panel || !slot) return;
      panel.querySelector("[data-panel-title]").textContent=saved.title;
      panel.querySelector("[data-panel-state]").textContent=saved.state;
      $(slot.body).innerHTML=saved.body;
    });
    $(".perf-investor-notes")?.removeAttribute("hidden");
  }

  function paint(slotKey,metrics,contextLabel) {
    const slot=slots[slotKey];
    const panel=$(slot.panel);
    panel.querySelector("[data-panel-title]").textContent=slot.title;
    panel.querySelector("[data-panel-state]").textContent=`${contextLabel} · ${slot.state}`;
    $(slot.body).innerHTML=metrics.join("");
  }

  function renderQuant() {
    captureInvestor();
    const m=model(selection());
    const q=m?.quant;
    if (!q) {
      Object.keys(slots).forEach(key=>paint(key,[metric("STATUS","—","Quant scope read model unavailable.")],"SCOPE UNAVAILABLE"));
      return;
    }
    const payoff=q.avgWin!=null&&q.avgLoss!=null?safeDivide(Math.abs(q.avgWin),Math.abs(q.avgLoss)):null;
    const preCost=q.netPnl!=null&&q.fees!=null?q.netPnl-q.fees:null;
    const costDrag=preCost!=null&&preCost>0&&q.fees!=null?Math.abs(q.fees)/preCost*100:null;
    const tailAmp=safeDivide(q.expectedShortfallPct,q.var95Pct);
    const benchmarkState=q.benchmark?.status||benchmarkPolicy.status||"UNSELECTED";
    const benchmarkReady=benchmarkState==="SELECTED";
    const volTarget=numberFrom(q.volatilityTargetPct??quantPolicy.targetVolatilityPct);

    paint("absolute",[
      metric("SHARPE",ratio(q.sharpe),"excess return / total volatility"),
      metric("SORTINO",ratio(q.sortino),"return / downside deviation"),
      metric("RECOVERY",ratio(q.recovery),"return efficiency / drawdown"),
      metric("VOL TARGET",volTarget==null?"UNSET":pct(volTarget,1),volTarget==null?"no scope policy":"annualized risk budget")
    ],m.contextLabel);
    paint("trade",[
      metric("EXPECTANCY",q.expectancyR==null?"—":`${q.expectancyR>=0?"+":""}${Number(q.expectancyR).toFixed(2)}R`,"expected R per trade"),
      metric("PAYOFF",ratio(payoff),"|avg win| / |avg loss|"),
      metric("PROFIT FACTOR",ratio(q.profitFactor),"gross profit / gross loss"),
      metric("COST DRAG",pct(costDrag,2),"cost / pre-cost P&L")
    ],m.contextLabel);
    paint("tail",[
      metric("VaR 95",pct(q.var95Pct,2),"scope loss-threshold estimate"),
      metric("EXPECTED SHORTFALL",pct(q.expectedShortfallPct,2),"average loss beyond VaR"),
      metric("ES / VaR",ratio(tailAmp),"tail amplification"),
      metric("MAX PAIR CORR",ratio(q.maxPairCorrelation),"largest reported dependence")
    ],m.contextLabel);
    paint("benchmark",[
      metric("BENCHMARK",benchmarkState,benchmarkReady?(q.benchmark?.label||benchmarkPolicy.label||"SELECTED"):"objective is not a benchmark"),
      metric("ALPHA / BETA","—",benchmarkReady?"regression model not exposed":"benchmark series required"),
      metric("TRACKING ERROR","—",benchmarkReady?"active-return series not exposed":"benchmark series required"),
      metric("INFORMATION RATIO","—",benchmarkReady?"active-return series not exposed":"benchmark series required")
    ],m.contextLabel);
    $(".perf-investor-notes")?.setAttribute("hidden","");
    const title=$("#perfScopeTitle");
    const note=$("#perfScopeNote");
    if(title) title.textContent=`${m.scopeLabel} · QUANT`;
    if(note) note.textContent=`Quant view · synchronized ${m.scopeLabel.toLowerCase()} read model.`;
  }

  function renderForLens() {
    if(document.body.classList.contains("perf-quant-active")) renderQuant(); else restoreInvestor();
  }

  // The Capital controller emits this only after its internal portfolio/entity
  // state and DOM controls are committed. Quant therefore never races a raw click.
  window.addEventListener("dusty:performance-capital-scope-changed",()=>{
    if(document.body.classList.contains("perf-quant-active")) renderQuant();
  });
  window.addEventListener("dusty:performance-scope-synchronized",()=>{
    if(document.body.classList.contains("perf-quant-active")) renderQuant();
    else { investorSnapshot.clear(); captureInvestor(); }
  });
  window.addEventListener("dusty:performance-lens-changed",event=>setTimeout(()=>event.detail?.lens==="quant"?renderQuant():restoreInvestor(),0));

  window.DUSTY_PERFORMANCE_QUANT_SYNC=Object.freeze({version:"4.2",render:renderForLens,selection});
  captureInvestor();
})();