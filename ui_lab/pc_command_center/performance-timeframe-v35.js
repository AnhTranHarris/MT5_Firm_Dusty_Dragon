(() => {
  "use strict";

  /*
   * PERFORMANCE TIMEFRAME v3.5 — institutional investor capital/objective view.
   * -------------------------------------------------------------------------
   * Financial semantics:
   * - Actual cumulative return is plotted only when the current read model owns
   *   a period-consistent series. Missing history is shown as unavailable; it is
   *   never synthesized from unrelated MTD/WTD fields.
   * - Yellow dashed line = ex-ante absolute-return OBJECTIVE, not a forecast and
   *   not a benchmark. Multi-period objectives compound geometrically.
   * - Blue vertical line = authoritative as-of date (TODAY in UI Lab).
   * - High-water mark is derived only when current drawdown is explicitly known:
   *       HWM = equity / (1 - current_drawdown)
   * - Drawdown watch floor is a policy reference, not a forecasted loss:
   *       watch_floor = HWM * (1 - drawdown_watch_limit)
   * - A benchmark is rendered only if a pre-specified, period-consistent benchmark
   *   series exists. Dusty's objective is never substituted for that benchmark.
   *
   * UX semantics:
   * - Novice investors get plain-language legend/readout/risk-floor context.
   * - Advanced investors get return axis, capital axis, HWM, policy floor,
   *   objective-at-today gap and explicit data-coverage state in one view.
   * - NO MOTION / OS reduced-motion switches the slider to static buttons.
   *
   * Production boundary:
   * - This module is read-only presentation. It never mutates MT5, broker, risk,
   *   ledger, benchmark, target, or capital-allocation authority.
   */

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data) return;

  const perf = data.performance || {};
  const policy = data.performancePolicy || {};
  const stats = new Map((perf.stats || []).map(([label, value]) => [label, value]));
  const FISCAL_START_MONTH = 9;
  const DAY_MS = 86400000;
  const MORPH_MS = 460;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const monthlyObjective = Number(policy.objective?.monthlyEffectivePct ?? data.firm?.monthlyTargetPct ?? 5);
  const drawdownWatchPct = Number(policy.risk?.drawdownWatchPct ?? 5);

  const numberFrom = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  const stat = label => numberFrom(stats.get(label));
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = t => t * t * (3 - 2 * t);
  const pct = (value, digits = 2) => value == null ? "—" : `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(digits)}%`;
  const money = value => value == null ? "—" : Number(value).toLocaleString(undefined, {style:"currency",currency:"USD",maximumFractionDigits:0});
  const fmtDate = date => date.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}).toUpperCase();
  const fmtShort = date => date.toLocaleDateString(undefined,{month:"short",day:"numeric"}).toUpperCase();
  const endOfMonth = date => new Date(date.getFullYear(), date.getMonth() + 1, 0);

  function fiscalYearStart(date) {
    return new Date(date.getMonth() >= FISCAL_START_MONTH ? date.getFullYear() : date.getFullYear() - 1, FISCAL_START_MONTH, 1);
  }
  function fiscalYearEnd(start) { return new Date(start.getFullYear() + 1, FISCAL_START_MONTH, 0); }
  function fiscalYearLabel(start) { return `FY${fiscalYearEnd(start).getFullYear()}`; }
  function quarterBounds(date) {
    const fyStart = fiscalYearStart(date);
    const monthIndex = (date.getFullYear() - fyStart.getFullYear()) * 12 + date.getMonth() - fyStart.getMonth();
    const qIndex = Math.floor(monthIndex / 3);
    return {
      start:new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3, 1),
      end:new Date(fyStart.getFullYear(), fyStart.getMonth() + qIndex * 3 + 3, 0),
      q:qIndex + 1,
      fyStart
    };
  }
  function compoundMonths(months) { return (Math.pow(1 + monthlyObjective / 100, months) - 1) * 100; }
  function objectiveAtFraction(horizonPct, fraction) {
    return (Math.pow(1 + Math.max(-.999999, horizonPct / 100), clamp(fraction,0,1)) - 1) * 100;
  }
  function elapsedFraction(start, end, asOf = today) {
    const span = Math.max(DAY_MS, end.getTime() - start.getTime());
    return clamp((asOf.getTime() - start.getTime()) / span, 0, 1);
  }

  function observedSeries(start, end, source) {
    if (!Array.isArray(source) || !source.length) return [];
    const usableEnd = new Date(Math.min(today.getTime(), end.getTime()));
    return source.map((value, index) => ({
      date:new Date(start.getTime() + (usableEnd.getTime() - start.getTime()) * index / Math.max(1, source.length - 1)),
      value:Number(value)
    })).filter(point => Number.isFinite(point.value));
  }

  function horizonSource(id) {
    const explicit = perf.horizonReturns?.[id];
    if (Array.isArray(explicit)) return explicit;
    return id === "month" && Array.isArray(perf.returns) ? perf.returns : null;
  }

  function monthConfig() {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    const end = endOfMonth(today);
    return {id:"month",label:"MONTHLY",start,end,target:compoundMonths(1),actual:observedSeries(start,end,horizonSource("month")),note:"1-MONTH EFFECTIVE OBJECTIVE"};
  }
  function quarterConfig() {
    const {start,end,q,fyStart} = quarterBounds(today);
    return {id:"quarter",label:"QUARTERLY",start,end,target:compoundMonths(3),actual:observedSeries(start,end,horizonSource("quarter")),note:`${fiscalYearLabel(fyStart)} · Q${q}`};
  }
  function annualConfig() {
    const start = fiscalYearStart(today);
    const end = fiscalYearEnd(start);
    return {id:"year",label:"ANNUAL",start,end,target:compoundMonths(12),actual:observedSeries(start,end,horizonSource("year")),note:`${fiscalYearLabel(start)} · OCT-SEP`};
  }
  function fiveYearConfig() {
    const start = fiscalYearStart(today);
    const end = new Date(start.getFullYear()+5,start.getMonth(),0);
    return {id:"fiveYear",label:"5 YEAR",start,end,target:compoundMonths(60),actual:observedSeries(start,end,horizonSource("fiveYear")),note:`${fiscalYearLabel(start)} → FY${end.getFullYear()}`};
  }

  const builders = [monthConfig, quarterConfig, annualConfig, fiveYearConfig];
  const labels = ["MONTHLY","QUARTERLY","ANNUAL","5 YEAR"];
  let selected = 0;
  let rendering = false;
  let morphTimer = 0;
  let morphToken = 0;

  const panel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  if (!panel || !chart || !readout) return;

  const sliderControls = document.createElement("div");
  sliderControls.className = "perf-timeframe-slider-control";
  sliderControls.innerHTML = `
    <div class="perf-timeframe-heading"><span>REPORTING HORIZON</span><strong id="perfTimeframeValue">MONTHLY</strong></div>
    <div class="perf-timeframe-slider-wrap">
      <input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0" aria-label="Investor reporting horizon" aria-valuetext="Monthly">
      <div class="perf-timeframe-slider-labels" aria-hidden="true">${labels.map(label=>`<span>${label}</span>`).join("")}</div>
    </div>`;
  panel.querySelector("header")?.insertAdjacentElement("afterend", sliderControls);

  const legend = document.createElement("div");
  legend.className = "perf-investor-legend";
  legend.innerHTML = `
    <span><i class="legend-actual-line"></i>ACTUAL CAPITAL PATH</span>
    <span><i class="legend-line"></i>ABSOLUTE-RETURN OBJECTIVE</span>
    <span><i class="legend-today"></i>AS-OF DATE</span>
    <span><i class="legend-hwm"></i>HIGH-WATER MARK</span>
    <span><i class="legend-floor"></i>DRAWDOWN WATCH FLOOR</span>
    <span class="perf-benchmark-state">BENCHMARK · ${policy.benchmark?.status || "UNSELECTED"}</span>`;
  sliderControls.insertAdjacentElement("afterend", legend);

  const staticControls = document.createElement("div");
  staticControls.className = "perf-timeframe-static-controls";
  staticControls.setAttribute("role","group");
  staticControls.setAttribute("aria-label","Investor reporting horizon");
  staticControls.innerHTML = labels.map((label,index)=>`<button type="button" data-timeframe="${index}" ${index===0?'class="active" aria-pressed="true"':'aria-pressed="false"'}>${label}</button>`).join("");
  chart.insertAdjacentElement("afterend", staticControls);

  const depthRibbon = document.createElement("div");
  depthRibbon.className = "perf-capital-depth-ribbon";
  readout.insertAdjacentElement("afterend", depthRibbon);

  const slider = sliderControls.querySelector("#perfTimeframeSlider");
  const valueLabel = sliderControls.querySelector("#perfTimeframeValue");
  const buttons = [...staticControls.querySelectorAll("[data-timeframe]")];

  function noMotion() {
    return document.body.classList.contains("render-no-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function scopeContext(config) {
    const scope = root.querySelector("#perfScope")?.value || "firm";
    if (scope === "layer") return {scope,available:false,reason:"No authoritative Layer aggregate capital history is exposed by the current read model."};
    if (scope === "desk") {
      const id = root.querySelector("#perfEntity")?.value;
      const desk = (data.desks || []).find(item => item.id === id);
      if (!desk) return {scope,available:false,reason:"Selected desk read model is unavailable."};
      return {
        scope,available:true,label:id,equity:numberFrom(desk.equity),currentDd:numberFrom(desk.dd),realized:numberFrom(desk.mtd),
        objective:null,actual:[],dataCoverage:"CURRENT DESK SNAPSHOT · PATH HISTORY NOT EXPOSED"
      };
    }
    const actual = config.actual || [];
    const realized = actual.length ? actual[actual.length-1].value : (config.id === "month" ? numberFrom(data.firm?.pnlMonthPct) : null);
    return {
      scope,available:true,label:"FIRM",equity:numberFrom(data.firm?.equity),currentDd:numberFrom(data.firm?.drawdownPct),realized,
      objective:config.target,actual,dataCoverage:actual.length > 1 ? "AUTHORITATIVE UI-LAB SERIES" : "HORIZON HISTORY NOT EXPOSED"
    };
  }

  function capitalReferences(ctx) {
    if (!ctx.available || ctx.equity == null || ctx.realized == null || ctx.realized <= -100) return {};
    const startCapital = ctx.equity / (1 + ctx.realized / 100);
    const hwm = ctx.currentDd != null && ctx.currentDd >= 0 && ctx.currentDd < 100 ? ctx.equity / (1 - ctx.currentDd / 100) : null;
    const watchFloor = hwm == null ? null : hwm * (1 - drawdownWatchPct / 100);
    const hwmReturn = hwm == null ? null : (hwm / startCapital - 1) * 100;
    const watchFloorReturn = watchFloor == null ? null : (watchFloor / startCapital - 1) * 100;
    return {startCapital,hwm,watchFloor,hwmReturn,watchFloorReturn};
  }

  function sampleSeries(series, normalized) {
    if (!series.length) return null;
    if (series.length === 1) return Number(series[0].value);
    const position = clamp(normalized,0,1) * (series.length - 1);
    const left = Math.floor(position);
    const right = Math.min(series.length - 1, left + 1);
    return lerp(Number(series[left].value), Number(series[right].value), position-left);
  }

  function blendedConfig(from, to, progress) {
    const t = smooth(progress);
    const start = new Date(lerp(from.start.getTime(),to.start.getTime(),t));
    const end = new Date(lerp(from.end.getTime(),to.end.getTime(),t));
    const count = Math.max(from.actual.length,to.actual.length,0);
    const actual = count ? Array.from({length:count},(_,index)=>{
      const n=index/Math.max(1,count-1);
      const a=sampleSeries(from.actual,n);
      const b=sampleSeries(to.actual,n);
      const value=a==null?b:b==null?a:lerp(a,b,t);
      return {date:new Date(lerp(start.getTime(),Math.min(today.getTime(),end.getTime()),n)),value};
    }).filter(point=>point.value!=null) : [];
    return {id:t<.5?from.id:to.id,label:t<.5?from.label:to.label,start,end,target:lerp(from.target,to.target,t),actual,note:t<.5?from.note:to.note,transitioning:true};
  }

  function axisDates(config) {
    if (config.transitioning) {
      const span=config.end-config.start;
      return [0,.25,.5,.75,1].map(f=>new Date(config.start.getTime()+span*f));
    }
    if (config.id === "month") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth(),8),new Date(config.start.getFullYear(),config.start.getMonth(),15),new Date(config.start.getFullYear(),config.start.getMonth(),22),config.end];
    if (config.id === "quarter") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth()+1,1),new Date(config.start.getFullYear(),config.start.getMonth()+2,1),config.end];
    if (config.id === "year") return [0,2,4,6,8,10,11].map(month=>new Date(config.start.getFullYear(),config.start.getMonth()+month,1));
    return [0,1,2,3,4].map(year=>new Date(config.start.getFullYear()+year,config.start.getMonth(),1));
  }

  function axisLabel(config,date,index,total) {
    const endpoint=index===0||index===total-1;
    if (config.transitioning) return endpoint?fmtDate(date):date.toLocaleDateString(undefined,{month:"short",year:"2-digit"}).toUpperCase();
    if (config.id === "month") return endpoint?`${date.toLocaleDateString(undefined,{month:"short"}).toUpperCase()} ${date.getDate()}`:String(date.getDate()).padStart(2,"0");
    if (config.id === "quarter") return endpoint?fmtShort(date):date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
    if (config.id === "year") return date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
    return `FY${fiscalYearEnd(date).getFullYear()}`;
  }

  function chartSvg(config, expanded, ctx, refs) {
    const width=expanded?1180:900;
    const height=expanded?470:300;
    const pad={l:expanded?74:62,r:expanded?84:72,t:34,b:expanded?72:60};
    if (!ctx.available) return `<div class="perf-chart-unavailable"><strong>CAPITAL PATH UNAVAILABLE</strong><span>${ctx.reason}</span></div>`;

    const actual=ctx.actual || [];
    const objective=ctx.objective;
    const values=[0,ctx.realized,objective,refs.hwmReturn,refs.watchFloorReturn,...actual.map(point=>point.value)].filter(Number.isFinite);
    let min=Math.min(0,...values);
    let max=Math.max(1,...values);
    const range=Math.max(1,max-min);
    min-=range*.10;
    max+=range*.13;
    const span=Math.max(DAY_MS,config.end-config.start);
    const x=date=>pad.l+clamp((date-config.start)/span,0,1)*(width-pad.l-pad.r);
    const y=value=>pad.t+(max-value)/(max-min)*(height-pad.t-pad.b);
    const currentDate=new Date(clamp(today.getTime(),config.start.getTime(),config.end.getTime()));
    const currentX=x(currentDate);
    const startCapital=refs.startCapital;
    const rightMoney=value=>startCapital==null?null:startCapital*(1+value/100);

    const gridValues=Array.from({length:6},(_,index)=>min+(max-min)*index/5);
    const grids=gridValues.map(value=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-axis-label" x="${pad.l-9}" y="${y(value)+4}" text-anchor="end">${value.toFixed(Math.abs(max-min)>=100?0:1)}%</text>${startCapital==null?"":`<text class="chart-capital-axis" x="${width-pad.r+9}" y="${y(value)+4}">${money(rightMoney(value))}</text>`}</g>`).join("");

    const actualPoints=actual.map(point=>`${x(point.date)},${y(point.value)}`).join(" ");
    const actualArea=actual.length>1?`<path class="investor-actual-area" d="M ${x(actual[0].date)} ${y(0)} L ${actual.map(point=>`${x(point.date)} ${y(point.value)}`).join(" L ")} L ${x(actual[actual.length-1].date)} ${y(0)} Z"/>`:"";
    const actualLine=actual.length>1?`<polyline class="investor-actual-line" points="${actualPoints}"/>`:ctx.realized!=null?`<circle class="investor-current-dot" cx="${currentX}" cy="${y(ctx.realized)}" r="5"><title>${ctx.label} current cumulative return ${pct(ctx.realized)}</title></circle>`:"";
    const actualDots=actual.map(point=>`<circle class="investor-actual-point" cx="${x(point.date)}" cy="${y(point.value)}" r="2.4"><title>${fmtDate(point.date)} · actual ${pct(point.value)}</title></circle>`).join("");

    const objectivePoints=objective==null?"":Array.from({length:81},(_,index)=>{
      const fraction=index/80;
      return `${x(new Date(config.start.getTime()+span*fraction))},${y(objectiveAtFraction(objective,fraction))}`;
    }).join(" ");
    const objectiveLine=objective==null?"":`<polyline class="investor-target-line" points="${objectivePoints}"/>`;
    const objectiveToday=objective==null?null:objectiveAtFraction(objective,elapsedFraction(config.start,config.end,today));
    const gap=ctx.realized==null||objectiveToday==null?null:ctx.realized-objectiveToday;
    const gapMarker=gap==null?"":`<g class="chart-objective-gap"><line x1="${currentX-10}" x2="${currentX-10}" y1="${y(ctx.realized)}" y2="${y(objectiveToday)}"/><line x1="${currentX-14}" x2="${currentX-6}" y1="${y(ctx.realized)}" y2="${y(ctx.realized)}"/><line x1="${currentX-14}" x2="${currentX-6}" y1="${y(objectiveToday)}" y2="${y(objectiveToday)}"/><text x="${currentX-18}" y="${(y(ctx.realized)+y(objectiveToday))/2+4}" text-anchor="end">${gap>=0?"+":""}${gap.toFixed(2)} pts</text></g>`;

    const hwmBand=refs.hwmReturn==null||refs.watchFloorReturn==null?"":`<g class="chart-capital-protection"><rect x="${pad.l}" y="${y(refs.hwmReturn)}" width="${Math.max(0,currentX-pad.l)}" height="${Math.max(0,y(refs.watchFloorReturn)-y(refs.hwmReturn))}"/><line class="chart-hwm-line" x1="${pad.l}" x2="${currentX}" y1="${y(refs.hwmReturn)}" y2="${y(refs.hwmReturn)}"/><text class="chart-ref-label chart-hwm-label" x="${pad.l+6}" y="${y(refs.hwmReturn)-5}">HWM ${money(refs.hwm)}</text><line class="chart-watch-floor" x1="${pad.l}" x2="${currentX}" y1="${y(refs.watchFloorReturn)}" y2="${y(refs.watchFloorReturn)}"/><text class="chart-ref-label chart-floor-label" x="${pad.l+6}" y="${y(refs.watchFloorReturn)+13}">WATCH FLOOR ${money(refs.watchFloor)}</text></g>`;

    const dates=axisDates(config);
    const axis=dates.map((date,index)=>`<g class="chart-date-tick"><line x1="${x(date)}" x2="${x(date)}" y1="${height-pad.b}" y2="${height-pad.b+5}"/><text class="chart-axis-label chart-date-label" x="${x(date)}" y="${height-pad.b+20}" text-anchor="middle">${axisLabel(config,date,index,dates.length)}</text></g>`).join("");
    const todayMark=`<g class="chart-today"><line x1="${currentX}" x2="${currentX}" y1="${pad.t}" y2="${height-pad.b}"/><rect x="${clamp(currentX-55,pad.l,width-pad.r-110)}" y="6" width="110" height="20" rx="3"/><text x="${clamp(currentX,pad.l+55,width-pad.r-55)}" y="20" text-anchor="middle">AS OF · ${fmtShort(today)}</text></g>`;
    const rangeLabels=`<text class="chart-range-label" x="${pad.l}" y="${height-9}">${fmtDate(config.start)}</text><text class="chart-range-label" x="${width-pad.r}" y="${height-9}" text-anchor="end">${fmtDate(config.end)}</text>`;
    const axisTitles=`<text class="chart-axis-title" x="${pad.l}" y="${pad.t-12}">CUMULATIVE RETURN</text>${startCapital==null?"":`<text class="chart-axis-title chart-axis-title-right" x="${width-pad.r}" y="${pad.t-12}" text-anchor="end">IMPLIED CAPITAL</text>`}`;
    const coverage=`<g class="chart-coverage"><rect x="${width-pad.r-220}" y="${height-pad.b-27}" width="214" height="19" rx="3"/><text x="${width-pad.r-113}" y="${height-pad.b-14}" text-anchor="middle">${ctx.dataCoverage}</text></g>`;

    return `<svg class="investor-detail-chart investor-depth-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${config.label} Dusty Dragon capital and objective view. Actual return, absolute-return objective, high-water mark, drawdown-watch floor and as-of date are separated. Benchmark status is ${policy.benchmark?.status || "unselected"}.">${grids}${hwmBand}${actualArea}${objectiveLine}${actualLine}${actualDots}${gapMarker}${todayMark}${axis}${rangeLabels}${axisTitles}${coverage}</svg>`;
  }

  function syncControls() {
    valueLabel.textContent=labels[selected];
    slider.value=String(selected);
    slider.setAttribute("aria-valuetext",labels[selected]);
    buttons.forEach((button,index)=>{
      const active=index===selected;
      button.classList.toggle("active",active);
      button.setAttribute("aria-pressed",String(active));
    });
  }

  function render(config=builders[selected](),updateReadout=true) {
    if (rendering) return;
    rendering=true;
    const ctx=scopeContext(config);
    const refs=capitalReferences(ctx);
    const expanded=panel.classList.contains("expanded");
    chart.innerHTML=chartSvg(config,expanded,ctx,refs);

    if (updateReadout) {
      if (!ctx.available) {
        readout.innerHTML=`<div><b>—</b><span>ACTUAL</span></div><div><b>—</b><span>OBJECTIVE</span></div><div><b>—</b><span>VARIANCE</span></div><p>${ctx.reason}</p>`;
        depthRibbon.innerHTML=`<div><span>DATA COVERAGE</span><b>UNAVAILABLE</b><small>no synthetic aggregate</small></div>`;
      } else {
        const objectiveToday=ctx.objective==null?null:objectiveAtFraction(ctx.objective,elapsedFraction(config.start,config.end,today));
        const delta=ctx.realized==null||objectiveToday==null?null:ctx.realized-objectiveToday;
        readout.innerHTML=`
          <div><b>${pct(ctx.realized)}</b><span>REALIZED · AS OF ${fmtShort(today)}</span></div>
          <div><b>${pct(objectiveToday)}</b><span>OBJECTIVE AT AS-OF</span></div>
          <div><b class="${delta==null?"":delta>=0?"positive":"caution"}">${delta==null?"—":`${delta>=0?"+":""}${delta.toFixed(2)} pts`}</b><span>VARIANCE TO OBJECTIVE</span></div>
          <p>Actual capital path and objective are separate. The shaded HWM-to-watch-floor zone visualizes capital-protection headroom; it is not a loss forecast. Benchmark: ${policy.benchmark?.status || "UNSELECTED"}.</p>`;
        const endpointCapital=refs.startCapital==null||ctx.objective==null?null:refs.startCapital*(1+ctx.objective/100);
        depthRibbon.innerHTML=`
          <div><span>PERIOD START CAPITAL</span><b>${money(refs.startCapital)}</b><small>derived from current equity and cumulative return</small></div>
          <div><span>CURRENT HIGH-WATER MARK</span><b>${money(refs.hwm)}</b><small>${ctx.currentDd==null?"drawdown unavailable":`${ctx.currentDd.toFixed(2)}% current drawdown`}</small></div>
          <div><span>${drawdownWatchPct.toFixed(1)}% DRAWDOWN WATCH FLOOR</span><b>${money(refs.watchFloor)}</b><small>policy reference from current HWM</small></div>
          <div><span>HORIZON OBJECTIVE CAPITAL</span><b>${money(endpointCapital)}</b><small>${ctx.objective==null?"no scope-specific objective":`${pct(ctx.objective)} cumulative objective`}</small></div>`;
      }
    }
    rendering=false;
  }

  function cancelMorph() {
    morphToken+=1;
    if (morphTimer) clearTimeout(morphTimer);
    morphTimer=0;
  }
  function selectStatic(index) {
    cancelMorph();
    selected=clamp(index,0,builders.length-1);
    syncControls();
    render(builders[selected]());
  }
  function animateTo(index) {
    const destination=clamp(index,0,builders.length-1);
    if (destination===selected) return;
    if (noMotion()) { selectStatic(destination); return; }
    cancelMorph();
    const token=morphToken;
    const from=builders[selected]();
    const to=builders[destination]();
    const started=performance.now();
    selected=destination;
    syncControls();
    const step=()=>{
      if (token!==morphToken) return;
      if (noMotion()) { render(builders[selected]()); return; }
      const progress=clamp((performance.now()-started)/MORPH_MS,0,1);
      render(blendedConfig(from,to,progress),progress>=1);
      if (progress<1) morphTimer=setTimeout(step,16);
      else { morphTimer=0; render(builders[selected]()); }
    };
    step();
  }

  slider.addEventListener("input",event=>animateTo(Number(event.target.value)||0));
  buttons.forEach((button,index)=>button.addEventListener("click",()=>selectStatic(index)));
  const schedule=()=>setTimeout(()=>render(builders[selected]()),0);
  root.querySelector("#perfScope")?.addEventListener("change",schedule);
  root.querySelector("#perfEntity")?.addEventListener("change",schedule);
  root.querySelector("#perfExpandChart")?.addEventListener("click",schedule);
  window.addEventListener("dusty:performance-chart-resize",schedule);

  const policyObserver=new MutationObserver(()=>{
    if (noMotion()) cancelMorph();
    syncControls();
    render(builders[selected]());
  });
  policyObserver.observe(document.body,{attributes:true,attributeFilter:["class"]});

  window.DUSTY_PERFORMANCE_TIMEFRAME=Object.freeze({
    version:"3.5",
    objectiveType:"ABSOLUTE_RETURN_OBJECTIVE",
    compounding:"GEOMETRIC",
    graphSemantics:["ACTUAL","OBJECTIVE","AS_OF","HWM","DRAWDOWN_WATCH_FLOOR","BENCHMARK_IF_AVAILABLE"],
    syntheticHorizonActuals:false
  });

  syncControls();
  render();
})();