(() => {
  "use strict";

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  const perf = data?.performance;
  if (!root || !perf) return;

  const policy = data.performancePolicy || {};
  const scopeMock = window.DUSTY_PERFORMANCE_SCOPE_MOCK;
  const FY_MONTH = 9;
  const DAY_MS = 86_400_000;
  const MORPH_MS = 460;
  const labels = ["MONTHLY", "QUARTERLY", "ANNUAL", "5 YEAR"];
  const horizonIds = ["month", "quarter", "year", "fiveYear"];
  const monthlyObjective = Number(policy.objective?.monthlyEffectivePct ?? data.firm?.monthlyTargetPct ?? 5);
  const drawdownWatchPct = Number(policy.risk?.drawdownWatchPct ?? 5);
  const asOf = parseUtc(perf.asOfUtc) || new Date();

  const panel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  const header = panel?.querySelector("header");
  if (!panel || !chart || !readout || !header) return;

  let selected = 0;
  let portfolio = 0;
  const entityByPortfolio = {1:"layer",2:"layer",3:"layer",4:"layer"};
  let rendering = false;
  let morphTimer = 0;
  let morphToken = 0;

  const title = header.querySelector("span:first-child");
  const scopeControls = document.createElement("div");
  scopeControls.className = "perf-capital-scope-controls";
  scopeControls.setAttribute("aria-label", "Capital chart scope");
  scopeControls.innerHTML = `
    <div class="perf-capital-scope-buttons" role="group" aria-label="Firm or portfolio">
      ${[0,1,2,3,4].map(index => `<button type="button" data-capital-scope="${index}" ${index===0?'class="active" aria-pressed="true"':'aria-pressed="false"'}>${index===0?"FIRM":`PORTFOLIO ${index}`}</button>`).join("")}
    </div>
    <select id="perfCapitalEntity" aria-label="Selected portfolio layer or desk" hidden>
      <option value="layer">LAYER</option>
      ${[1,2,3,4,5,6].map(index => `<option value="desk${index}">DESK ${index}</option>`).join("")}
    </select>
    <span id="perfCapitalScopeState" class="perf-capital-scope-state">FIRM · BROKER-RECONCILED SHAPE</span>`;
  title?.insertAdjacentElement("afterend", scopeControls);

  const controls = document.createElement("div");
  controls.className = "perf-timeframe-slider-control";
  controls.innerHTML = `<div class="perf-timeframe-heading"><span>REPORTING HORIZON</span><strong id="perfTimeframeValue">MONTHLY</strong></div><div class="perf-timeframe-slider-wrap"><input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0" aria-label="Investor reporting horizon" aria-valuetext="Monthly"><div class="perf-timeframe-slider-labels" aria-hidden="true">${labels.map(label=>`<span>${label}</span>`).join("")}</div></div>`;
  header.insertAdjacentElement("afterend", controls);

  const legend = document.createElement("div");
  legend.className = "perf-investor-legend";
  legend.innerHTML = `<span><i class="legend-actual-bar"></i>ACTUAL CAPITAL / RETURN</span><span><i class="legend-line"></i><b class="perf-objective-legend-label">ABSOLUTE-RETURN OBJECTIVE</b></span><span><i class="legend-today"></i>AS-OF DATE</span><span><i class="legend-hwm"></i>HIGH-WATER MARK</span><span><i class="legend-floor"></i>DRAWDOWN WATCH FLOOR</span><span class="perf-benchmark-state">BENCHMARK · ${policy.benchmark?.status || "UNSELECTED"}</span>`;
  controls.insertAdjacentElement("afterend", legend);

  const staticControls = document.createElement("div");
  staticControls.className = "perf-timeframe-static-controls";
  staticControls.setAttribute("role","group");
  staticControls.setAttribute("aria-label","Investor reporting horizon");
  staticControls.innerHTML = labels.map((label,index)=>`<button type="button" data-timeframe="${index}" ${index===0?'class="active" aria-pressed="true"':'aria-pressed="false"'}>${label}</button>`).join("");
  chart.insertAdjacentElement("afterend", staticControls);

  const ribbon = document.createElement("div");
  ribbon.className = "perf-capital-depth-ribbon";
  readout.insertAdjacentElement("afterend", ribbon);

  const slider = controls.querySelector("#perfTimeframeSlider");
  const valueLabel = controls.querySelector("#perfTimeframeValue");
  const timeButtons = [...staticControls.querySelectorAll("[data-timeframe]")];
  const scopeButtons = [...scopeControls.querySelectorAll("[data-capital-scope]")];
  const entitySelect = scopeControls.querySelector("#perfCapitalEntity");
  const scopeState = scopeControls.querySelector("#perfCapitalScopeState");
  const objectiveLegendLabel = legend.querySelector(".perf-objective-legend-label");
  const reduceMotionQuery = matchMedia("(prefers-reduced-motion: reduce)");

  function buildConfig(index = selected) {
    const id = horizonIds[index];
    let start;
    let end;
    let target;
    let note;
    if (id === "month") {
      start = utcDate(asOf.getUTCFullYear(), asOf.getUTCMonth(), 1);
      end = utcDate(asOf.getUTCFullYear(), asOf.getUTCMonth() + 1, 0, 23, 59, 59);
      target = compound(1);
      note = "1-MONTH EFFECTIVE OBJECTIVE";
    } else if (id === "quarter") {
      const bounds = quarterBounds(asOf);
      start = bounds.start;
      end = bounds.end;
      target = compound(3);
      note = `${fiscalYearLabel(bounds.fiscalStart)} · Q${bounds.quarter}`;
    } else if (id === "year") {
      start = fiscalYearStart(asOf);
      end = fiscalYearEnd(start);
      target = compound(12);
      note = `${fiscalYearLabel(start)} · OCT-SEP`;
    } else {
      start = fiscalYearStart(asOf);
      start = utcDate(start.getUTCFullYear() - 4, start.getUTCMonth(), 1);
      end = fiscalYearEnd(utcDate(start.getUTCFullYear() + 4, start.getUTCMonth(), 1));
      target = compound(60);
      note = `${fiscalYearLabel(start)} → FY${end.getUTCFullYear()}`;
    }
    return {id,label:labels[index],start,end,target,note};
  }

  function currentEntity() {
    if (portfolio === 0) {
      return {
        label:"FIRM",
        provenance:perf.historyProvenance || "READ_MODEL",
        snapshot:{equity:numberOrNull(data.firm?.equity),currentDrawdownPct:numberOrNull(data.firm?.drawdownPct)},
        horizonSeries:perf.horizonSeries,
        objectivePolicy:"FIRM"
      };
    }
    return scopeMock?.portfolios?.[portfolio]?.entities?.[entityByPortfolio[portfolio]] || null;
  }

  function context(config) {
    const entity = currentEntity();
    if (!entity) return {available:false,reason:"Selected scope read model is unavailable."};
    const raw = entity.horizonSeries?.[config.id];
    const actual = Array.isArray(raw) ? raw.map(normalizePoint).filter(Boolean).filter(point=>point.date>=config.start&&point.date<=asOf).sort((a,b)=>a.date-b.date) : [];
    if (!actual.length) return {available:false,reason:"No dated performance history exists for this scope and horizon."};
    const realized = actual.at(-1).value;
    return {
      available:true,
      label:entity.label,
      equity:numberOrNull(entity.snapshot?.equity),
      currentDd:numberOrNull(entity.snapshot?.currentDrawdownPct),
      realized,
      actual,
      objective:config.target,
      objectiveKind:portfolio===0?"SCOPE_OBJECTIVE":"FIRM_REFERENCE",
      provenance:entity.provenance || "READ_MODEL"
    };
  }

  function references(ctx) {
    if (!ctx.available || ctx.equity==null || ctx.realized==null || ctx.realized<=-100) return {};
    const startCapital = ctx.equity/(1+ctx.realized/100);
    const hwm = ctx.currentDd!=null&&ctx.currentDd>=0&&ctx.currentDd<100 ? ctx.equity/(1-ctx.currentDd/100) : null;
    const watchFloor = hwm==null?null:hwm*(1-drawdownWatchPct/100);
    return {startCapital,hwm,watchFloor,hwmReturn:hwm==null?null:(hwm/startCapital-1)*100,watchFloorReturn:watchFloor==null?null:(watchFloor/startCapital-1)*100};
  }

  function render(config = buildConfig(), updateReadout = true) {
    if (rendering) return;
    rendering = true;
    try {
      const ctx = context(config);
      const refs = references(ctx);
      chart.innerHTML = buildSvg(config, panel.classList.contains("expanded"), ctx, refs);
      if (updateReadout) renderReadout(config, ctx, refs);
    } finally { rendering = false; }
  }

  function buildSvg(config, expanded, ctx, refs) {
    if (!ctx.available) return `<div class="perf-chart-unavailable"><strong>CAPITAL PATH UNAVAILABLE</strong><span>${ctx.reason}</span></div>`;
    const width = expanded?1180:900;
    const height = expanded?470:300;
    const pad = {l:expanded?74:62,r:expanded?84:72,t:34,b:expanded?72:60};
    const values=[0,ctx.realized,ctx.objective,refs.hwmReturn,refs.watchFloorReturn,...ctx.actual.map(point=>point.value)].filter(Number.isFinite);
    let min=Math.min(0,...values),max=Math.max(1,...values);
    const range=Math.max(1,max-min); min-=range*.1; max+=range*.13;
    const span=Math.max(DAY_MS,config.end-config.start);
    const x=date=>pad.l+clamp((date-config.start)/span,0,1)*(width-pad.l-pad.r);
    const y=value=>pad.t+((max-value)/(max-min))*(height-pad.t-pad.b);
    const currentDate=new Date(clamp(asOf.getTime(),config.start.getTime(),config.end.getTime()));
    const currentX=x(currentDate), baselineY=y(0);
    const moneyAt=value=>refs.startCapital==null?null:refs.startCapital*(1+value/100);
    const grids=Array.from({length:6},(_,i)=>min+((max-min)*i)/5).map(value=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-axis-label" x="${pad.l-9}" y="${y(value)+4}" text-anchor="end">${value.toFixed(Math.abs(max-min)>=100?0:1)}%</text>${refs.startCapital==null?"":`<text class="chart-capital-axis" x="${width-pad.r+9}" y="${y(value)+4}">${money(moneyAt(value))}</text>`}</g>`).join("");
    const plotWidth=Math.max(1,currentX-pad.l);
    const centers=ctx.actual.map(point=>clamp(x(point.date),pad.l,currentX));
    const positiveGaps=centers.slice(1).map((center,index)=>center-centers[index]).filter(gap=>gap>0.05);
    const minGap=positiveGaps.length?Math.min(...positiveGaps):plotWidth;
    const densityWidth=(plotWidth/Math.max(1,ctx.actual.length))*.62;
    const barWidth=Math.max(1.25,Math.min(expanded?32:24,densityWidth,minGap*.68));
    const bars=ctx.actual.map((point,index)=>{const py=y(point.value),top=Math.min(py,baselineY),barHeight=Math.max(1,Math.abs(baselineY-py));const center=centers[index];const bx=clamp(center-barWidth/2,pad.l,width-pad.r-barWidth);return `<rect class="investor-actual-bar ${index===ctx.actual.length-1?"investor-current-bar":""}" x="${bx}" y="${top}" width="${barWidth}" height="${barHeight}" rx="2"><title>${formatDate(point.date)} · actual ${percent(point.value)}</title></rect>`;}).join("");
    const objectivePoints=Array.from({length:81},(_,i)=>{const f=i/80;return `${x(new Date(config.start.getTime()+span*f))},${y(objectiveAt(ctx.objective,f))}`;}).join(" ");
    const objectiveLine=`<polyline class="investor-target-line" points="${objectivePoints}"/>`;
    const objectiveToday=objectiveAt(ctx.objective,elapsed(config.start,config.end,asOf));
    const gap=ctx.realized-objectiveToday;
    const badgeWidth=110,badgeHeight=22,badgeX=clamp(currentX-badgeWidth/2,pad.l,width-pad.r-badgeWidth),badgeY=pad.t-badgeHeight;
    return `<svg class="investor-detail-chart investor-depth-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${escapeText(ctx.label)} ${config.label} capital history">${grids}${protectionBandFill(pad,currentX,y,refs)}${bars}${objectiveLine}${protectionReferences(pad,currentX,y,refs)}${gapMark(currentX,y,ctx.realized,objectiveToday,gap,pad,width)}<g class="chart-today"><rect x="${badgeX}" y="${badgeY}" width="${badgeWidth}" height="${badgeHeight}" rx="3"/><text x="${badgeX+badgeWidth/2}" y="${badgeY+15}" text-anchor="middle">AS OF · ${formatShortDate(asOf)}</text><line x1="${currentX}" x2="${currentX}" y1="${badgeY+badgeHeight-2}" y2="${height-pad.b}"/></g>${dateAxis(config,x,height,pad)}<text class="chart-range-label" x="${pad.l}" y="${height-9}">${formatDate(config.start)}</text><text class="chart-range-label" x="${width-pad.r}" y="${height-9}" text-anchor="end">${formatDate(config.end)}</text><text class="chart-axis-title chart-axis-title-left" x="${pad.l}" y="${pad.t-12}">CUMULATIVE RETURN</text></svg>`;
  }

  function renderReadout(config,ctx,refs){
    if(!ctx.available){readout.innerHTML=`<div><b>—</b><span>ACTUAL</span></div><div><b>—</b><span>OBJECTIVE</span></div><div><b>—</b><span>VARIANCE</span></div><p>${ctx.reason}</p>`;ribbon.innerHTML=`<div><span>DATA COVERAGE</span><b>UNAVAILABLE</b><small>no synthetic production fallback</small></div>`;return;}
    const objectiveToday=objectiveAt(ctx.objective,elapsed(config.start,config.end,asOf));
    const delta=ctx.realized-objectiveToday;
    const referenceOnly=ctx.objectiveKind==="FIRM_REFERENCE";
    readout.innerHTML=`<div><b>${percent(ctx.realized)}</b><span>${escapeText(ctx.label)} · AS OF ${formatShortDate(asOf)}</span></div><div><b>${percent(objectiveToday)}</b><span>${referenceOnly?"FIRM OBJECTIVE REFERENCE AT AS-OF":"OBJECTIVE AT AS-OF"}</span></div><div><b class="${delta>=0?"positive":"caution"}">${delta>=0?"+":""}${delta.toFixed(2)} pts</b><span>${referenceOnly?"VARIANCE TO FIRM REFERENCE":"VARIANCE TO OBJECTIVE"}</span></div><p>${ctx.provenance.startsWith("MOCK")?"Simulated UI-lab scope history. ":""}Green bars are observed cumulative performance for the selected scope. ${referenceOnly?"The yellow line remains the firm absolute-return objective as a comparison reference only; it is not a Portfolio/Desk target.":"The yellow line is the firm absolute-return objective."}</p>`;
    const endpoint=refs.startCapital==null?null:refs.startCapital*(1+ctx.objective/100);
    ribbon.innerHTML=`<div><span>PERIOD START CAPITAL</span><b>${money(refs.startCapital)}</b><small>scope read-model basis</small></div><div><span>CURRENT HIGH-WATER MARK</span><b>${money(refs.hwm)}</b><small>${ctx.currentDd==null?"drawdown unavailable":`${ctx.currentDd.toFixed(2)}% current drawdown`}</small></div><div><span>${drawdownWatchPct.toFixed(1)}% DRAWDOWN WATCH FLOOR</span><b>${money(refs.watchFloor)}</b><small>policy reference from scope HWM</small></div><div><span>${referenceOnly?"FIRM REFERENCE OBJECTIVE CAPITAL":"HORIZON OBJECTIVE CAPITAL"}</span><b>${money(endpoint)}</b><small>${percent(ctx.objective)} cumulative ${referenceOnly?"firm reference":"objective"}</small></div>`;
  }

  function protectionBandFill(pad,currentX,y,refs){if(refs.hwmReturn==null||refs.watchFloorReturn==null)return"";return `<g class="chart-capital-protection chart-capital-protection-fill"><rect x="${pad.l}" y="${y(refs.hwmReturn)}" width="${Math.max(0,currentX-pad.l)}" height="${Math.max(0,y(refs.watchFloorReturn)-y(refs.hwmReturn))}"/></g>`;}
  function protectionReferences(pad,currentX,y,refs){if(refs.hwmReturn==null||refs.watchFloorReturn==null)return"";return `<g class="chart-capital-protection chart-capital-protection-foreground"><line class="chart-hwm-line" x1="${pad.l}" x2="${currentX}" y1="${y(refs.hwmReturn)}" y2="${y(refs.hwmReturn)}"/><text class="chart-ref-label chart-hwm-label" x="${pad.l+6}" y="${y(refs.hwmReturn)-5}">HWM ${money(refs.hwm)}</text><line class="chart-watch-floor" x1="${pad.l}" x2="${currentX}" y1="${y(refs.watchFloorReturn)}" y2="${y(refs.watchFloorReturn)}"/><text class="chart-ref-label chart-floor-label" x="${pad.l+6}" y="${y(refs.watchFloorReturn)+13}">WATCH FLOOR ${money(refs.watchFloor)}</text></g>`;}
  function gapMark(currentX,y,realized,objectiveToday,gap,pad,width){if(gap==null)return"";const middle=(y(realized)+y(objectiveToday))/2,boxWidth=58,boxHeight=18,boxX=clamp(currentX-74,pad.l,width-pad.r-boxWidth),boxY=middle-boxHeight/2;return `<g class="chart-objective-gap"><line x1="${currentX-10}" x2="${currentX-10}" y1="${y(realized)}" y2="${y(objectiveToday)}"/><rect class="chart-objective-gap-box" x="${boxX}" y="${boxY}" width="${boxWidth}" height="${boxHeight}" rx="3"/><text class="chart-objective-gap-value" x="${boxX+boxWidth/2}" y="${boxY+12}" text-anchor="middle">${gap>=0?"+":""}${gap.toFixed(2)} pts</text></g>`;}
  function dateAxis(config,x,height,pad){const ticks=dateTicks(config);return ticks.map((date,index)=>`<g class="chart-date-tick"><line x1="${x(date)}" x2="${x(date)}" y1="${height-pad.b}" y2="${height-pad.b+5}"/><text class="chart-axis-label chart-date-label" x="${x(date)}" y="${height-pad.b+20}" text-anchor="middle">${dateLabel(config,date,index,ticks.length)}</text></g>`).join("");}

  function syncTime(){valueLabel.textContent=labels[selected];slider.value=String(selected);slider.setAttribute("aria-valuetext",labels[selected]);timeButtons.forEach((button,index)=>{const active=index===selected;button.classList.toggle("active",active);button.setAttribute("aria-pressed",String(active));});}
  function syncScope(){scopeButtons.forEach(button=>{const active=Number(button.dataset.capitalScope)===portfolio;button.classList.toggle("active",active);button.setAttribute("aria-pressed",String(active));});entitySelect.hidden=portfolio===0;if(portfolio!==0)entitySelect.value=entityByPortfolio[portfolio];const entity=currentEntity();scopeState.textContent=portfolio===0?"FIRM · CANONICAL READ MODEL":`${scopeMock?.portfolios?.[portfolio]?.label || `PORTFOLIO ${portfolio}`} · ${entity?.label || "UNAVAILABLE"} · UI-LAB SIMULATED`;if(objectiveLegendLabel)objectiveLegendLabel.textContent=portfolio===0?"ABSOLUTE-RETURN OBJECTIVE":"FIRM OBJECTIVE REFERENCE";}
  function emitScopeChanged(){window.dispatchEvent(new CustomEvent("dusty:performance-capital-scope-changed",{detail:{portfolio,entity:portfolio===0?"firm":entityByPortfolio[portfolio]}}));}
  function selectTime(index){cancelMorph();selected=clamp(index,0,3);syncTime();render(buildConfig());}
  function animateTo(index){const destination=clamp(index,0,3);if(destination===selected)return;if(noMotion()){selectTime(destination);return;}cancelMorph();const token=morphToken,from=buildConfig(selected),to=buildConfig(destination),started=performance.now();selected=destination;syncTime();const step=()=>{if(token!==morphToken)return;if(noMotion()){render(buildConfig());return;}const p=clamp((performance.now()-started)/MORPH_MS,0,1),t=smooth(p);const mixed={...to,start:new Date(lerp(from.start.getTime(),to.start.getTime(),t)),end:new Date(lerp(from.end.getTime(),to.end.getTime(),t)),target:lerp(from.target,to.target,t)};render(mixed,p>=1);if(p<1)morphTimer=setTimeout(step,16);else{morphTimer=0;render(buildConfig());}};step();}
  function selectScope(next){portfolio=clamp(next,0,4);syncScope();render(buildConfig());emitScopeChanged();}
  function cancelMorph(){morphToken+=1;if(morphTimer)clearTimeout(morphTimer);morphTimer=0;}
  function noMotion(){return document.body.classList.contains("render-no-motion")||reduceMotionQuery.matches;}

  slider.addEventListener("input",event=>animateTo(Number(event.target.value)||0));
  timeButtons.forEach((button,index)=>button.addEventListener("click",()=>selectTime(index)));
  scopeButtons.forEach(button=>button.addEventListener("click",()=>selectScope(Number(button.dataset.capitalScope)||0)));
  entitySelect.addEventListener("change",()=>{if(portfolio===0)return;entityByPortfolio[portfolio]=entitySelect.value;syncScope();render(buildConfig());emitScopeChanged();});
  root.querySelector("#perfExpandChart")?.addEventListener("click",()=>setTimeout(()=>render(buildConfig()),0));
  window.addEventListener("dusty:performance-chart-resize",()=>setTimeout(()=>render(buildConfig()),0));
  new MutationObserver(()=>{if(noMotion())cancelMorph();syncTime();syncScope();render(buildConfig());}).observe(document.body,{attributes:true,attributeFilter:["class"]});

  function dateTicks(config){if(config.id==="month")return[config.start,utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth(),8),utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth(),15),utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth(),22),config.end];if(config.id==="quarter")return[config.start,utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth()+1,1),utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth()+2,1),config.end];if(config.id==="year")return[0,2,4,6,8,10,11].map(month=>utcDate(config.start.getUTCFullYear(),config.start.getUTCMonth()+month,1));return[0,1,2,3,4].map(year=>utcDate(config.start.getUTCFullYear()+year,config.start.getUTCMonth(),1));}
  function dateLabel(config,date,index,count){const endpoint=index===0||index===count-1;if(config.id==="month")return endpoint?`${month(date)} ${date.getUTCDate()}`:String(date.getUTCDate()).padStart(2,"0");if(config.id==="quarter")return endpoint?formatShortDate(date):month(date);if(config.id==="year")return month(date);return `FY${fiscalYearEnd(date).getUTCFullYear()}`;}
  function quarterBounds(date){const fiscalStart=fiscalYearStart(date);const monthIndex=(date.getUTCFullYear()-fiscalStart.getUTCFullYear())*12+date.getUTCMonth()-fiscalStart.getUTCMonth();const q=Math.floor(monthIndex/3);return{start:utcDate(fiscalStart.getUTCFullYear(),fiscalStart.getUTCMonth()+q*3,1),end:utcDate(fiscalStart.getUTCFullYear(),fiscalStart.getUTCMonth()+q*3+3,0,23,59,59),quarter:q+1,fiscalStart};}
  function fiscalYearStart(date){return utcDate(date.getUTCMonth()>=FY_MONTH?date.getUTCFullYear():date.getUTCFullYear()-1,FY_MONTH,1);}
  function fiscalYearEnd(start){return utcDate(start.getUTCFullYear()+1,FY_MONTH,0,23,59,59);}
  function fiscalYearLabel(start){return `FY${fiscalYearEnd(start).getUTCFullYear()}`;}
  function utcDate(year,month,day,hour=0,minute=0,second=0){return new Date(Date.UTC(year,month,day,hour,minute,second));}
  function compound(months){return(Math.pow(1+monthlyObjective/100,months)-1)*100;}
  function objectiveAt(horizonReturn,fraction){return(Math.pow(1+Math.max(-.999999,horizonReturn/100),clamp(fraction,0,1))-1)*100;}
  function elapsed(start,end,at){return clamp((at-start)/Math.max(DAY_MS,end-start),0,1);}
  function normalizePoint(point){const date=parseUtc(point?.atUtc),value=Number(point?.cumulativeReturnPct);return date&&Number.isFinite(value)?{date,value}:null;}
  function parseUtc(raw){if(typeof raw!=="string"||!raw.endsWith("Z"))return null;const parsed=new Date(raw);return Number.isNaN(parsed.getTime())?null:parsed;}
  function numberOrNull(value){if(typeof value==="number")return Number.isFinite(value)?value:null;const parsed=Number(String(value??"").replace(/[^0-9.+-]/g,""));return Number.isFinite(parsed)?parsed:null;}
  function percent(value,digits=2){return value==null?"—":`${Number(value)>=0?"+":""}${Number(value).toFixed(digits)}%`;}
  function money(value){return value==null?"—":Number(value).toLocaleString(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0});}
  function month(date){return date.toLocaleDateString(undefined,{month:"short",timeZone:"UTC"}).toUpperCase();}
  function formatDate(date){return date.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}).toUpperCase();}
  function formatShortDate(date){return date.toLocaleDateString(undefined,{month:"short",day:"numeric",timeZone:"UTC"}).toUpperCase();}
  function clamp(value,min,max){return Math.min(max,Math.max(min,value));}
  function lerp(a,b,t){return a+(b-a)*t;}
  function smooth(t){return t*t*(3-2*t);}
  function escapeText(value){return String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));}

  window.DUSTY_PERFORMANCE_TIMEFRAME=Object.freeze({version:"3.9",scopeContract:"FIRM_PORTFOLIO_LAYER_DESK",historyContract:"DATED_CUMULATIVE_RETURN_SERIES_UTC",objectiveType:"ABSOLUTE_RETURN_OBJECTIVE_WITH_FIRM_REFERENCE_ON_CHILD_SCOPES",actualMark:"VERTICAL_BARS_NON_OVERLAP",compounding:"GEOMETRIC",syntheticProductionFallback:false});
  syncTime();syncScope();render();
})();