(() => {
  "use strict";

  /*
   * PERFORMANCE TIMEFRAME v3.1 — presentation-only reporting horizon.
   * -----------------------------------------------------------------
   * This UI-Lab module intentionally owns no accounting truth. The longer-horizon
   * series below are deterministic MOCK data so the investor interaction can be
   * evaluated before Dusty Core exposes authoritative monthly/quarterly/annual
   * performance history. Production must replace TIMEFRAMES[*].series with a
   * versioned immutable performance read model produced server-side.
   *
   * Windows handoff rules:
   * - Changing report horizon is view state only; never mutate ledger/risk/MT5.
   * - Query/aggregate authoritative closed-period history in Dusty Core, not UI.
   * - Preserve period boundaries/timezone and distinguish realized from target.
   * - Do not interpolate missing financial periods as if they were observations.
   * - Keep target policy separately versioned from realized performance history.
   */

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data) return;

  const TIMEFRAMES = Object.freeze([
    {
      id: "month", label: "MONTHLY", short: "1M", unit: "DAY",
      labels: ["01","04","07","10","13","16","19","22","25","NOW"],
      series: data.performance?.returns || [1.2,1.8,1.4,2.6,2.1,3.0,2.7,3.5,3.1,3.82],
      target: Number(data.firm?.monthlyTargetPct || 5), note: "Current month"
    },
    {
      id: "quarter", label: "QUARTERLY", short: "3M", unit: "WEEK",
      labels: ["W1","W2","W3","W4","W5","W6","W7","W8","W9","W10","W11","NOW"],
      series: [0.8,1.7,2.6,3.1,4.9,5.8,6.6,7.9,8.4,9.8,10.7,11.9],
      target: 15, note: "Rolling quarter · mock history"
    },
    {
      id: "year", label: "ANNUAL", short: "1Y", unit: "MONTH",
      labels: ["SEP","OCT","NOV","DEC","JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG"],
      series: [2.7,5.9,8.1,11.8,14.6,18.2,20.5,24.1,28.3,31.7,34.8,37.6],
      target: 60, note: "Trailing 12 months · mock history"
    },
    {
      id: "fiveYear", label: "5 YEAR", short: "5Y", unit: "QUARTER",
      labels: ["Y1 Q1","Y1 Q2","Y1 Q3","Y1 Q4","Y2 Q1","Y2 Q2","Y2 Q3","Y2 Q4","Y3 Q1","Y3 Q2","Y3 Q3","Y3 Q4","Y4 Q1","Y4 Q2","Y4 Q3","Y4 Q4","Y5 Q1","Y5 Q2","Y5 Q3","NOW"],
      series: [4,9,14,20,27,34,41,50,58,66,75,85,96,108,119,131,142,151,160,168.4],
      target: 300, note: "Five-year cumulative · mock history"
    }
  ]);

  let index = 0;
  let rendering = false;

  const chartPanel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  if (!chartPanel || !chart || !readout) return;

  const control = document.createElement("div");
  control.className = "perf-timeframe-control";
  control.innerHTML = `
    <div class="perf-timeframe-heading">
      <span>REPORT TIMEFRAME</span>
      <strong id="perfTimeframeValue">MONTHLY</strong>
    </div>
    <div class="perf-timeframe-slider-wrap">
      <input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0" aria-label="Investor report timeframe" aria-valuetext="Monthly">
      <div class="perf-timeframe-ticks" aria-hidden="true">
        ${TIMEFRAMES.map((item, i) => `<span data-index="${i}">${item.label}</span>`).join("")}
      </div>
    </div>`;

  const header = chartPanel.querySelector("header");
  header?.insertAdjacentElement("afterend", control);

  const slider = control.querySelector("#perfTimeframeSlider");
  const value = control.querySelector("#perfTimeframeValue");
  const ticks = [...control.querySelectorAll(".perf-timeframe-ticks span")];

  function pct(v) {
    const n = Number(v || 0);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
  }

  function currentScale() {
    const scope = root.querySelector("#perfScope")?.value || "firm";
    if (scope === "layer") {
      const layer = Number(root.querySelector("#perfEntity")?.value || 1);
      return Math.max(.45, 1 - (layer - 1) * .09);
    }
    if (scope === "desk") {
      const deskId = root.querySelector("#perfEntity")?.value;
      const desk = (data.desks || []).find(item => item.id === deskId);
      const firmMtd = Number(data.firm?.pnlMonthPct || 1);
      return desk ? Math.max(.05, Number(desk.mtd || 0) / Math.max(firmMtd, .01)) : 1;
    }
    return 1;
  }

  function seriesForCurrentScope(config) {
    const scale = currentScale();
    return config.series.map(v => Number(v) * scale);
  }

  function chartSvg(config, expanded) {
    const actual = seriesForCurrentScope(config);
    const target = config.target * currentScale();
    const width = expanded ? 1120 : 760;
    const height = expanded ? 430 : 250;
    const pad = {l: expanded ? 68 : 48, r: 24, t: 20, b: expanded ? 52 : 36};
    const maximum = Math.max(target, ...actual, 1) * 1.14;
    const usableW = width - pad.l - pad.r;
    const step = usableW / Math.max(actual.length - 1, 1);
    const x = i => pad.l + i * step;
    const y = v => height - pad.b - (Math.max(0, v) / maximum) * (height - pad.t - pad.b);
    const barW = Math.max(3, Math.min(expanded ? 34 : 22, step * .58));
    const gridCount = 5;
    const grids = Array.from({length: gridCount + 1}, (_, i) => maximum * i / gridCount)
      .map(v => `<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(v)}" y2="${y(v)}"/><text class="chart-axis-label" x="${pad.l-8}" y="${y(v)+4}" text-anchor="end">${v.toFixed(maximum >= 100 ? 0 : 1)}%</text></g>`).join("");
    const bars = actual.map((v, i) => `<rect class="investor-actual-bar" x="${x(i)-barW/2}" y="${y(v)}" width="${barW}" height="${Math.max(1,height-pad.b-y(v))}" rx="2"><title>${config.labels[i]} · realized ${pct(v)}</title></rect>`).join("");
    const goals = actual.map((_, i) => target * (i + 1) / actual.length);
    const goalPoints = goals.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    const labelStride = actual.length > 12 ? 4 : actual.length > 10 ? 2 : 1;
    const labels = config.labels.map((label, i) => {
      const visible = expanded ? i % labelStride === 0 || i === config.labels.length - 1 : i === 0 || i === config.labels.length - 1 || (actual.length <= 12 && i % Math.max(1,labelStride*2) === 0);
      return visible ? `<text class="chart-axis-label" x="${x(i)}" y="${height-12}" text-anchor="middle">${label}</text>` : "";
    }).join("");
    return `<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${config.label} realized cumulative performance bars compared with target path">${grids}${bars}<polyline class="investor-target-line" points="${goalPoints}"/>${goals.map((v,i)=>`<circle class="investor-target-point" cx="${x(i)}" cy="${y(v)}" r="${expanded?4:3}"><title>${config.labels[i]} · target ${pct(v)}</title></circle>`).join("")}${labels}</svg>`;
  }

  function renderTimeframe() {
    if (rendering) return;
    rendering = true;
    const config = TIMEFRAMES[index];
    const actual = seriesForCurrentScope(config);
    const realized = actual[actual.length - 1] || 0;
    const target = config.target * currentScale();
    const delta = realized - target;
    const expanded = chartPanel.classList.contains("expanded");

    value.textContent = config.label;
    slider.setAttribute("aria-valuetext", config.label);
    ticks.forEach((tick, i) => tick.classList.toggle("active", i === index));
    chart.innerHTML = chartSvg(config, expanded);
    readout.innerHTML = `
      <div><b>${pct(realized)}</b><span>REALIZED · ${config.short}</span></div>
      <div><b>${target.toFixed(2)}%</b><span>${config.label} OBJECTIVE</span></div>
      <div><b class="${delta >= 0 ? "positive" : "caution"}">${delta >= 0 ? "+" : ""}${delta.toFixed(2)} pts</b><span>VS OBJECTIVE</span></div>
      <p><i class="legend-bar"></i> Realized cumulative return <i class="legend-line"></i> Financial target path · ${config.note}. Target is a planning objective, not a forecast.</p>`;
    rendering = false;
  }

  function scheduleRender() {
    window.setTimeout(renderTimeframe, 0);
  }

  slider.addEventListener("input", event => {
    index = Math.max(0, Math.min(TIMEFRAMES.length - 1, Number(event.target.value) || 0));
    renderTimeframe();
  });

  ticks.forEach((tick, i) => {
    tick.addEventListener("click", () => {
      index = i;
      slider.value = String(i);
      renderTimeframe();
    });
  });

  root.querySelector("#perfScope")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfEntity")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfExpandChart")?.addEventListener("click", scheduleRender);
  root.querySelectorAll("[data-lens]").forEach(button => button.addEventListener("click", scheduleRender));

  const observer = new MutationObserver(() => {
    if (rendering) return;
    if (!chart.querySelector("svg") || !readout.textContent.includes(TIMEFRAMES[index].short)) scheduleRender();
  });
  observer.observe(chart, {childList:true});

  renderTimeframe();
})();
