(() => {
  "use strict";
  const data = window.DUSTY_MOCK;
  if (!data) return;
  const root = document.querySelector("#performance .performance-layout");
  if (!root) return;

  const money = v => Number(v || 0).toLocaleString(undefined,{style:"currency",currency:"USD",maximumFractionDigits:0});
  const pct = v => `${Number(v)>=0?"+":""}${Number(v||0).toFixed(2)}%`;
  const desks = data.desks || [];
  const perf = data.performance || {};
  const hierarchy = data.hierarchy || {layers:[]};
  let lens = "investor";
  let scope = "firm";
  let layer = 1;
  let desk = desks[0]?.id || "G01";
  let chartExpanded = false;

  root.innerHTML = `
    <article class="panel perf-commandbar">
      <div><span class="eyebrow">PERFORMANCE</span><strong id="perfScopeTitle">DUSTY DRAGON · FIRM</strong><small id="perfScopeNote">Capital growth, downside and consistency at a glance.</small></div>
      <div class="perf-controls">
        <div class="segmented" aria-label="Performance lens"><button data-lens="investor" class="active">INVESTOR</button><button data-lens="quant">QUANT</button></div>
        <select id="perfScope" aria-label="Performance scope"><option value="firm">FIRM</option><option value="layer">PORTFOLIO / LAYER</option><option value="desk">DESK</option></select>
        <select id="perfEntity" aria-label="Selected portfolio or desk" hidden></select>
      </div>
    </article>
    <article class="panel perf-hero"><header><span>INVESTOR SUMMARY</span><span id="perfPeriod">MONTH TO DATE</span></header><div id="perfHeroMetrics" class="perf-hero-metrics"></div><div id="perfVerdict" class="perf-verdict"></div></article>
    <article class="panel perf-chart" id="perfChartPanel"><header><span>CAPITAL GROWTH</span><span class="perf-chart-actions"><span>ACTUAL vs TARGET PATH · MOCK</span><button id="perfExpandChart" type="button" aria-expanded="false" title="Expand investor chart">EXPAND ↗</button></span></header><div id="perfGrowthChart" class="perf-growth-chart"></div><div id="perfChartReadout" class="perf-chart-readout" hidden></div></article>
    <article class="panel perf-quality"><header>QUALITY OF RETURN</header><div id="perfQuality"></div></article>
    <article class="panel perf-contributors"><header><span>CONTRIBUTION</span><span id="perfContributionScope">BY DESK</span></header><div id="perfContributors"></div></article>
    <article class="panel perf-quant" id="perfQuant" hidden><header><span>QUANT DIAGNOSTICS</span><span>RISK-ADJUSTED / EXECUTION-AWARE</span></header><div id="perfQuantGrid" class="perf-quant-grid"></div></article>`;

  const $ = s => root.querySelector(s);
  const lensButtons = [...root.querySelectorAll("[data-lens]")];

  function layerName(n){return hierarchy.layers?.find(x=>x.layer===n)?.name || `Layer ${n}`;}
  function selectedDesk(){return desks.find(d=>d.id===desk) || desks[0] || {};}
  function entityMetrics(){
    if(scope === "desk"){
      const d=selectedDesk();
      return {title:`${d.id} · DESK`,note:`Single-desk performance · ${d.state||"UNKNOWN"}`,equity:d.equity||0,ret:d.mtd||0,dd:d.dd||0,pf:d.pf||0,sharpe:d.sharpe||0,risk:d.risk||0,win:Math.max(0,Math.min(100,54+(d.pf||1)*4)),pnl:(d.equity||0)*(d.mtd||0)/100};
    }
    if(scope === "layer"){
      const factor=Math.max(.45,1-(layer-1)*.09);
      return {title:`L${layer} · ${layerName(layer).toUpperCase()}`,note:"Portfolio aggregate · desks remain financially isolated",equity:data.firm.equity*factor,ret:data.firm.pnlMonthPct*factor,dd:data.firm.drawdownPct*(1+(layer-1)*.12),pf:1.71-(layer-1)*.06,sharpe:1.36-(layer-1)*.05,risk:data.firm.openRiskPct*factor,win:61.6-(layer-1)*1.4,pnl:3297.04*factor};
    }
    return {title:"DUSTY DRAGON · FIRM",note:"Capital growth, downside and consistency at a glance.",equity:data.firm.equity,ret:data.firm.pnlMonthPct,dd:data.firm.drawdownPct,pf:1.71,sharpe:1.36,risk:data.firm.openRiskPct,win:61.6,pnl:3297.04};
  }
  function metric(label,value,sub=""){return `<div class="perf-kpi"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`;}
  function populateEntity(){
    const e=$("#perfEntity");
    if(scope==="firm"){e.hidden=true;return;}
    e.hidden=false;
    if(scope==="layer") e.innerHTML=[0,1,2,3,4].map(n=>`<option value="${n}" ${n===layer?"selected":""}>L${n} · ${layerName(n)}</option>`).join("");
    else e.innerHTML=desks.map(d=>`<option value="${d.id}" ${d.id===desk?"selected":""}>${d.id} · ${d.state}</option>`).join("");
  }
  function chartSeries(ret){
    const source=perf.returns||[1,1.5,2,2.4,3];
    const actual=source.map((v,i,a)=>v*(ret/(a[a.length-1]||1)));
    const target=Number(data.firm.monthlyTargetPct||5);
    const goal=actual.map((_,i)=>target*(i+1)/actual.length);
    return {actual,goal,target};
  }
  function renderCompactChart(ret){
    const {actual,goal,target}=chartSeries(ret);
    const max=Math.max(target,...actual,1);
    $("#perfGrowthChart").innerHTML=actual.map((v,i)=>`<div class="growth-col"><i style="height:${Math.max(8,v/max*82)}%"></i><em style="bottom:${Math.max(4,goal[i]/max*82)}%"></em><span>${i===actual.length-1?pct(v):""}</span></div>`).join("");
  }
  function renderExpandedChart(ret){
    const {actual,goal,target}=chartSeries(ret);
    const width=1000,height=390,pad={l:62,r:30,t:24,b:48};
    const max=Math.max(target,...actual,1)*1.12;
    const x=i=>pad.l+i*((width-pad.l-pad.r)/(actual.length-1));
    const y=v=>height-pad.b-(v/max)*(height-pad.t-pad.b);
    const barW=Math.min(48,(width-pad.l-pad.r)/actual.length*.54);
    const grid=[0,1,2,3,4,5,6].filter(v=>v<=max+.2);
    const bars=actual.map((v,i)=>`<rect class="investor-actual-bar" x="${x(i)-barW/2}" y="${y(Math.max(0,v))}" width="${barW}" height="${Math.max(1,height-pad.b-y(Math.max(0,v)))}" rx="3"><title>Period ${i+1}: ${pct(v)}</title></rect>`).join("");
    const goalPoints=goal.map((v,i)=>`${x(i)},${y(v)}`).join(" ");
    const labels=actual.map((_,i)=>`<text class="chart-axis-label" x="${x(i)}" y="${height-20}" text-anchor="middle">P${i+1}</text>`).join("");
    const grids=grid.map(v=>`<g><line class="chart-gridline" x1="${pad.l}" x2="${width-pad.r}" y1="${y(v)}" y2="${y(v)}"/><text class="chart-axis-label" x="${pad.l-10}" y="${y(v)+4}" text-anchor="end">${v.toFixed(0)}%</text></g>`).join("");
    $("#perfGrowthChart").innerHTML=`<svg class="investor-detail-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Current cumulative performance bars compared with the monthly financial target path">${grids}${bars}<polyline class="investor-target-line" points="${goalPoints}"/>${goal.map((v,i)=>`<circle class="investor-target-point" cx="${x(i)}" cy="${y(v)}" r="4"><title>Target path ${pct(v)}</title></circle>`).join("")}${labels}</svg>`;
    $("#perfChartReadout").hidden=false;
    $("#perfChartReadout").innerHTML=`<div><b>${pct(ret)}</b><span>CURRENT MTD</span></div><div><b>${target.toFixed(2)}%</b><span>MONTHLY TARGET</span></div><div><b>${(ret-target)>=0?"+":""}${(ret-target).toFixed(2)} pts</b><span>TO TARGET</span></div><p><i class="legend-bar"></i> Bars = realized cumulative performance &nbsp; <i class="legend-line"></i> Line = financial target path. Target path is a planning objective, not a return forecast.</p>`;
  }
  function renderChart(ret){chartExpanded?renderExpandedChart(ret):renderCompactChart(ret);}
  function setChartExpanded(expanded){
    chartExpanded=Boolean(expanded);
    $("#perfChartPanel").classList.toggle("expanded",chartExpanded);
    $("#perfExpandChart").setAttribute("aria-expanded",String(chartExpanded));
    $("#perfExpandChart").textContent=chartExpanded?"CLOSE ×":"EXPAND ↗";
    if(!chartExpanded) $("#perfChartReadout").hidden=true;
    render();
  }
  function render(){
    const m=entityMetrics();
    $("#perfScopeTitle").textContent=m.title; $("#perfScopeNote").textContent=m.note;
    $("#perfHeroMetrics").innerHTML=[metric("EQUITY",money(m.equity),"current capital"),metric("MTD RETURN",pct(m.ret),"net performance"),metric("NET P&L",money(m.pnl),"after modeled costs"),metric("MAX DRAWDOWN",`${m.dd.toFixed(2)}%`,m.dd<5?"within tolerance":"review required")].join("");
    $("#perfVerdict").innerHTML=`<b>${m.ret>=0?"CAPITAL TREND POSITIVE":"CAPITAL TREND NEGATIVE"}</b><span>${m.ret>=data.firm.monthlyTargetPct?"Growth objective exceeded.":`${(data.firm.monthlyTargetPct-m.ret).toFixed(2)} pts below the 5% monthly objective.`} Risk remains ${m.risk<3?"contained":"elevated"}; drawdown is ${m.dd<3?"controlled":"material"}.</span>`;
    $("#perfQuality").innerHTML=[metric("WIN RATE",`${m.win.toFixed(1)}%`),metric("PROFIT FACTOR",m.pf.toFixed(2)),metric("SHARPE",m.sharpe.toFixed(2)),metric("OPEN RISK",`${m.risk.toFixed(2)}%`)].join("");
    const contrib=scope==="desk"?[{id:selectedDesk().id,pnl:m.pnl,pct:100}]:(perf.deskAttribution||[]);
    $("#perfContributors").innerHTML=contrib.map(x=>`<div class="perf-contrib"><b>${x.id}</b><div><i style="width:${Math.max(3,Math.abs(x.pct))}%"></i></div><span>${money(x.pnl)} · ${x.pct}%</span></div>`).join("");
    $("#perfContributionScope").textContent=scope==="firm"?"BY DESK":scope==="layer"?`L${layer} DESKS`:desk;
    $("#perfQuant").hidden=lens!=="quant";
    $("#perfQuantGrid").innerHTML=[metric("SORTINO",(m.sharpe*1.38).toFixed(2),"downside-adjusted"),metric("RECOVERY",(m.pf*2).toFixed(2),"return / drawdown"),metric("EXPECTANCY",`+${(m.pf*.158).toFixed(2)}R`,"per trade"),metric("PAYOFF",(1.72+(m.pf-1.5)*.2).toFixed(2),"avg win / loss"),metric("COST LOAD",scope==="firm"?"$126.88":"$21.15","fees + swap"),metric("TAIL RISK",`${(m.dd*.34).toFixed(2)}%`,"modeled ES contribution"),metric("RISK EFFICIENCY",(m.ret/Math.max(m.risk,.01)).toFixed(2),"return / open risk"),metric("STATE",m.dd<3?"HEALTHY":"WATCH","performance governance")].join("");
    renderChart(m.ret);
  }
  lensButtons.forEach(b=>b.addEventListener("click",()=>{lens=b.dataset.lens;lensButtons.forEach(x=>x.classList.toggle("active",x===b));render();}));
  $("#perfScope").addEventListener("change",e=>{scope=e.target.value;populateEntity();render();});
  $("#perfEntity").addEventListener("change",e=>{if(scope==="layer")layer=Number(e.target.value);else desk=e.target.value;render();});
  $("#perfExpandChart").addEventListener("click",()=>setChartExpanded(!chartExpanded));
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&chartExpanded)setChartExpanded(false);});
  populateEntity(); render();
})();
