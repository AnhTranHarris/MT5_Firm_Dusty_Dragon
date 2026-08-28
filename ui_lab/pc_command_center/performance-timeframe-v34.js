(() => {
  "use strict";

  /*
   * PERFORMANCE TIMEFRAME v3.4 — investor-grade objective reporting.
   * -----------------------------------------------------------------
   * Research-backed semantics:
   * - Green bars = realized Dusty return through the authoritative as-of date.
   * - Blue line = authoritative reporting cut (TODAY in UI Lab).
   * - Yellow dashed line = ex-ante ABSOLUTE RETURN OBJECTIVE PATH.
   *   It is NOT a forecast, guarantee, or external market benchmark.
   * - A true external benchmark must be selected separately, in advance, and be
   *   appropriate/measurable for the strategy before it is drawn on this chart.
   *
   * Objective mathematics:
   * - UI Lab currently stores a 5% effective monthly objective in mock data.
   * - Multi-period objectives are geometrically compounded, never added linearly:
   *     R(n months) = (1 + r_month)^n - 1
   * - Progress inside a selected horizon is also geometric:
   *     R(f) = (1 + R_horizon)^f - 1,  0 <= f <= 1
   *   This produces a mathematically consistent cumulative objective path.
   *
   * Display policy:
   * - SPATIAL FULL / REDUCED: four-stop slider with short numeric morph.
   * - NO MOTION / HIGH CONTRAST / OS reduced-motion: static buttons below chart.
   * - Presentation controls never mutate MT5, broker, risk, ledger or target policy.
   */

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data) return;

  const FISCAL_START_MONTH = 9; // October, U.S. federal fiscal convention.
  const MONTHLY_OBJECTIVE = Number(data.firm?.monthlyTargetPct || 5);
  const BENCHMARK_LABEL = data.performancePolicy?.benchmarkLabel || "EXTERNAL BENCHMARK · NOT SELECTED";
  const DAY_MS = 86400000;
  const MORPH_MS = 460;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = t => t * t * (3 - 2 * t);
  const endOfMonth = date => new Date(date.getFullYear(), date.getMonth() + 1, 0);
  const pct = value => `${Number(value) >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}%`;
  const fmtDate = date => date.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}).toUpperCase();
  const fmtShort = date => date.toLocaleDateString(undefined,{month:"short",day:"numeric"}).toUpperCase();

  function compoundMonths(months) {
    return (Math.pow(1 + MONTHLY_OBJECTIVE / 100, months) - 1) * 100;
  }

  function objectiveAtFraction(horizonPct, fraction) {
    return (Math.pow(1 + Math.max(-.999999, horizonPct / 100), clamp(fraction,0,1)) - 1) * 100;
  }

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
    const q = Math.floor(monthIndex / 3);
    return {
      start:new Date(fyStart.getFullYear(),fyStart.getMonth()+q*3,1),
      end:new Date(fyStart.getFullYear(),fyStart.getMonth()+q*3+3,0),
      q:q+1,
      fyStart
    };
  }

  function elapsedFraction(start, end, asOf = today) {
    const span = Math.max(DAY_MS, end.getTime() - start.getTime());
    return clamp((asOf.getTime() - start.getTime()) / span, 0, 1);
  }

  function shapedValues(finalValue, count) {
    const shape = [0.10,0.18,0.16,0.29,0.27,0.41,0.48,0.55,0.53,0.66,0.73,0.82,0.91,1];
    return Array.from({length:Math.max(1,count)},(_,index) => {
      const i = Math.round(index * (shape.length - 1) / Math.max(1,count - 1));
      return finalValue * shape[i];
    });
  }

  function monthConfig() {
    const start = new Date(today.getFullYear(),today.getMonth(),1);
    const end = endOfMonth(today);
    const count = Math.min(10,Math.max(1,today.getDate()));
    const values = shapedValues(Number(data.firm?.pnlMonthPct || 0),count);
    const actual = values.map((value,index)=>({
      date:new Date(start.getTime()+(today.getTime()-start.getTime())*index/Math.max(1,count-1)),value
    }));
    return {id:"month",label:"MONTHLY",short:"1M",start,end,target:compoundMonths(1),actual,note:"1-MONTH EFFECTIVE OBJECTIVE"};
  }

  function quarterConfig() {
    const {start,end,q,fyStart}=quarterBounds(today);
    const weeks=Math.min(13,Math.max(2,Math.ceil((today-start)/(7*DAY_MS))+1));
    const finalValue=Number(data.firm?.pnlMonthPct||0)+Number(data.firm?.pnlWeekPct||0)*2.55;
    const values=shapedValues(finalValue,weeks);
    const actual=values.map((value,index)=>({
      date:new Date(start.getTime()+(today.getTime()-start.getTime())*index/Math.max(1,weeks-1)),value
    }));
    return {id:"quarter",label:"QUARTERLY",short:`Q${q}`,start,end,target:compoundMonths(3),actual,note:`${fiscalYearLabel(fyStart)} · Q${q} · COMPOUNDED`};
  }

  function annualConfig() {
    const start=fiscalYearStart(today);
    const end=fiscalYearEnd(start);
    const months=Math.max(1,(today.getFullYear()-start.getFullYear())*12+today.getMonth()-start.getMonth()+1);
    const values=shapedValues(37.6,months); // deterministic UI-Lab mock until Core supplies fiscal YTD.
    const actual=values.map((value,index)=>{
      const date=new Date(start.getFullYear(),start.getMonth()+index+1,0);
      return {date:date>today?today:date,value};
    });
    return {id:"year",label:"ANNUAL",short:fiscalYearLabel(start),start,end,target:compoundMonths(12),actual,note:`${fiscalYearLabel(start)} · OCT-SEP · COMPOUNDED`};
  }

  function fiveYearConfig() {
    const start=fiscalYearStart(today);
    const end=new Date(start.getFullYear()+5,start.getMonth(),0);
    const months=Math.max(1,(today.getFullYear()-start.getFullYear())*12+today.getMonth()-start.getMonth()+1);
    const values=shapedValues(37.6,months);
    const actual=values.map((value,index)=>{
      const date=new Date(start.getFullYear(),start.getMonth()+index+1,0);
      return {date:date>today?today:date,value};
    });
    return {id:"fiveYear",label:"5 YEAR",short:"5Y",start,end,target:compoundMonths(60),actual,note:`${fiscalYearLabel(start)}-FY${fiscalYearEnd(new Date(start.getFullYear()+4,start.getMonth(),1)).getFullYear()} · COMPOUNDED`};
  }

  const builders=[monthConfig,quarterConfig,annualConfig,fiveYearConfig];
  const labels=["MONTHLY","QUARTERLY","ANNUAL","5 YEAR"];
  let selected=0;
  let renderedConfig=builders[0]();
  let rendering=false;
  let morphTimer=0;
  let morphToken=0;

  const panel=root.querySelector("#perfChartPanel");
  const chart=root.querySelector("#perfGrowthChart");
  const readout=root.querySelector("#perfChartReadout");
  if (!panel || !chart || !readout) return;

  const sliderControls=document.createElement("div");
  sliderControls.className="perf-timeframe-slider-control";
  sliderControls.innerHTML=`
    <div class="perf-timeframe-heading"><span>FISCAL REPORT VIEW</span><strong id="perfTimeframeValue">MONTHLY</strong></div>
    <div class="perf-timeframe-slider-wrap">
      <input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0" aria-label="Investor fiscal report timeframe" aria-valuetext="Monthly">
      <div class="perf-timeframe-slider-labels" aria-hidden="true">${labels.map(label=>`<span>${label}</span>`).join("")}</div>
    </div>`;
  panel.querySelector("header")?.insertAdjacentElement("afterend",sliderControls);

  const staticControls=document.createElement("div");
  staticControls.className="perf-timeframe-static-controls";
  staticControls.setAttribute("role","group");
  staticControls.setAttribute("aria-label","Investor fiscal report timeframe");
  staticControls.innerHTML=labels.map((label,index)=>`<button type="button" data-timeframe="${index}" ${index===0?'class="active" aria-pressed="true"':'aria-pressed="false"'}>${label}</button>`).join("");
  chart.insertAdjacentElement("afterend",staticControls);

  const slider=sliderControls.querySelector("#perfTimeframeSlider");
  const valueLabel=sliderControls.querySelector("#perfTimeframeValue");
  const buttons=[...staticControls.querySelectorAll("[data-timeframe]")];

  function noMotion() {
    return document.body.classList.contains("render-no-motion") || matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function currentScale() {
    const scope=root.querySelector("#perfScope")?.value||"firm";
    if (scope==="layer") {
      const layer=Number(root.querySelector("#perfEntity")?.value||1);
      return Math.max(.45,1-(layer-1)*.09);
    }
    if (scope==="desk") {
      const id=root.querySelector("#perfEntity")?.value;
      const desk=(data.desks||[]).find(item=>item.id===id);
      return desk?Math.max(.05,Number(desk.mtd||0)/Math.max(Number(data.firm?.pnlMonthPct||1),.01)):1;
    }
    return 1;
  }

  function sampleSeries(series,normalized) {
    if (!series.length) return 0;
    if (series.length===1) return Number(series[0].value||0);
    const position=clamp(normalized,0,1)*(series.length-1);
    const left=Math.floor(position);
    const right=Math.min(series.length-1,left+1);
    return lerp(Number(series[left].value||0),Number(series[right].value||0),position-left);
  }

  function blendedConfig(from,to,progress) {
    const t=smooth(progress);
    const start=new Date(lerp(from.start.getTime(),to.start.getTime(),t));
    const end=new Date(lerp(from.end.getTime(),to.end.getTime(),t));
    const actualEnd=new Date(Math.min(today.getTime(),end.getTime()));
    const count=Math.max(from.actual.length,to.actual.length,8);
    const actual=Array.from({length:count},(_,index)=>{
      const n=index/Math.max(1,count-1);
      return {date:new Date(lerp(start.getTime(),actualEnd.getTime(),n)),value:lerp(sampleSeries(from.actual,n),sampleSeries(to.actual,n),t)};
    });
    return {id:t<.5?from.id:to.id,label:t<.5?from.label:to.label,short:t<.5?from.short:to.short,start,end,target:lerp(from.target,to.target,t),actual,note:t<.5?from.note:to.note,transitioning:true};
  }

  function axisDates(config) {
    if (config.transitioning) {
      const span=config.end.getTime()-config.start.getTime();
      return [0,.25,.5,.75,1].map(f=>new Date(config.start.getTime()+span*f));
    }
    if (config.id==="month") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth(),8),new Date(config.start.getFullYear(),config.start.getMonth(),15),new Date(config.start.getFullYear(),config.start.getMonth(),22),config.end];
    if (config.id==="quarter") return [config.start,new Date(config.start.getFullYear(),config.start.getMonth()+1,1),new Date(config.start.getFullYear(),config.start.getMonth()+2,1),config.end];
    if (config.id==="year") return [0,2,4,6,8,10,11].map(month=>new Date(config.start.getFullYear(),config.start.getMonth()+month,1));
    return [0,1,2,3,4,5].map(year=>year===5?config.end:new Date(config.start.getFullYear()+year,config.start.getMonth(),1));
  }

  function axisLabel(config,date,index,total) {
    const endpoint=index===0||index===total-1;
    if (config.transitioning) return endpoint?fmtDate(date):date.toLocaleDateString(undefined,{month:"short",year:"2-digit"}).toUpperCase();
    if (config.id==="month") return endpoint?`${date.toLocaleDateString(undefined,{month:"short"}).toUpperCase()} ${date.getDate()}`:String(date.getDate()).padStart(2,"0");
    if (config.id==="quarter") return endpoint?fmtShort(date):date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
    if (config.id==="year") {
      const month=date.toLocaleDateString(undefined,{month:"short"}).toUpperCase();
      return endpoint?`${month} '${String(date.getFullYear()).slice(-2)}`:month;
    }
    return `FY${fiscalYearEnd(new Date(date.getFullYear(),FISCAL_START_MONTH,1)).getFullYear()}`;
  }

  function chartSvg(config,expanded) {
    const scale=currentScale();
    const actual=config.actual.map(point=>({date:point.date,value:point.value*scale})).filter(point=>point.date<=today);
    const target=config.target*scale;
    const width=expanded?1180:900;
    const height=expanded?450:280;
    const pad={l:expanded?72:58,r:expanded?34:24,t:28,b:expanded?70:58};
    const maximum=Math.max(target,...actual.map(point=>point.value),1)*1.14;
    const span=Math.max(DAY_MS,config.end-config.start);
    const x=date=>pad.l+clamp((date-config.start)/span,0,1)*(width-pad.l-pad.r);
    const y=value=>height-pad.b-(Math.max(0,value)/maximum)*(height-pad.t-pad.b);
    const currentX=x(new Date(clamp(today.getTime(),config.start.getTime(),config.end.getTime())));
    const barWidth=Math.max(4,Math.min(expanded?38:28,Math.max(1,currentX-pad.l)/Math.max(1,actual.length)*.62));
    const barX=point=>clamp(Math.min(x(point.date)-barWidth/2,currentX-barWidth),pad.l,width-pad.r-barWidth);

    const grids=Array.from({length:6},(_,index)=>maximum*index/5).map(value=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-axis-label" x="${pad.l-8}" y="${y(value)+4}" text-anchor="end">${value.toFixed(maximum>=100?0:1)}%</text></g>`).join("");
    const bars=actual.map(point=>`<rect class="investor-actual-bar" x="${barX(point)}" y="${y(point.value)}" width="${barWidth}" height="${Math.max(1,height-pad.b-y(point.value))}" rx="2"><title>${fmtDate(point.date)} · realized ${pct(point.value)}</title></rect>`).join("");
    const objectivePoints=Array.from({length:65},(_,index)=>{
      const fraction=index/64;
      const date=new Date(config.start.getTime()+span*fraction);
      return `${x(date)},${y(objectiveAtFraction(target,fraction))}`;
    }).join(" ");
    const dates=axisDates(config);
    const axis=dates.map((date,index)=>`<g class="chart-date-tick"><line x1="${x(date)}" x2="${x(date)}" y1="${height-pad.b}" y2="${height-pad.b+5}"/><text class="chart-axis-label chart-date-label" x="${x(date)}" y="${height-pad.b+19}" text-anchor="middle">${axisLabel(config,date,index,dates.length)}</text></g>`).join("");
    const todayMark=`<g class="chart-today"><line x1="${currentX}" x2="${currentX}" y1="${pad.t}" y2="${height-pad.b}"/><rect x="${clamp(currentX-55,pad.l,width-pad.r-110)}" y="4" width="110" height="20" rx="3"/><text x="${clamp(currentX,pad.l+55,width-pad.r-55)}" y="18" text-anchor="middle">TODAY · ${fmtShort(today)}</text></g>`;
    const range=`<text class="chart-range-label" x="${pad.l}" y="${height-8}">${fmtDate(config.start)}</text><text class="chart-range-label" x="${width-pad.r}" y="${height-8}" text-anchor="end">${fmtDate(config.end)}</text>`;

    return `<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${config.label} fiscal performance from ${fmtDate(config.start)} through ${fmtDate(config.end)}. Realized bars stop at ${fmtDate(today)}. Yellow dashed line is the compounded return objective, not a forecast or external benchmark.">${grids}${bars}<polyline class="investor-target-line" points="${objectivePoints}"/>${todayMark}${axis}${range}</svg>`;
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
    renderedConfig=config;
    const scale=currentScale();
    const actual=config.actual.filter(point=>point.date<=today);
    const realized=(actual[actual.length-1]?.value||0)*scale;
    const horizonObjective=config.target*scale;
    const objectiveToday=objectiveAtFraction(horizonObjective,elapsedFraction(config.start,config.end,today));
    const delta=realized-objectiveToday;
    const expanded=panel.classList.contains("expanded");

    chart.innerHTML=chartSvg(config,expanded);
    if (updateReadout) {
      readout.innerHTML=`
        <div><b>${pct(realized)}</b><span>REALIZED · AS OF ${fmtShort(today)}</span></div>
        <div><b>${pct(objectiveToday)}</b><span>OBJECTIVE AT TODAY</span></div>
        <div><b class="${delta>=0?"positive":"caution"}">${delta>=0?"+":""}${delta.toFixed(2)} pts</b><span>VS OBJECTIVE</span></div>
        <p><i class="legend-bar"></i> Actual through blue TODAY line &nbsp; <i class="legend-line"></i> Compounded return objective to ${fmtDate(config.end)} · ${config.note}. Not a forecast or guarantee. ${BENCHMARK_LABEL}.</p>`;
    }
    rendering=false;
  }

  function cancelMorph() {
    morphToken+=1;
    if (morphTimer) window.clearTimeout(morphTimer);
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
      if (progress<1) morphTimer=window.setTimeout(step,16);
      else { morphTimer=0; render(builders[selected]()); }
    };
    step();
  }

  slider.addEventListener("input",event=>animateTo(Number(event.target.value)||0));
  buttons.forEach((button,index)=>button.addEventListener("click",()=>selectStatic(index)));

  const schedule=()=>window.setTimeout(()=>render(builders[selected]()),0);
  root.querySelector("#perfScope")?.addEventListener("change",schedule);
  root.querySelector("#perfEntity")?.addEventListener("change",schedule);
  root.querySelector("#perfExpandChart")?.addEventListener("click",schedule);
  root.querySelectorAll("[data-lens]").forEach(button=>button.addEventListener("click",schedule));

  const chartObserver=new MutationObserver(()=>{
    if (!rendering && !chart.querySelector(".chart-today")) schedule();
  });
  chartObserver.observe(chart,{childList:true});

  const policyObserver=new MutationObserver(()=>{
    if (noMotion()) cancelMorph();
    syncControls();
    render(builders[selected]());
  });
  policyObserver.observe(document.body,{attributes:true,attributeFilter:["class"]});

  window.DUSTY_PERFORMANCE_TIMEFRAME=Object.freeze({
    version:"3.4",
    objectiveType:"ABSOLUTE_RETURN_OBJECTIVE",
    compounding:"GEOMETRIC",
    basePeriod:"MONTHLY",
    baseRatePct:MONTHLY_OBJECTIVE,
    benchmarkSelected:Boolean(data.performancePolicy?.benchmarkLabel)
  });

  syncControls();
  render(renderedConfig);
})();