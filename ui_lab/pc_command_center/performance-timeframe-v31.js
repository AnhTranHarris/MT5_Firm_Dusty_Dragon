(() => {
  "use strict";

  /*
   * PERFORMANCE TIMEFRAME v3.3 — federal-fiscal-calendar investor reporting.
   * ------------------------------------------------------------------------
   * Presentation-only UI-Lab behavior. Bars represent realized firm results and
   * MUST NEVER render to the right of the authoritative "as-of" date. The target
   * line may continue through the complete selected fiscal reporting horizon.
   *
   * MOCK POLICY:
   * - Dusty Dragon uses the U.S. FEDERAL FISCAL YEAR convention for management
   *   reporting: October 1 -> September 30, with FY named for its ending year.
   *   Example: FY2026 = Oct 1, 2025 through Sep 30, 2026.
   * - This is a Dusty Dragon management/reporting policy for the UI Lab. IRS rules
   *   do NOT impose one universal fiscal year on every U.S. business; production
   *   tax/accounting configuration must follow the legal entity's adopted tax year.
   * - The browser's local calendar date is used as the UI-Lab "today" marker.
   * - Longer-horizon realized values are deterministic mock history until Dusty
   *   Core exposes authoritative fiscal-period performance read models.
   *
   * REFERENCES / PRODUCTION HANDOFF:
   * - U.S. federal fiscal year: Oct 1 through Sep 30.
   *   https://www.usa.gov/federal-budget-process
   * - IRS tax years: businesses may use a calendar year or an eligible fiscal year;
   *   a fiscal tax year generally ends on the last day of a month other than Dec.
   *   https://www.irs.gov/businesses/small-businesses-self-employed/tax-years
   * - Move fiscal-year start month/day, FY naming convention and reporting timezone
   *   into firm policy / authoritative backend configuration.
   * - Dusty Core must calculate authoritative fiscal boundaries and return an
   *   immutable {period_start, period_end, as_of, actual[], target[]} read model.
   * - The UI must not derive ledger truth, fill missing future actuals, interpolate
   *   unobserved returns, or move the as-of line beyond the backend timestamp.
   * - Switching Month / Quarter / Annual / 5-Year is view state only and must not
   *   mutate MT5, broker, risk, capital, ledger, execution or target-policy state.
   * - Historical target policies must be versioned separately from realized P&L;
   *   never rewrite old targets when firm policy changes later.
   */

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data) return;

  const FISCAL_START_MONTH = 9; // October (0-based). FY is named for ending year.
  const MONTHLY_TARGET = Number(data.firm?.monthlyTargetPct || 5);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
  const dayMs = 86400000;
  const endOfMonth = d => new Date(d.getFullYear(), d.getMonth() + 1, 0);
  const fmtDate = d => d.toLocaleDateString(undefined, {month:"short", day:"numeric", year:"numeric"}).toUpperCase();
  const fmtShort = d => d.toLocaleDateString(undefined, {month:"short", day:"numeric"}).toUpperCase();

  function fiscalYearStart(date) {
    const y = date.getMonth() >= FISCAL_START_MONTH ? date.getFullYear() : date.getFullYear() - 1;
    return new Date(y, FISCAL_START_MONTH, 1);
  }

  function fiscalYearEnd(start) {
    return new Date(start.getFullYear() + 1, FISCAL_START_MONTH, 0);
  }

  function fiscalYearNumber(start) {
    return fiscalYearEnd(start).getFullYear();
  }

  function fiscalYearForDate(date) {
    return date.getMonth() >= FISCAL_START_MONTH ? date.getFullYear() + 1 : date.getFullYear();
  }

  function currentQuarterBounds(date) {
    const fyStart = fiscalYearStart(date);
    const fiscalMonthIndex = (date.getFullYear() - fyStart.getFullYear()) * 12 + date.getMonth() - fyStart.getMonth();
    const qIndex = Math.floor(fiscalMonthIndex / 3);
    const start = new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3, 1);
    const end = new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3 + 3, 0);
    return {start, end, q: qIndex + 1, fy: fiscalYearNumber(fyStart)};
  }

  function elapsedFraction(start, end, asOf = today) {
    const span = Math.max(dayMs, end.getTime() - start.getTime());
    return clamp((asOf.getTime() - start.getTime()) / span, 0, 1);
  }

  function scaledActual(finalReturn, count) {
    const shape = [0.12,0.22,0.18,0.34,0.31,0.48,0.54,0.63,0.59,0.74,0.81,0.88,0.94,1];
    return Array.from({length:count}, (_, i) => {
      const idx = Math.round(i * (shape.length - 1) / Math.max(1, count - 1));
      return finalReturn * shape[idx];
    });
  }

  function monthConfig() {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    const end = endOfMonth(today);
    const elapsedDays = Math.max(1, today.getDate());
    const count = Math.min(10, elapsedDays);
    const actual = scaledActual(Number(data.firm?.pnlMonthPct || 0), count);
    const points = actual.map((value, i) => {
      const day = 1 + Math.round((elapsedDays - 1) * i / Math.max(1, count - 1));
      return {date:new Date(today.getFullYear(), today.getMonth(), day), value};
    });
    return {id:"month",label:"MONTHLY",short:"1M",start,end,target:MONTHLY_TARGET,actual:points,note:`FY${fiscalYearForDate(today)} · CURRENT FISCAL MONTH`};
  }

  function quarterConfig() {
    const {start,end,q,fy} = currentQuarterBounds(today);
    const elapsedWeeks = Math.max(2, Math.ceil((today - start) / (7 * dayMs)) + 1);
    const count = Math.min(12, elapsedWeeks);
    const quarterReturn = Number(data.firm?.pnlMonthPct || 0) + Number(data.firm?.pnlWeekPct || 0) * 2.55;
    const actual = scaledActual(quarterReturn, count);
    const points = actual.map((value, i) => {
      const fraction = i / Math.max(1, count - 1);
      return {date:new Date(start.getTime() + (today.getTime() - start.getTime()) * fraction), value};
    });
    return {id:"quarter",label:"QUARTERLY",short:`FY${fy} Q${q}`,start,end,target:MONTHLY_TARGET * 3,actual:points,note:`FY${fy} · Q${q}`};
  }

  function yearConfig() {
    const start = fiscalYearStart(today);
    const end = fiscalYearEnd(start);
    const fy = fiscalYearNumber(start);
    const elapsedMonths = (today.getFullYear() - start.getFullYear()) * 12 + today.getMonth() - start.getMonth() + 1;
    const count = Math.max(1, elapsedMonths);
    const ytdReturn = 37.6; // deterministic UI-Lab mock; replace with Dusty Core fiscal YTD.
    const actual = scaledActual(ytdReturn, count).map((value, i) => {
      const monthDate = new Date(start.getFullYear(), start.getMonth() + i + 1, 0);
      return {date: monthDate > today ? today : monthDate, value};
    });
    return {id:"year",label:"ANNUAL",short:`FY${fy}`,start,end,target:MONTHLY_TARGET * 12,actual,note:`FY${fy} · OCT 1 ${start.getFullYear()} – SEP 30 ${end.getFullYear()}`};
  }

  function fiveYearConfig() {
    const start = fiscalYearStart(today);
    const firstFY = fiscalYearNumber(start);
    const end = new Date(start.getFullYear() + 5, start.getMonth(), 0);
    const elapsedMonths = Math.max(1, (today.getFullYear() - start.getFullYear()) * 12 + today.getMonth() - start.getMonth() + 1);
    const ytdReturn = 37.6;
    const actual = scaledActual(ytdReturn, elapsedMonths).map((value, i) => {
      const monthDate = new Date(start.getFullYear(), start.getMonth() + i + 1, 0);
      return {date: monthDate > today ? today : monthDate, value};
    });
    return {id:"fiveYear",label:"5 YEAR",short:"5Y",start,end,target:MONTHLY_TARGET * 60,actual,note:`FY${firstFY}–FY${firstFY+4} PLAN`};
  }

  const timeframeBuilders = [monthConfig, quarterConfig, yearConfig, fiveYearConfig];
  const timeframeLabels = ["MONTHLY","QUARTERLY","ANNUAL","5 YEAR"];
  let index = 0;
  let rendering = false;

  const chartPanel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  if (!chartPanel || !chart || !readout) return;

  const control = document.createElement("div");
  control.className = "perf-timeframe-control";
  control.innerHTML = `
    <div class="perf-timeframe-heading"><span>FISCAL REPORT VIEW</span><strong id="perfTimeframeValue">MONTHLY</strong></div>
    <div class="perf-timeframe-slider-wrap">
      <input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0" aria-label="Investor fiscal report timeframe" aria-valuetext="Monthly">
      <div class="perf-timeframe-ticks">${timeframeLabels.map((label,i)=>`<button type="button" data-index="${i}" tabindex="-1">${label}</button>`).join("")}</div>
    </div>`;
  chartPanel.querySelector("header")?.insertAdjacentElement("afterend", control);

  const slider = control.querySelector("#perfTimeframeSlider");
  const value = control.querySelector("#perfTimeframeValue");
  const ticks = [...control.querySelectorAll(".perf-timeframe-ticks button")];

  function pct(v) {
    const n = Number(v || 0);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
  }

  function currentScale() {
    const scope = root.querySelector("#perfScope")?.value || "firm";
    if (scope === "layer") {
      const n = Number(root.querySelector("#perfEntity")?.value || 1);
      return Math.max(.45, 1 - (n - 1) * .09);
    }
    if (scope === "desk") {
      const id = root.querySelector("#perfEntity")?.value;
      const d = (data.desks || []).find(item => item.id === id);
      return d ? Math.max(.05, Number(d.mtd || 0) / Math.max(Number(data.firm?.pnlMonthPct || 1), .01)) : 1;
    }
    return 1;
  }

  function xLabels(config) {
    if (config.id === "month") {
      return [config.start, new Date(config.start.getFullYear(), config.start.getMonth(), 8), new Date(config.start.getFullYear(), config.start.getMonth(), 15), new Date(config.start.getFullYear(), config.start.getMonth(), 22), config.end];
    }
    if (config.id === "quarter") {
      return [config.start, new Date(config.start.getFullYear(), config.start.getMonth()+1,1), new Date(config.start.getFullYear(), config.start.getMonth()+2,1), config.end];
    }
    if (config.id === "year") {
      return [0,3,6,9,11].map(m => new Date(config.start.getFullYear(), config.start.getMonth()+m, 1));
    }
    return [0,1,2,3,4,5].map(y => y===5 ? config.end : new Date(config.start.getFullYear()+y, config.start.getMonth(),1));
  }

  function labelFor(config, date) {
    if (config.id === "month") return String(date.getDate()).padStart(2,"0");
    if (config.id === "quarter" || config.id === "year") return date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
    return `FY${fiscalYearForDate(date)}`;
  }

  function chartSvg(config, expanded) {
    const scale = currentScale();
    const actual = config.actual.map(p => ({date:p.date,value:p.value*scale})).filter(p => p.date <= today);
    const target = config.target * scale;
    const width = expanded ? 1120 : 760;
    const height = expanded ? 430 : 250;
    const pad = {l: expanded ? 68 : 48, r:26, t:24, b:expanded ? 54 : 38};
    const maximum = Math.max(target, ...actual.map(p=>p.value), 1) * 1.14;
    const span = Math.max(dayMs, config.end - config.start);
    const x = date => pad.l + clamp((date - config.start) / span, 0, 1) * (width - pad.l - pad.r);
    const y = n => height - pad.b - (Math.max(0,n)/maximum)*(height-pad.t-pad.b);
    const currentX = x(clamp(today.getTime(), config.start.getTime(), config.end.getTime()));
    const barSlots = Math.max(1, actual.length);
    const barW = Math.max(3, Math.min(expanded ? 34 : 22, (currentX-pad.l)/barSlots*.62));

    const grids = Array.from({length:6},(_,i)=>maximum*i/5).map(n=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(n)}" y2="${y(n)}"/><text class="chart-axis-label" x="${pad.l-8}" y="${y(n)+4}" text-anchor="end">${n.toFixed(maximum>=100?0:1)}%</text></g>`).join("");
    const bars = actual.map(p=>`<rect class="investor-actual-bar" x="${x(p.date)-barW/2}" y="${y(p.value)}" width="${barW}" height="${Math.max(1,height-pad.b-y(p.value))}" rx="2"><title>${fmtShort(p.date)} · realized ${pct(p.value)}</title></rect>`).join("");

    const targetPoints = Array.from({length:49},(_,i)=>{
      const f=i/48;
      const date=new Date(config.start.getTime()+span*f);
      return `${x(date)},${y(target*f)}`;
    }).join(" ");

    const labels = xLabels(config).map(d=>`<text class="chart-axis-label" x="${x(d)}" y="${height-12}" text-anchor="middle">${labelFor(config,d)}</text>`).join("");
    const todayLine = `<g class="chart-today"><line x1="${currentX}" x2="${currentX}" y1="${pad.t}" y2="${height-pad.b}"/><rect x="${Math.max(pad.l,currentX-48)}" y="3" width="96" height="18" rx="3"/><text x="${clamp(currentX,pad.l+48,width-pad.r-48)}" y="16" text-anchor="middle">${fmtDate(today)}</text></g>`;

    return `<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${config.label} fiscal performance. Realized bars stop at ${fmtDate(today)} while the financial target continues through ${fmtDate(config.end)}.">${grids}${bars}<polyline class="investor-target-line" points="${targetPoints}"/>${todayLine}${labels}</svg>`;
  }

  function renderTimeframe() {
    if (rendering) return;
    rendering = true;
    const config = timeframeBuilders[index]();
    const scale = currentScale();
    const actual = config.actual.filter(p=>p.date<=today);
    const realized = (actual[actual.length-1]?.value || 0) * scale;
    const target = config.target * scale;
    const currentTarget = target * elapsedFraction(config.start, config.end, today);
    const deltaNow = realized - currentTarget;
    const expanded = chartPanel.classList.contains("expanded");

    value.textContent = config.label;
    slider.setAttribute("aria-valuetext", config.label);
    ticks.forEach((tick,i)=>tick.classList.toggle("active",i===index));
    chart.innerHTML = chartSvg(config, expanded);
    readout.innerHTML = `
      <div><b>${pct(realized)}</b><span>REALIZED · AS OF ${fmtShort(today)}</span></div>
      <div><b>${pct(currentTarget)}</b><span>TARGET AT TODAY</span></div>
      <div><b class="${deltaNow>=0?"positive":"caution"}">${deltaNow>=0?"+":""}${deltaNow.toFixed(2)} pts</b><span>VS TODAY'S TARGET</span></div>
      <p><i class="legend-bar"></i> Bars = realized performance only through the blue as-of line &nbsp; <i class="legend-line"></i> Line = financial target through ${fmtShort(config.end)} · ${config.note}. Target is a planning objective, not a forecast.</p>`;
    rendering = false;
  }

  function scheduleRender() { window.setTimeout(renderTimeframe, 0); }

  slider.addEventListener("input", event => {
    index = clamp(Number(event.target.value)||0,0,timeframeBuilders.length-1);
    renderTimeframe();
  });
  ticks.forEach((tick,i)=>tick.addEventListener("click",()=>{index=i;slider.value=String(i);renderTimeframe();}));
  root.querySelector("#perfScope")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfEntity")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfExpandChart")?.addEventListener("click", scheduleRender);
  root.querySelectorAll("[data-lens]").forEach(button=>button.addEventListener("click",scheduleRender));

  const observer = new MutationObserver(()=>{
    if (rendering) return;
    if (!chart.querySelector(".chart-today")) scheduleRender();
  });
  observer.observe(chart,{childList:true});

  renderTimeframe();
})();
