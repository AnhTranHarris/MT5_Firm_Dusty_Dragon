(() => {
  const data = window.DUSTY_MOCK;
  if (!data) return;

  const trading = document.querySelector("#trading");
  const layout = trading?.querySelector(".trading-layout");
  if (!trading || !layout) return;

  const hierarchy = data.hierarchy || {layers:[],nodes:[]};
  const money = value => Number(value || 0).toLocaleString(undefined,{style:"currency",currency:"USD"});
  const pct = value => `${Number(value)>=0?"+":""}${Number(value||0).toFixed(2)}%`;
  const generalists = data.desks || [];
  const allDesks = [...generalists, ...hierarchy.nodes.filter(node => node.layer !== undefined && !generalists.some(d => d.id === node.id))];
  const layerName = layer => layer === 0 ? "Demo" : layer === 1 ? "Generalist" : layer === 2 ? "Trading Style" : layer === 3 ? "Sector" : "Symbol";

  const consoleEl = document.createElement("section");
  consoleEl.className = "trading-scope-console panel";
  consoleEl.innerHTML = `
    <div class="trading-scope-controls">
      <div><span class="scope-kicker">TRADING LENS</span><strong id="scopeTitle">FIRM</strong></div>
      <label>SCOPE<select id="tradingScope"><option value="firm">Firm</option><option value="portfolio">Portfolio</option><option value="desk">Desk</option></select></label>
      <label>TARGET<select id="tradingTarget" disabled><option value="FIRM">Dusty Dragon Firm</option></select></label>
      <div class="scope-note" id="scopeNote">Analytical aggregation across financially isolated desks.</div>
    </div>
    <div id="tradingScopeMetrics" class="trading-scope-metrics"></div>
    <div id="tradingScopeContext" class="trading-scope-context"></div>`;
  trading.insertBefore(consoleEl, layout);

  const scopeSelect = consoleEl.querySelector("#tradingScope");
  const targetSelect = consoleEl.querySelector("#tradingTarget");
  const title = consoleEl.querySelector("#scopeTitle");
  const note = consoleEl.querySelector("#scopeNote");
  const metrics = consoleEl.querySelector("#tradingScopeMetrics");
  const context = consoleEl.querySelector("#tradingScopeContext");

  const layerChildren = layer => {
    if (layer === 1) return generalists;
    return hierarchy.nodes.filter(node => node.layer === layer);
  };

  const average = (items,key,fallback=0) => {
    const values = items.map(item => Number(item[key])).filter(Number.isFinite);
    return values.length ? values.reduce((a,b)=>a+b,0)/values.length : fallback;
  };
  const sum = (items,key) => items.reduce((total,item)=>total + (Number(item[key]) || 0),0);
  const max = (items,key) => Math.max(0,...items.map(item=>Number(item[key])||0));

  function firmStats(){
    return {
      balance:data.firm.balance,
      equity:data.firm.equity,
      pnl24h:data.firm.pnl24h,
      mtd:data.firm.pnlMonthPct,
      dd:data.firm.drawdownPct,
      pf:1.71,
      sharpe:1.36,
      openRisk:data.firm.openRiskPct,
      marginUtil:18.4,
      grossExposure:data.riskStats?.grossExposure ?? 0,
      positions:data.positions?.length ?? 0,
      winRate:61.4,
      expectancy:.27,
      label:"Dusty Dragon Firm",
      sub:"All production layers · analytical aggregation",
      broker:"Multiple brokers",
      account:"Multiple MT5 account types",
      environment:"MIXED",
      state:"OPERATIONAL"
    };
  }

  function portfolioStats(layer){
    const items = layerChildren(layer);
    const equity = sum(items,"equity") || data.firm.equity * Math.max(.12,1-layer*.12);
    return {
      balance:equity + Math.max(80,items.length*23),
      equity,
      pnl24h:equity * average(items,"today",.35) / 100,
      mtd:average(items,"mtd",data.firm.pnlMonthPct),
      dd:max(items,"dd") || data.firm.drawdownPct,
      pf:average(items,"pf",1.62),
      sharpe:average(items,"sharpe",1.28),
      openRisk:Math.min(6.5,average(items,"risk",.55)*Math.max(1,Math.sqrt(items.length))),
      marginUtil:14 + layer*2.8,
      grossExposure:22 + layer*8.7,
      positions:Math.max(0,Math.round((data.positions?.length || 0) * Math.max(.18,1-layer*.14))),
      winRate:59.5 + layer*.7,
      expectancy:.21 + layer*.018,
      label:`L${layer} ${layerName(layer)} Portfolio`,
      sub:`${items.length} seeded desks · portfolio aggregate`,
      broker:"Multiple brokers",
      account:"Multiple MT5 account types",
      environment:layer===0?"DEMO":"MIXED",
      state:"NORMAL"
    };
  }

  function deskStats(desk){
    const equity = Number(desk.equity || 5000);
    return {
      balance:equity + 37,
      equity,
      pnl24h:equity * Number(desk.today || .2) / 100,
      mtd:Number(desk.mtd || 0),
      dd:Number(desk.dd || 0),
      pf:Number(desk.pf || 1.45),
      sharpe:Number(desk.sharpe || 1.15),
      openRisk:Number(desk.risk || .35),
      marginUtil:10 + Number(desk.risk || .35)*9,
      grossExposure:12 + Number(desk.risk || .35)*18,
      positions:(data.positions || []).filter(p=>p.desk===desk.id).length,
      winRate:53 + Number(desk.pf || 1.45)*5,
      expectancy:.12 + Number(desk.pf || 1.45)*.07,
      label:`${desk.id} · ${desk.name || "Desk"}`,
      sub:`Layer ${desk.layer ?? 1} · ${layerName(desk.layer ?? 1)} desk`,
      broker:desk.broker || "Mock broker",
      account:desk.accountType || "MT5",
      environment:desk.environment || "DEMO",
      state:desk.state || "NORMAL"
    };
  }

  function metric(label,value,detail=""){
    return `<div><span>${label}</span><b>${value}</b><small>${detail}</small></div>`;
  }

  function populateTargets(){
    const scope = scopeSelect.value;
    if (scope === "firm") {
      targetSelect.innerHTML = `<option value="FIRM">Dusty Dragon Firm</option>`;
      targetSelect.disabled = true;
      return;
    }
    targetSelect.disabled = false;
    if (scope === "portfolio") {
      targetSelect.innerHTML = [0,1,2,3,4].map(layer=>`<option value="L${layer}">L${layer} · ${layerName(layer)} Portfolio</option>`).join("");
      targetSelect.value = "L1";
      return;
    }
    targetSelect.innerHTML = allDesks.map(desk=>`<option value="${desk.id}">${desk.id} · ${desk.name || layerName(desk.layer ?? 1)}</option>`).join("");
    targetSelect.value = generalists[0]?.id || allDesks[0]?.id || "";
  }

  function currentStats(){
    if (scopeSelect.value === "firm") return firmStats();
    if (scopeSelect.value === "portfolio") return portfolioStats(Number(targetSelect.value.replace("L","")));
    return deskStats(allDesks.find(d=>d.id===targetSelect.value) || generalists[0] || {});
  }

  function filterPositions(){
    const positions = data.positions || [];
    if (scopeSelect.value !== "desk") return positions;
    return positions.filter(p=>p.desk===targetSelect.value);
  }

  function filterDecisions(){
    const decisions = data.decisions || [];
    if (scopeSelect.value !== "desk") return decisions;
    return decisions.filter(d=>d.desk===targetSelect.value);
  }

  function renderTables(stats){
    const positions = filterPositions();
    const positionsHost = document.querySelector("#positionsTable");
    if (positionsHost) positionsHost.innerHTML = `<table class="data-table"><thead><tr><th>Desk / Symbol</th><th>Side</th><th>Entry</th><th>Mark</th><th>P&L</th><th>R</th><th>Risk</th><th>Age</th></tr></thead><tbody>${positions.length?positions.map(x=>`<tr><td>${x.desk} · <b>${x.symbol}</b></td><td>${x.side}</td><td>${x.entry}</td><td>${x.mark}</td><td class="${x.pnl>=0?"positive":"negative"}">${money(x.pnl)}</td><td>${x.r.toFixed(2)}R</td><td>${x.risk.toFixed(2)}%</td><td>${x.age}</td></tr>`).join(""):`<tr><td colspan="8" class="empty-scope">No open mock positions for this selection.</td></tr>`}</tbody></table>`;

    const decisions = filterDecisions();
    const decisionHost = document.querySelector("#decisionFeed");
    if (decisionHost) decisionHost.innerHTML = decisions.length?decisions.map(x=>`<div class="decision-item"><b><span>${x.time} · ${x.desk} · ${x.symbol}</span><span>${x.result}</span></b><p>Evidence score ${x.score}/100 · ${x.reason}</p></div>`).join(""):`<div class="empty-scope">No recent mock decisions for this selection.</div>`;

    const chartHeader = document.querySelector(".chart-panel>header span:last-child");
    if (chartHeader) chartHeader.textContent = scopeSelect.value === "desk" ? targetSelect.value : scopeSelect.value === "portfolio" ? targetSelect.value : "FIRM";
    const watermark = document.querySelector(".chart-watermark");
    if (watermark) watermark.textContent = `${stats.label.toUpperCase()} · MOCK SUPERVISION PATH`;
  }

  function render(){
    const stats = currentStats();
    title.textContent = stats.label.toUpperCase();
    note.textContent = stats.sub;
    metrics.innerHTML = [
      metric("BALANCE",money(stats.balance),"ledger"),
      metric("EQUITY",money(stats.equity),money(stats.pnl24h)+" / 24H"),
      metric("MTD",pct(stats.mtd),"return"),
      metric("MAX DD",`${stats.dd.toFixed(2)}%`,"selected scope"),
      metric("PROFIT FACTOR",stats.pf.toFixed(2),"gross profit / gross loss"),
      metric("SHARPE",stats.sharpe.toFixed(2),"risk-adjusted"),
      metric("OPEN RISK",`${stats.openRisk.toFixed(2)}%`,"current"),
      metric("MARGIN UTIL",`${stats.marginUtil.toFixed(1)}%`,"capital use"),
      metric("GROSS EXP",`${stats.grossExposure.toFixed(1)}%`,"notional"),
      metric("OPEN POS",String(stats.positions),"positions"),
      metric("WIN RATE",`${stats.winRate.toFixed(1)}%`,"rolling"),
      metric("EXPECTANCY",`+${stats.expectancy.toFixed(2)}R`,"per trade")
    ].join("");
    context.innerHTML = `<span><b>STATE</b>${stats.state}</span><span><b>BROKER</b>${stats.broker}</span><span><b>ACCOUNT</b>${stats.account}</span><span><b>ENVIRONMENT</b>${stats.environment}</span><span><b>LENS</b>${scopeSelect.value.toUpperCase()}</span>`;
    renderTables(stats);
  }

  scopeSelect.addEventListener("change",()=>{populateTargets();render()});
  targetSelect.addEventListener("change",render);
  populateTargets();
  render();
})();
