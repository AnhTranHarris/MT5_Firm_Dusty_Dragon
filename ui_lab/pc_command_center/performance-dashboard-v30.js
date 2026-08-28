(() => {
  "use strict";

  /*
   * PERFORMANCE UI v3.2 — investor-first firm reporting surface.
   * ------------------------------------------------------------
   * Production boundary: this module is presentation/view-model only. Scope and
   * lens controls must never mutate broker, MT5, ledger, risk or execution state.
   * The native Windows implementation should receive immutable performance read
   * models from Dusty Core and render them without recomputing authoritative P&L.
   */
  const data = window.DUSTY_MOCK;
  if (!data) return;
  const root = document.querySelector("#performance .performance-layout");
  if (!root) return;

  const money = (v, digits = 0) => Number(v || 0).toLocaleString(undefined, {
    style: "currency", currency: "USD", maximumFractionDigits: digits
  });
  const pct = (v, digits = 2) => `${Number(v) >= 0 ? "+" : ""}${Number(v || 0).toFixed(digits)}%`;
  const desks = data.desks || [];
  const perf = data.performance || {};
  const hierarchy = data.hierarchy || {layers: []};
  const risk = data.riskStats || {};
  let lens = "investor";
  let scope = "firm";
  let layer = 1;
  let desk = desks[0]?.id || "G01";
  let chartExpanded = false;

  root.innerHTML = `
    <article class="panel perf-commandbar">
      <div class="perf-titleblock"><span class="eyebrow">PERFORMANCE</span><strong id="perfScopeTitle">DUSTY DRAGON · FIRM</strong><small id="perfScopeNote">Investor view of capital growth, protection, consistency and operating quality.</small></div>
      <div class="perf-controls">
        <div class="segmented" aria-label="Performance lens"><button data-lens="investor" class="active">INVESTOR</button><button data-lens="quant">QUANT</button></div>
        <select id="perfScope" aria-label="Performance scope"><option value="firm">FIRM</option><option value="layer">PORTFOLIO / LAYER</option><option value="desk">DESK</option></select>
        <select id="perfEntity" aria-label="Selected portfolio or desk" hidden></select>
      </div>
    </article>

    <section class="perf-headline" id="perfHeadline" aria-label="Investor headline metrics"></section>

    <article class="panel perf-capital" id="perfChartPanel">
      <header><span>CAPITAL & OBJECTIVES</span><span class="perf-chart-actions"><span>REALIZED vs TARGET</span><button id="perfExpandChart" type="button" aria-expanded="false">EXPAND ↗</button></span></header>
      <div id="perfGrowthChart" class="perf-growth-chart"></div>
      <div id="perfChartReadout" class="perf-chart-readout"></div>
    </article>

    <article class="panel perf-protection">
      <header><span>CAPITAL PROTECTION</span><span id="perfProtectionState">WITHIN POLICY</span></header>
      <div id="perfProtection" class="perf-card-grid"></div>
    </article>

    <article class="panel perf-quality">
      <header><span>RETURN QUALITY</span><span id="perfQualityState">CONSISTENT</span></header>
      <div id="perfQuality" class="perf-card-grid"></div>
    </article>

    <article class="panel perf-exposure">
      <header><span>LIQUIDITY & EXPOSURE</span><span>CAPITAL AVAILABLE</span></header>
      <div id="perfExposure" class="perf-card-grid"></div>
    </article>

    <article class="panel perf-contributors">
      <header><span>RETURN CONTRIBUTION</span><span id="perfContributionScope">BY DESK</span></header>
      <div id="perfContributors"></div>
    </article>

    <article class="panel perf-investor-notes">
      <header><span>INVESTOR READOUT</span><span id="perfInvestorState">POSITIVE / WATCH</span></header>
      <div id="perfInvestorNotes"></div>
    </article>

    <article class="panel perf-quant" id="perfQuant" hidden>
      <header><span>QUANT DIAGNOSTICS</span><span>RISK-ADJUSTED / EXECUTION-AWARE</span></header>
      <div id="perfQuantGrid" class="perf-quant-grid"></div>
    </article>`;

  const $ = selector => root.querySelector(selector);
  const lensButtons = [...root.querySelectorAll("[data-lens]")];

  function layerName(n) {
    return hierarchy.layers?.find(item => item.layer === n)?.name || `Layer ${n}`;
  }

  function selectedDesk() {
    return desks.find(item => item.id === desk) || desks[0] || {};
  }

  function entityMetrics() {
    if (scope === "desk") {
      const d = selectedDesk();
      return {
        title: `${d.id} · DESK`, note: `Single-desk investor reporting · ${d.state || "UNKNOWN"}`,
        balance: d.equity || 0, equity: d.equity || 0, freeMargin: (d.equity || 0) * .91,
        ret: d.mtd || 0, week: (d.mtd || 0) * .46, day: d.today || 0, dd: d.dd || 0,
        pf: d.pf || 0, sharpe: d.sharpe || 0, risk: d.risk || 0,
        win: Math.max(0, Math.min(100, 54 + (d.pf || 1) * 4)), pnl: (d.equity || 0) * (d.mtd || 0) / 100,
        activeDesks: d.state === "FAULT" ? 0 : 1, totalDesks: 1, unresolved: 0
      };
    }
    if (scope === "layer") {
      const factor = Math.max(.45, 1 - (layer - 1) * .09);
      return {
        title: `L${layer} · ${layerName(layer).toUpperCase()}`,
        note: "Portfolio aggregate · constituent desks remain financially isolated",
        balance: data.firm.balance * factor, equity: data.firm.equity * factor, freeMargin: data.firm.freeMargin * factor,
        ret: data.firm.pnlMonthPct * factor, week: data.firm.pnlWeekPct * factor, day: .48 * factor,
        dd: data.firm.drawdownPct * (1 + (layer - 1) * .12), pf: 1.71 - (layer - 1) * .06,
        sharpe: 1.36 - (layer - 1) * .05, risk: data.firm.openRiskPct * factor,
        win: 61.6 - (layer - 1) * 1.4, pnl: 3297.04 * factor,
        activeDesks: Math.max(1, 5 - Math.floor(layer / 2)), totalDesks: 6, unresolved: 0
      };
    }
    return {
      title: "DUSTY DRAGON · FIRM", note: "Investor view of capital growth, protection, consistency and operating quality.",
      balance: data.firm.balance, equity: data.firm.equity, freeMargin: data.firm.freeMargin,
      ret: data.firm.pnlMonthPct, week: data.firm.pnlWeekPct, day: data.firm.pnl24h / Math.max(data.firm.equity, 1) * 100,
      dd: data.firm.drawdownPct, pf: 1.71, sharpe: 1.36, risk: data.firm.openRiskPct, win: 61.6,
      pnl: 3297.04, activeDesks: desks.filter(d => !["FAULT", "UNBOUND"].includes(d.state)).length,
      totalDesks: desks.length, unresolved: data.firm.unresolvedExecutions || 0
    };
  }

  function metric(label, value, sub = "", tone = "") {
    return `<div class="perf-kpi ${tone}"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`;
  }

  function populateEntity() {
    const entity = $("#perfEntity");
    if (scope === "firm") { entity.hidden = true; return; }
    entity.hidden = false;
    if (scope === "layer") {
      entity.innerHTML = [0,1,2,3,4].map(n => `<option value="${n}" ${n === layer ? "selected" : ""}>L${n} · ${layerName(n)}</option>`).join("");
    } else {
      entity.innerHTML = desks.map(d => `<option value="${d.id}" ${d.id === desk ? "selected" : ""}>${d.id} · ${d.state}</option>`).join("");
    }
  }

  function chartSeries(ret) {
    const source = perf.returns || [1,1.5,2,2.4,3];
    const scale = ret / (source[source.length - 1] || 1);
    const actual = source.map(v => v * scale);
    const target = Number(data.firm.monthlyTargetPct || 5);
    const goal = actual.map((_, i) => target * (i + 1) / actual.length);
    return {actual, goal, target};
  }

  function investorChartSvg(ret, expanded) {
    const {actual, goal, target} = chartSeries(ret);
    const width = expanded ? 1120 : 760;
    const height = expanded ? 430 : 250;
    const pad = {l: expanded ? 62 : 44, r: 24, t: 20, b: expanded ? 44 : 30};
    const top = Math.max(target, ...actual, 1) * 1.18;
    const step = (width - pad.l - pad.r) / Math.max(actual.length - 1, 1);
    const x = i => pad.l + i * step;
    const y = v => height - pad.b - (Math.max(0, v) / top) * (height - pad.t - pad.b);
    const barW = Math.min(expanded ? 46 : 30, step * .55);
    const gridCount = expanded ? 5 : 4;
    const grid = Array.from({length:gridCount + 1}, (_, i) => top * i / gridCount);
    const grids = grid.map(v => `<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(v)}" y2="${y(v)}"/><text class="chart-axis-label" x="${pad.l-8}" y="${y(v)+4}" text-anchor="end">${v.toFixed(1)}%</text></g>`).join("");
    const bars = actual.map((v,i) => `<rect class="investor-actual-bar" x="${x(i)-barW/2}" y="${y(v)}" width="${barW}" height="${Math.max(1,height-pad.b-y(v))}" rx="2"><title>Period ${i+1}: ${pct(v)}</title></rect>`).join("");
    const goalPoints = goal.map((v,i) => `${x(i)},${y(v)}`).join(" ");
    const labels = actual.map((_,i) => `<text class="chart-axis-label" x="${x(i)}" y="${height-10}" text-anchor="middle">${expanded ? `P${i+1}` : i === actual.length - 1 ? "NOW" : ""}</text>`).join("");
    return `<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Realized cumulative return bars compared with the financial target path">${grids}${bars}<polyline class="investor-target-line" points="${goalPoints}"/>${goal.map((v,i) => `<circle class="investor-target-point" cx="${x(i)}" cy="${y(v)}" r="${expanded ? 4 : 3}"><title>Target ${pct(v)}</title></circle>`).join("")}${labels}</svg>`;
  }

  function renderChart(m) {
    const {target} = chartSeries(m.ret);
    $("#perfGrowthChart").innerHTML = investorChartSvg(m.ret, chartExpanded);
    const delta = m.ret - target;
    $("#perfChartReadout").innerHTML = `
      <div><b>${pct(m.ret)}</b><span>REALIZED MTD</span></div>
      <div><b>${target.toFixed(2)}%</b><span>MONTHLY OBJECTIVE</span></div>
      <div><b class="${delta >= 0 ? "positive" : "caution"}">${delta >= 0 ? "+" : ""}${delta.toFixed(2)} pts</b><span>VS OBJECTIVE</span></div>
      <p><i class="legend-bar"></i> Realized cumulative return <i class="legend-line"></i> Financial target path · planning objective, not a forecast.</p>`;
  }

  function setChartExpanded(expanded) {
    chartExpanded = Boolean(expanded);
    $("#perfChartPanel").classList.toggle("expanded", chartExpanded);
    $("#perfExpandChart").setAttribute("aria-expanded", String(chartExpanded));
    $("#perfExpandChart").textContent = chartExpanded ? "CLOSE ×" : "EXPAND ↗";
    render();
  }

  function render() {
    const m = entityMetrics();
    const target = Number(data.firm.monthlyTargetPct || 5);
    const goalProgress = Math.max(0, Math.min(100, m.ret / Math.max(target, .01) * 100));
    const marginRatio = m.equity ? m.freeMargin / m.equity * 100 : 0;
    const riskBudgetRemaining = Math.max(0, 5 - m.risk);
    const positiveDays = Math.round(Math.max(50, Math.min(85, m.win + 4)));

    $("#perfScopeTitle").textContent = m.title;
    $("#perfScopeNote").textContent = m.note;

    $("#perfHeadline").innerHTML = [
      metric("EQUITY", money(m.equity), "investor capital"),
      metric("MTD RETURN", pct(m.ret), "net performance", m.ret >= 0 ? "positive" : "negative"),
      metric("NET P&L", money(m.pnl), "after modeled costs", m.pnl >= 0 ? "positive" : "negative"),
      metric("MAX DRAWDOWN", `${m.dd.toFixed(2)}%`, m.dd < 3 ? "controlled" : "investor watch", m.dd < 3 ? "positive" : "caution"),
      `<div class="perf-kpi perf-goal"><span>MONTHLY GOAL</span><strong>${goalProgress.toFixed(0)}%</strong><small>${pct(m.ret)} of ${target.toFixed(2)}%</small><div class="perf-progress"><i style="width:${goalProgress}%"></i></div></div>`
    ].join("");

    $("#perfProtection").innerHTML = [
      metric("CURRENT DRAWDOWN", `${m.dd.toFixed(2)}%`, "from current peak", m.dd < 3 ? "positive" : "caution"),
      metric("OPEN RISK", `${m.risk.toFixed(2)}%`, "capital presently at risk"),
      metric("RISK HEADROOM", `${riskBudgetRemaining.toFixed(2)} pts`, "to 5% planning ceiling"),
      metric("UNRESOLVED EXECUTIONS", String(m.unresolved), m.unresolved ? "requires review" : "clean", m.unresolved ? "negative" : "positive")
    ].join("");
    $("#perfProtectionState").textContent = m.dd < 3 && m.unresolved === 0 ? "WITHIN POLICY" : "WATCH";

    $("#perfQuality").innerHTML = [
      metric("WIN RATE", `${m.win.toFixed(1)}%`, "profitable trades"),
      metric("PROFIT FACTOR", m.pf.toFixed(2), "gross wins / gross losses"),
      metric("SHARPE", m.sharpe.toFixed(2), "risk-adjusted return"),
      metric("POSITIVE DAYS", `${positiveDays}%`, "modeled consistency")
    ].join("");
    $("#perfQualityState").textContent = m.pf >= 1.5 && m.sharpe >= 1 ? "CONSISTENT" : "MIXED";

    $("#perfExposure").innerHTML = [
      metric("FREE MARGIN", money(m.freeMargin), `${marginRatio.toFixed(0)}% of equity`),
      metric("GROSS EXPOSURE", `${Number(risk.grossExposure || 18.4).toFixed(1)}%`, "firm notional footprint"),
      metric("NET EXPOSURE", `${Number(risk.netExposure || 7.9).toFixed(1)}%`, "directional footprint"),
      metric("ACTIVE DESKS", `${m.activeDesks} / ${m.totalDesks}`, "capital-producing units")
    ].join("");

    const contribution = scope === "desk" ? [{id:selectedDesk().id,pnl:m.pnl,pct:100}] : (perf.deskAttribution || []);
    const maxContribution = Math.max(1, ...contribution.map(item => Math.abs(item.pct)));
    $("#perfContributors").innerHTML = contribution.map(item => `<div class="perf-contrib"><b>${item.id}</b><div><i style="width:${Math.max(4, Math.abs(item.pct)/maxContribution*100)}%"></i></div><span>${money(item.pnl)} · ${item.pct}%</span></div>`).join("");
    $("#perfContributionScope").textContent = scope === "firm" ? "BY DESK" : scope === "layer" ? `L${layer} PORTFOLIO` : desk;

    const goalGap = target - m.ret;
    $("#perfInvestorNotes").innerHTML = `
      <div class="investor-note"><b>${m.ret >= 0 ? "CAPITAL IS GROWING" : "CAPITAL IS CONTRACTING"}</b><span>${m.ret >= 0 ? `${pct(m.ret)} month-to-date with ${m.dd.toFixed(2)}% drawdown.` : `Month-to-date performance is ${pct(m.ret)}.`}</span></div>
      <div class="investor-note"><b>${goalGap <= 0 ? "OBJECTIVE ACHIEVED" : "OBJECTIVE GAP"}</b><span>${goalGap <= 0 ? `${Math.abs(goalGap).toFixed(2)} points above the monthly objective.` : `${goalGap.toFixed(2)} points remain to the ${target.toFixed(2)}% monthly objective.`}</span></div>
      <div class="investor-note"><b>OPERATING CAPACITY</b><span>${marginRatio.toFixed(0)}% of equity remains as free margin; ${m.activeDesks} of ${m.totalDesks} desks are capital-active.</span></div>`;
    $("#perfInvestorState").textContent = m.ret >= 0 && m.dd < 3 ? "POSITIVE / CONTROLLED" : "WATCH";

    $("#perfQuant").hidden = lens !== "quant";
    $("#perfQuantGrid").innerHTML = [
      metric("SORTINO", (m.sharpe * 1.38).toFixed(2), "downside-adjusted"),
      metric("RECOVERY", (m.pf * 2).toFixed(2), "return / drawdown"),
      metric("EXPECTANCY", `+${(m.pf * .158).toFixed(2)}R`, "per trade"),
      metric("PAYOFF", (1.72 + (m.pf - 1.5) * .2).toFixed(2), "average win / loss"),
      metric("EXPECTED SHORTFALL", `${Number(risk.expectedShortfall || 1.72).toFixed(2)}%`, "tail-loss estimate"),
      metric("VaR 95", `${Number(risk.var95 || 1.21).toFixed(2)}%`, "one-period estimate"),
      metric("RISK EFFICIENCY", (m.ret / Math.max(m.risk, .01)).toFixed(2), "return / open risk"),
      metric("STATE", m.dd < 3 ? "HEALTHY" : "WATCH", "performance governance")
    ].join("");

    document.body.classList.toggle("perf-quant-active", lens === "quant");
    renderChart(m);
  }

  lensButtons.forEach(button => button.addEventListener("click", () => {
    lens = button.dataset.lens;
    lensButtons.forEach(item => item.classList.toggle("active", item === button));
    render();
  }));
  $("#perfScope").addEventListener("change", event => { scope = event.target.value; populateEntity(); render(); });
  $("#perfEntity").addEventListener("change", event => { if (scope === "layer") layer = Number(event.target.value); else desk = event.target.value; render(); });
  $("#perfExpandChart").addEventListener("click", () => setChartExpanded(!chartExpanded));
  document.addEventListener("keydown", event => { if (event.key === "Escape" && chartExpanded) setChartExpanded(false); });

  populateEntity();
  render();
})();
