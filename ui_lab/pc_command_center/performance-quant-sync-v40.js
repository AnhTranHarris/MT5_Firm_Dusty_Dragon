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

  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const n = Number(String(value ?? "").replace(/[^0-9.+-]/g,""));
    return Number.isFinite(n) ? n : null;
  };
  const pct = (value,digits=2,signed=false) => value==null?"—":`${signed&&Number(value)>=0?"+":""}${Number(value).toFixed(digits)}%`;
  const ratio = (value,digits=2) => value==null?"—":Number(value).toFixed(digits);
  const money = (value,digits=2) => value==null?"—":Number(value).toLocaleString(undefined,{style:"currency",currency:"USD",maximumFractionDigits:digits});
  const safeDivide = (a,b) => a==null||b==null||Math.abs(Number(b))<1e-12?null:Number(a)/Number(b);
  const metric = (label,value,sub="",tone="") => `<div class="perf-kpi ${tone}"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`;
  const section = (title,note,metrics) => `<section class="perf-quant-section"><header><b>${title}</b><span>${note}</span></header><div>${metrics.join("")}</div></section>`;

  function selection() {
    const active = root.querySelector("[data-capital-scope].active");
    const portfolio = Number(active?.dataset.capitalScope || 0);
    const entity = portfolio===0 ? "firm" : root.querySelector("#perfCapitalEntity")?.value || "layer";
    return {portfolio,entity};
  }

  function model(sel) {
    if (sel.portfolio===0) {
      return {
        label:"FIRM",
        scopeLabel:"DUSTY DRAGON · FIRM",
        quant:quantMock.firm,
        investorMetrics:null,
        provenance:quantMock.firm.provenance
      };
    }
    const portfolio = scopeMock.portfolios?.[sel.portfolio];
    const entity = portfolio?.entities?.[sel.entity];
    const quant = sel.entity==="layer"
      ? quantMock.portfolios?.[sel.portfolio]?.layer
      : quantMock.portfolios?.[sel.portfolio]?.desks?.[sel.entity];
    if (!portfolio || !entity || !quant) return null;
    return {
      label:entity.label,
      scopeLabel:`PORTFOLIO ${sel.portfolio} · ${entity.label}`,
      quant,
      investorMetrics:entity.panelMetrics,
      provenance:quant.provenance
    };
  }

  function renderUnavailable(message="Quant scope read model unavailable.") {
    $("#perfQuantGrid").innerHTML = [
      section("ABSOLUTE EFFICIENCY","risk-adjusted absolute return",[metric("SHARPE","—",message),metric("SORTINO","—",message),metric("RECOVERY","—",message),metric("VOL TARGET","—",message)]),
      section("TRADE EDGE","execution economics",[metric("EXPECTANCY","—",message),metric("PAYOFF","—",message),metric("PROFIT FACTOR","—",message),metric("COST DRAG","—",message)]),
      section("TAIL / DIVERSIFICATION","loss shape and dependence",[metric("VaR 95","—",message),metric("EXPECTED SHORTFALL","—",message),metric("ES / VaR","—",message),metric("MAX PAIR CORR","—",message)]),
      section("BENCHMARK / ACTIVE RISK","relative skill",[metric("BENCHMARK","UNSELECTED","objective is not a benchmark"),metric("ALPHA / BETA","—","benchmark series required"),metric("TRACKING ERROR","—","benchmark series required"),metric("INFORMATION RATIO","—","benchmark series required")])
    ].join("");
  }

  function render() {
    const sel = selection();
    const m = model(sel);
    if (!m) { renderUnavailable(); return; }

    const q = m.quant;
    const payoff = q.avgWin!=null&&q.avgLoss!=null ? safeDivide(Math.abs(q.avgWin),Math.abs(q.avgLoss)) : null;
    const preCost = q.netPnl!=null&&q.fees!=null ? q.netPnl-q.fees : null;
    const costDrag = preCost!=null&&preCost>0&&q.fees!=null ? Math.abs(q.fees)/preCost*100 : null;
    const tailAmp = safeDivide(q.expectedShortfallPct,q.var95Pct);
    const benchmarkState = q.benchmark?.status || benchmarkPolicy.status || "UNSELECTED";
    const benchmarkReady = benchmarkState === "SELECTED";
    const volTarget = numberFrom(q.volatilityTargetPct ?? quantPolicy.targetVolatilityPct);
    const mockScope = String(q.provenance || "").startsWith("MOCK");

    $("#perfQuantGrid").innerHTML = [
      section("ABSOLUTE EFFICIENCY","reward per unit of total/downside risk",[
        metric("SHARPE",ratio(q.sharpe),"excess return / total volatility"),
        metric("SORTINO",ratio(q.sortino),"return / downside deviation"),
        metric("RECOVERY",ratio(q.recovery),"return efficiency relative to drawdown"),
        metric("VOL TARGET",volTarget==null?"UNSET":pct(volTarget,1,false),volTarget==null?"no scope-specific volatility policy":"annualized risk budget")
      ]),
      section("TRADE EDGE","execution-level economics",[
        metric("EXPECTANCY",q.expectancyR==null?"—":`${q.expectancyR>=0?"+":""}${Number(q.expectancyR).toFixed(2)}R`,"expected R per trade"),
        metric("PAYOFF",ratio(payoff),payoff==null?"avg win/loss unavailable":"|avg win| / |avg loss|"),
        metric("PROFIT FACTOR",ratio(q.profitFactor),"gross profit / gross loss"),
        metric("COST DRAG",pct(costDrag,2,false),costDrag==null?"cost basis unavailable":"|fees + swap| / pre-cost P&L")
      ]),
      section("TAIL / DIVERSIFICATION","tail severity and concentration",[
        metric("VaR 95",pct(q.var95Pct,2,false),"scope loss-threshold estimate"),
        metric("EXPECTED SHORTFALL",pct(q.expectedShortfallPct,2,false),"average loss beyond VaR threshold"),
        metric("ES / VaR",ratio(tailAmp),tailAmp==null?"requires VaR + ES":"tail amplification ratio"),
        metric("MAX PAIR CORR",ratio(q.maxPairCorrelation),"largest reported strategy/desk correlation")
      ]),
      section("BENCHMARK / ACTIVE RISK","relative skill requires a pre-specified benchmark",[
        metric("BENCHMARK",benchmarkState,benchmarkReady?(q.benchmark?.label||benchmarkPolicy.label||"SELECTED"):"objective is never substituted"),
        metric("ALPHA / BETA","—",benchmarkReady?"regression read model not exposed":"benchmark series required"),
        metric("TRACKING ERROR","—",benchmarkReady?"active-return series not exposed":"annualized σ(scope − benchmark)"),
        metric("INFORMATION RATIO","—",benchmarkReady?"active-return series not exposed":"mean active return / tracking error")
      ])
    ].join("");

    const scopeState = $("#perfQuantScopeState");
    if (scopeState) scopeState.textContent = `${m.scopeLabel} · ${mockScope?"UI-LAB SIMULATED":"CORE READ MODEL"}`;
    const title = $("#perfScopeTitle");
    const note = $("#perfScopeNote");
    if (document.body.classList.contains("perf-quant-active")) {
      if (title) title.textContent = `${m.scopeLabel} · QUANT`;
      if (note) note.textContent = `Quant view · synchronized to the same ${m.scopeLabel.toLowerCase()} selection as the investor lens.`;
    }
  }

  window.addEventListener("dusty:performance-scope-synchronized", render);
  window.addEventListener("dusty:performance-lens-changed", event => {
    if (event.detail?.lens === "quant") setTimeout(render,0);
  });
  root.addEventListener("change", event => {
    if (event.target.id === "perfCapitalEntity") setTimeout(render,0);
  });
  root.addEventListener("click", event => {
    if (event.target.closest("[data-capital-scope]")) setTimeout(render,0);
  });

  window.DUSTY_PERFORMANCE_QUANT_SYNC = Object.freeze({version:"4.0",render,selection});
  render();
})();