(() => {
  "use strict";

  /*
   * PERFORMANCE TIMEFRAME v3.2 — fiscal-calendar, no-motion-safe reporting.
   * ---------------------------------------------------------------------
   * UX contract:
   * - Timeframe selection is discrete buttons, not animation-dependent.
   * - Actual bars NEVER render beyond the authoritative as-of date.
   * - The bright-blue as-of line marks today's reporting cut.
   * - The target line continues to the selected fiscal horizon end.
   * - Bottom-axis labels must make the reporting range explicit.
   *
   * DUSTY MANAGEMENT REPORTING POLICY (UI Lab):
   * - Uses the U.S. federal fiscal convention: Oct 1 -> Sep 30.
   * - Fiscal year is named by its END year (FY2026 = Oct 1 2025-Sep 30 2026).
   * - This is a Dusty management-reporting convention, not an assertion that the
   *   IRS mandates one fiscal year for every business entity.
   *
   * WINDOWS / PRODUCTION HANDOFF:
   * - Dusty Core owns {period_start, period_end, as_of, actual[], target[]}.
   * - Use the backend reporting timezone/as_of date; never browser time for truth.
   * - Missing future actuals remain missing. Never fabricate/interpolate them.
   * - Target policy is versioned separately from realized P&L history.
   * - View switches are presentation state only: no MT5/broker/risk/ledger writes.
   * - Render using ordinary SVG/WinUI drawing primitives; no animation is required.
   */

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data) return;

  const FISCAL_START_MONTH = 9; // October (0-based)
  const MONTHLY_TARGET = Number(data.firm?.monthlyTargetPct || 5);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dayMs = 86400000;
  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
  const endOfMonth = d => new Date(d.getFullYear(), d.getMonth() + 1, 0);
  const pct = v => `${Number(v) >= 0 ? "+" : ""}${Number(v || 0).toFixed(2)}%`;
  const fmtDate = d => d.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}).toUpperCase();
  const fmtShort = d => d.toLocaleDateString(undefined,{month:"short",day:"numeric"}).toUpperCase();

  function fiscalYearStart(date) {
    const year = date.getMonth() >= FISCAL_START_MONTH ? date.getFullYear() : date.getFullYear() - 1;
    return new Date(year, FISCAL_START_MONTH, 1);
  }

  function fiscalYearEnd(start) {
    return new Date(start.getFullYear() + 1, FISCAL_START_MONTH, 0);
  }

  function fiscalYearLabel(start) {
    return `FY${fiscalYearEnd(start).getFullYear()}`;
  }

  function quarterBounds(date) {
    const fyStart = fiscalYearStart(date);
    const monthIndex = (date.getFullYear() - fyStart.getFullYear()) * 12 + date.getMonth() - fyStart.getMonth();
    const qIndex = Math.floor(monthIndex / 3);
    return {
      start: new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3, 1),
      end: new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3 + 3, 0),
      q: qIndex + 1,
      fyStart
    };
  }

  function elapsedFraction(start, end, asOf = today) {
    const span = Math.max(dayMs, end.getTime() - start.getTime());
    return clamp((asOf.getTime() - start.getTime()) / span, 0, 1);
  }

  function shapedValues(finalValue, count) {
    const shape = [0.10,0.18,0.16,0.29,0.27,0.41,0.48,0.55,0.53,0.66,0.73,0.82,0.91,1];
    return Array.from({length:Math.max(1,count)},(_,i) => {
      const idx = Math.round(i * (shape.length - 1) / Math.max(1,count - 1));
      return finalValue * shape[idx];
    });
  }

  function monthConfig() {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    const end = endOfMonth(today);
    const count = Math.min(10, Math.max(1, today.getDate()));
    const values = shapedValues(Number(data.firm?.pnlMonthPct || 0), count);
    const actual = values.map((value,i) => ({
      date: new Date(start.getTime() + (today.getTime() - start.getTime()) * i / Math.max(1,count-1)),
      value
    }));
    return {id:"month",label:"MONTHLY",short:"1M",start,end,target:MONTHLY_TARGET,actual,note:"CURRENT MONTH"};
  }

  function quarterConfig() {
    const {start,end,q,fyStart} = quarterBounds(today);
    const weeks = Math.min(13, Math.max(2, Math.ceil((today-start)/(7*dayMs))+1));
    const finalValue = Number(data.firm?.pnlMonthPct || 0) + Number(data.firm?.pnlWeekPct || 0) * 2.55;
    const values = shapedValues(finalValue,weeks);
    const actual = values.map((value,i) => ({
      date: new Date(start.getTime() + (today.getTime()-start.getTime()) * i / Math.max(1,weeks-1)),
      value
    }));
    return {id:"quarter",label:"QUARTERLY",short:`Q${q}`,start,end,target:MONTHLY_TARGET*3,actual,note:`${fiscalYearLabel(fyStart)} · Q${q}`};
  }

  function annualConfig() {
    const start = fiscalYearStart(today);
    const end = fiscalYearEnd(start);
    const months = Math.max(1,(today.getFullYear()-start.getFullYear())*12 + today.getMonth()-start.getMonth()+1);
    const values = shapedValues(37.6,months); // deterministic UI-Lab mock until Core supplies fiscal YTD.
    const actual = values.map((value,i) => {
      const d = new Date(start.getFullYear(),start.getMonth()+i+1,0);
      return {date:d>today?today:d,value};
    });
    return {id:"year",label:"ANNUAL",short:fiscalYearLabel(start),start,end,target:MONTHLY_TARGET*12,actual,note:`${fiscalYearLabel(start)} · OCT-SEP`};
  }

  function fiveYearConfig() {
    const start = fiscalYearStart(today);
    const end = new Date(start.getFullYear()+5,start.getMonth(),0);
    const months = Math.max(1,(today.getFullYear()-start.getFullYear())*12 + today.getMonth()-start.getMonth()+1);
    const values = shapedValues(37.6,months);
    const actual = values.map((value,i) => {
      const d = new Date(start.getFullYear(),start.getMonth()+i+1,0);
      return {date:d>today?today:d,value};
    });
    return {id:"fiveYear",label:"5 YEAR",short:"5Y",start,end,target:MONTHLY_TARGET*60,actual,note:`${fiscalYearLabel(start)}-${fiscalYearEnd(new Date(start.getFullYear()+4,start.getMonth(),1)).getFullYear()} PLAN`};
  }

  const builders = [monthConfig,quarterConfig,annualConfig,fiveYearConfig];
  const labels = ["MONTHLY","QUARTERLY","ANNUAL","5 YEAR"];
  let selected = 0;
  let rendering = false;

  const panel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  if (!panel || !chart || !readout) return;

  const controls = document.createElement("div");
  controls.className = "perf-timeframe-control";
  controls.innerHTML = `
    <div class="perf-timeframe-heading"><span>FISCAL REPORT VIEW</span><strong id="perfTimeframeValue">MONTHLY</strong></div>
    <div class="perf-timeframe-buttons" role="group" aria-label="Investor fiscal report timeframe">
      ${labels.map((label,i)=>`<button type="button" data-timeframe="${i}" ${i===0?'class="active" aria-pressed="true"':'aria-pressed="false"'}>${label}</button>`).join("")}
    </div>`;
  panel.querySelector("header")?.insertAdjacentElement("afterend",controls);

  const valueLabel = controls.querySelector("#perfTimeframeValue");
  const buttons = [...controls.querySelectorAll("[data-timeframe]")];

  function currentScale() {
    const scope = root.querySelector("#perfScope")?.value || "firm";
    if (scope === "layer") {
      const n = Number(root.querySelector("#perfEntity")?.value || 1);
      return Math.max(.45,1-(n-1)*.09);
    }
    if (scope === "desk") {
      const id = root.querySelector("#perfEntity")?.value;
      const desk = (data.desks || []).find(item=>item.id===id);
      return desk ? Math.max(.05,Number(desk.mtd||0)/Math.max(Number(data.firm?.pnlMonthPct||1),.01)) : 1;
    }
    return 1;
  }

  function axisDates(config) {
    if (config.id === "month") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth(),8),new Date(config.start.getFullYear(),config.start.getMonth(),15),new Date(config.start.getFullYear(),config.start.getMonth(),22),config.end];
    if (config.id === "quarter") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth()+1,1),new Date(config.start.getFullYear(),config.start.getMonth()+2,1),config.end];
    if (config.id === "year") return [0,2,4,6,8,10,11].map(m=>new Date(config.start.getFullYear(),config.start.getMonth()+m,1));
    return [0,1,2,3,4,5].map(y=>y===5?config.end:new Date(config.start.getFullYear()+y,config.start.getMonth(),1));
  }

  function axisLabel(config,date,index,total) {
    const endpoint = index===0 || index===total-1;
    if (config.id === "month") return endpoint ? `${date.toLocaleDateString(undefined,{month:"short"}).toUpperCase()} ${date.getDate()}` : String(date.getDate()).padStart(2,"0");
    if (config.id === "quarter") return endpoint ? fmtShort(date) : date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
    if (config.id === "year") {
      const month = date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
      return endpoint ? `${month} '${String(date.getFullYear()).slice(-2)}` : month;
    }
    return `FY${fiscalYearEnd(new Date(date.getFullYear(),FISCAL_START_MONTH,1)).getFullYear()}`;
  }

  function chartSvg(config,expanded) {
    const scale=currentScale();
    const actual=config.actual.map(p=>({date:p.date,value:p.value*scale})).filter(p=>p.date<=today);
    const target=config.target*scale;
    const width=expanded?1180:900;
    const height=expanded?450:280;
    const pad={l:expanded?72:58,r:expanded?34:24,t:28,b:expanded?70:58};
    const max=Math.max(target,...actual.map(p=>p.value),1)*1.14;
    const span=Math.max(dayMs,config.end-config.start);
    const x=date=>pad.l+clamp((date-config.start)/span,0,1)*(width-pad.l-pad.r);
    const y=n=>height-pad.b-(Math.max(0,n)/max)*(height-pad.t-pad.b);
    const currentX=x(new Date(clamp(today.getTime(),config.start.getTime(),config.end.getTime())));
    const barW=Math.max(4,Math.min(expanded?38:28,Math.max(1,currentX-pad.l)/Math.max(1,actual.length)*.62));

    const grids=Array.from({length:6},(_,i)=>max*i/5).map(n=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(n)}" y2="${y(n)}"/><text class="chart-axis-label" x="${pad.l-8}" y="${y(n)+4}" text-anchor="end">${n.toFixed(max>=100?0:1)}%</text></g>`).join("");
    const bars=actual.map(p=>`<rect class="investor-actual-bar" x="${x(p.date)-barW/2}" y="${y(p.value)}" width="${barW}" height="${Math.max(1,height-pad.b-y(p.value))}" rx="2"><title>${fmtDate(p.date)} · realized ${pct(p.value)}</title></rect>`).join("");
    const goalPoints=Array.from({length:65},(_,i)=>{const f=i/64;const d=new Date(config.start.getTime()+span*f);return `${x(d)},${y(target*f)}`;}).join(" ");
    const dates=axisDates(config);
    const axis=dates.map((d,i)=>`<g class="chart-date-tick"><line x1="${x(d)}" x2="${x(d)}" y1="${height-pad.b}" y2="${height-pad.b+5}"/><text class="chart-axis-label chart-date-label" x="${x(d)}" y="${height-pad.b+19}" text-anchor="middle">${axisLabel(config,d,i,dates.length)}</text></g>`).join("");
    const todayMark=`<g class="chart-today"><line x1="${currentX}" x2="${currentX}" y1="${pad.t}" y2="${height-pad.b}"/><rect x="${clamp(currentX-55,pad.l,width-pad.r-110)}" y="4" width="110" height="20" rx="3"/><text x="${clamp(currentX,pad.l+55,width-pad.r-55)}" y="18" text-anchor="middle">TODAY · ${fmtShort(today)}</text></g>`;
    const range=`<text class="chart-range-label" x="${pad.l}" y="${height-8}">${fmtDate(config.start)}</text><text class="chart-range-label" x="${width-pad.r}" y="${height-8}" text-anchor="end">${fmtDate(config.end)}</text>`;

    return `<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${config.label} fiscal performance from ${fmtDate(config.start)} through ${fmtDate(config.end)}. Realized bars stop at ${fmtDate(today)}; target continues to period end.">${grids}${bars}<polyline class="investor-target-line" points="${goalPoints}"/>${todayMark}${axis}${range}</svg>`;
  }

  function render() {
    if (rendering) return;
    rendering=true;
    const config=builders[selected]();
    const scale=currentScale();
    const actual=config.actual.filter(p=>p.date<=today);
    const realized=(actual[actual.length-1]?.value||0)*scale;
    const target=config.target*scale;
    const targetToday=target*elapsedFraction(config.start,config.end,today);
    const delta=realized-targetToday;
    const expanded=panel.classList.contains("expanded");

    valueLabel.textContent=config.label;
    buttons.forEach((button,i)=>{
      const active=i===selected;
      button.classList.toggle("active",active);
      button.setAttribute("aria-pressed",String(active));
    });
    chart.innerHTML=chartSvg(config,expanded);
    readout.innerHTML=`
      <div><b>${pct(realized)}</b><span>REALIZED · AS OF ${fmtShort(today)}</span></div>
      <div><b>${pct(targetToday)}</b><span>TARGET AT TODAY</span></div>
      <div><b class="${delta>=0?"positive":"caution"}">${delta>=0?"+":""}${delta.toFixed(2)} pts</b><span>VS TODAY'S TARGET</span></div>
      <p><i class="legend-bar"></i> Actual bars stop at the blue TODAY line &nbsp; <i class="legend-line"></i> Target continues through ${fmtDate(config.end)} · ${config.note}.</p>`;
    rendering=false;
  }

  buttons.forEach((button,i)=>button.addEventListener("click",()=>{selected=i;render();}));
  const schedule=()=>window.setTimeout(render,0);
  root.querySelector("#perfScope")?.addEventListener("change",schedule);
  root.querySelector("#perfEntity")?.addEventListener("change",schedule);
  root.querySelector("#perfExpandChart")?.addEventListener("click",schedule);
  root.querySelectorAll("[data-lens]").forEach(button=>button.addEventListener("click",schedule));

  const observer=new MutationObserver(()=>{
    if (!rendering && !chart.querySelector(".chart-today")) schedule();
  });
  observer.observe(chart,{childList:true});

  render();
})();
