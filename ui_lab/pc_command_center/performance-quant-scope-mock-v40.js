(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const scope = window.DUSTY_PERFORMANCE_SCOPE_MOCK;
  if (!data || !scope?.portfolios) return;

  /*
   * UI-LAB ONLY — QUANT SCOPE FIXTURE v4.0
   * ---------------------------------------
   * Provides explicit simulated quant diagnostics for visual/interaction testing.
   * Production must replace this entire object with Core-owned, versioned quant
   * read models calculated from canonical return/trade/risk histories.
   */

  const parse = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const n = Number(String(value ?? "").replace(/[^0-9.+-]/g, ""));
    return Number.isFinite(n) ? n : null;
  };
  const stats = new Map((data.performance?.stats || []).map(([label,value]) => [label,value]));

  const firm = {
    provenance:"MOCK_FIRM_QUANT",
    sharpe:parse(stats.get("Sharpe")),
    sortino:parse(stats.get("Sortino")),
    recovery:parse(stats.get("Recovery Factor")),
    expectancyR:parse(stats.get("Expectancy")),
    profitFactor:parse(stats.get("Profit Factor")),
    avgWin:parse(stats.get("Avg Win")),
    avgLoss:parse(stats.get("Avg Loss")),
    fees:parse(stats.get("Fees / swap")),
    netPnl:parse(stats.get("Net P&L")),
    var95Pct:parse(data.riskStats?.var95),
    expectedShortfallPct:parse(data.riskStats?.expectedShortfall),
    maxPairCorrelation:parse(data.riskStats?.maxPairCorrelation),
    trades:parse(stats.get("Trades")),
    volatilityTargetPct:null,
    benchmark:{status:"UNSELECTED",label:null}
  };

  function entityQuant(portfolio, deskNumber, entity) {
    const m = entity.panelMetrics || {};
    const scale = portfolio * 0.07 + deskNumber * 0.025;
    const pnl = parse(m.netPnl);
    const avgWin = 36 + portfolio * 5.5 + deskNumber * 3.1;
    const avgLoss = -(24 + portfolio * 2.9 + deskNumber * 1.7);
    const fees = pnl == null ? null : -Math.max(2.5,Math.abs(pnl) * (0.022 + portfolio * 0.002 + deskNumber * 0.001));
    const var95 = 0.46 + scale;
    const es = var95 * (1.28 + portfolio * 0.025 + deskNumber * 0.008);
    return {
      provenance:"MOCK_QUANT_SCOPE_SIMULATED",
      sharpe:parse(m.sharpe),
      sortino:Number(((parse(m.sharpe) || 0) * (1.24 + portfolio * 0.02)).toFixed(2)),
      recovery:Number(((parse(m.profitFactor) || 0) * (1.55 + deskNumber * 0.05)).toFixed(2)),
      expectancyR:parse(m.expectancyR),
      profitFactor:parse(m.profitFactor),
      avgWin:Number(avgWin.toFixed(2)),
      avgLoss:Number(avgLoss.toFixed(2)),
      fees:fees==null?null:Number(fees.toFixed(2)),
      netPnl:pnl,
      var95Pct:Number(var95.toFixed(2)),
      expectedShortfallPct:Number(es.toFixed(2)),
      maxPairCorrelation:Number(Math.min(0.94,0.43 + portfolio * 0.06 + deskNumber * 0.035).toFixed(2)),
      trades:Math.max(0,Math.round(9 + portfolio * 3 + deskNumber * 2)),
      volatilityTargetPct:null,
      benchmark:{status:"UNSELECTED",label:null}
    };
  }

  function weighted(desks,key) {
    const weights = desks.map(d => Math.max(0,Number(d.entity.snapshot?.equity || 0)));
    const denom = weights.reduce((a,b)=>a+b,0);
    if (!denom) return null;
    return desks.reduce((sum,d,index)=>sum + Number(d.quant[key] || 0) * weights[index],0) / denom;
  }

  const portfolios = {};
  for (let portfolio=1; portfolio<=4; portfolio+=1) {
    const model = scope.portfolios[portfolio];
    const desks = [];
    for (let deskNumber=1; deskNumber<=6; deskNumber+=1) {
      const entity = model.entities[`desk${deskNumber}`];
      desks.push({entity,quant:entityQuant(portfolio,deskNumber,entity)});
    }
    const layer = {
      provenance:"MOCK_QUANT_SCOPE_SIMULATED",
      sharpe:Number((weighted(desks,"sharpe") || 0).toFixed(2)),
      sortino:Number((weighted(desks,"sortino") || 0).toFixed(2)),
      recovery:Number((weighted(desks,"recovery") || 0).toFixed(2)),
      expectancyR:Number((weighted(desks,"expectancyR") || 0).toFixed(2)),
      profitFactor:Number((weighted(desks,"profitFactor") || 0).toFixed(2)),
      avgWin:Number((weighted(desks,"avgWin") || 0).toFixed(2)),
      avgLoss:Number((weighted(desks,"avgLoss") || 0).toFixed(2)),
      fees:Number(desks.reduce((sum,d)=>sum+Number(d.quant.fees||0),0).toFixed(2)),
      netPnl:Number(desks.reduce((sum,d)=>sum+Number(d.quant.netPnl||0),0).toFixed(2)),
      var95Pct:Number((weighted(desks,"var95Pct") || 0).toFixed(2)),
      expectedShortfallPct:Number((weighted(desks,"expectedShortfallPct") || 0).toFixed(2)),
      maxPairCorrelation:Number(Math.max(...desks.map(d=>d.quant.maxPairCorrelation)).toFixed(2)),
      trades:desks.reduce((sum,d)=>sum+d.quant.trades,0),
      volatilityTargetPct:null,
      benchmark:{status:"UNSELECTED",label:null}
    };
    portfolios[portfolio] = {
      layer,
      desks:Object.fromEntries(desks.map((d,index)=>[`desk${index+1}`,d.quant]))
    };
  }

  window.DUSTY_QUANT_SCOPE_MOCK = Object.freeze({
    contractVersion:"UI_LAB_QUANT_SCOPE_1",
    asOfUtc:data.performance?.asOfUtc,
    firm,
    portfolios
  });
})();