(() => {
  const data = window.DUSTY_MOCK;
  const $ = selector => document.querySelector(selector);
  const money = value => value.toLocaleString(undefined,{style:"currency",currency:"USD"});
  const pct = value => `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  const metric = (label,value,note="") => `<div class="metric"><label>${label}</label><strong>${value}</strong><small>${note}</small></div>`;
  const kv = (label,value) => `<div class="kv"><span>${label}</span><span>${value}</span></div>`;
  const stateClass = state => state === "CAUTION" ? "caution" : state === "FAULT" ? "fault" : "normal";
  let pendingCommand = null;
  let stageDesk = null;

  $("#serviceStrip").innerHTML = data.services.map(([name,state]) => `<span class="service-pill"><b>${name}</b> <span class="state-${state}">● ${state}</span></span>`).join("");
  $("#firmMetrics").innerHTML = [
    metric("FIRM EQUITY",money(data.firm.equity),`${money(data.firm.pnl24h)} / 24H`),
    metric("MTD GROWTH",pct(data.firm.pnlMonthPct),`${data.firm.monthlyTargetPct.toFixed(1)}% objective`),
    metric("DRAWDOWN",`${data.firm.drawdownPct.toFixed(2)}%`,"NORMAL"),
    metric("OPEN RISK",`${data.firm.openRiskPct.toFixed(2)}%`,"CAUTION: USD cluster"),
    metric("FREE MARGIN",money(data.firm.freeMargin),"analytical aggregate"),
    metric("EXECUTION","READY 5/6","G06 fault-latched")
  ].join("");
  $("#firmTicker").innerHTML = [...data.ticker,...data.ticker].map(item => `<span>${item}</span>`).join("");
  $("#incidentList").innerHTML = data.incidents.map((item,index) => `<div class="incident" data-incident="${index}"><span class="severity ${item.severity}">${item.severity}</span> <b>${item.title}</b><p>${item.detail}</p></div>`).join("");
  $("#timeline").innerHTML = data.overnight.map(([time,event]) => `<div class="timeline-row"><time>${time}</time><span>${event}</span></div>`).join("");
  $("#researchDelta").innerHTML = [kv("Jobs completed",data.research.completed),kv("Candidates promoted",data.research.promoted),kv("Candidates rejected",data.research.rejected),kv("Holdout",`${data.research.holdoutPass}/${data.research.holdoutTotal} PASS`),kv("Challenge",`Day ${data.research.challengeDay}/${data.research.challengeLength}`)].join("");
  $("#rejectedSummary").innerHTML = [kv("Total rejected",data.rejected.total),kv("Portfolio capacity",data.rejected.portfolioCapacity),kv("Desk risk",data.rejected.deskRisk),kv("Correlation",data.rejected.correlation),kv("Avoided loss",money(data.rejected.avoidedLoss)),kv("Missed profit",money(data.rejected.missedProfit)),kv("Governance value",money(data.rejected.avoidedLoss-data.rejected.missedProfit))].join("");

  function renderFirmOrbit(){
    stageDesk = null;
    $("#stageTitle").textContent = "FIRM CORE / GENERALIST SYSTEM";
    $("#focusLabel").textContent = "ORBITAL VIEW";
    $("#backToFirm").hidden = true;
    $("#coreNode").innerHTML = `<span>DUSTY</span><strong>CORE</strong><small>OPERATIONAL</small>`;
    $("#coreNode").className = "core-node firm-node";
    $("#deskNodes").innerHTML = data.desks.map((desk,index) => `<button class="desk-node ${stateClass(desk.state)}" style="--start:${index*60}deg;--delay:-${index*2.7}s" data-orbit-desk="${desk.id}"><span>${desk.id}</span><b>${desk.state}</b></button>`).join("");
    $("#deskDossier").innerHTML = [metric("FIRM",data.firm.state,"click an orbiting desk to descend"),metric("DESKS","6 GENERALIST","independent capital"),metric("PORTFOLIO",pct(data.firm.pnlMonthPct),"MTD growth"),metric("RISK",`${data.firm.openRiskPct.toFixed(2)}%`,"open risk")].join("");
  }

  function descendIntoDesk(id){
    const desk = data.desks.find(item => item.id === id);
    if(!desk) return;
    const scene = $("#coreScene");
    scene.classList.add("zooming");
    window.setTimeout(() => {
      stageDesk = desk;
      $("#stageTitle").textContent = `${desk.id} / DESK SYSTEM`;
      $("#focusLabel").textContent = `${desk.state} · ${desk.graduation}`;
      $("#backToFirm").hidden = false;
      $("#coreNode").innerHTML = `<span>${desk.id}</span><strong>${desk.state}</strong><small>${desk.graduation}</small>`;
      $("#deskNodes").innerHTML = data.deskSystems.map(name => `<button class="subsystem-node"><span>${name}</span><b>${name === "RISK" ? `${desk.risk.toFixed(2)}%` : name === "GRADUATION" ? `${desk.progress}%` : "ACTIVE"}</b></button>`).join("");
      $("#deskDossier").innerHTML = [metric("EQUITY",money(desk.equity),"independent desk capital"),metric("TODAY",pct(desk.today),"realized + floating"),metric("MTD",pct(desk.mtd),`PF ${desk.pf.toFixed(2)} · Sharpe ${desk.sharpe.toFixed(2)}`),metric("RISK / DD",`${desk.risk.toFixed(2)}% / ${desk.dd.toFixed(2)}%`,desk.state)].join("");
      scene.classList.remove("zooming");
    },430);
  }

  $("#deskMatrix").innerHTML = data.desks.map(desk => `<div class="desk-tile" data-matrix-desk="${desk.id}"><b>${desk.id}</b> <span class="state-${desk.state}">● ${desk.state}</span><small>${desk.state === "FAULT" ? "EXECUTION BLOCKED" : `Equity ${money(desk.equity)}`}</small><div class="numbers"><span>MTD ${pct(desk.mtd)}</span><span>DD ${desk.dd.toFixed(2)}%</span><span>PF ${desk.pf.toFixed(2)}</span><span>Risk ${desk.risk.toFixed(2)}%</span></div></div>`).join("");
  renderFirmOrbit();

  $("#watchlistTable").innerHTML = `<table class="data-table"><thead><tr><th>Symbol</th><th>Last</th><th>Move</th><th>Spread</th><th>Regime</th></tr></thead><tbody>${data.watchlist.map(x => `<tr><td><b>${x.symbol}</b></td><td>${x.price}</td><td class="${x.move>=0?"positive":"negative"}">${pct(x.move)}</td><td>${x.spread}</td><td>${x.regime}</td></tr>`).join("")}</tbody></table>`;
  $("#decisionFeed").innerHTML = data.decisions.map(x => `<div class="decision-item"><b><span>${x.time} · ${x.desk} · ${x.symbol}</span><span class="${x.result.toLowerCase()}">${x.result}</span></b><p>Evidence score ${x.score}/100 · ${x.reason}</p></div>`).join("");
  $("#positionsTable").innerHTML = `<table class="data-table"><thead><tr><th>Desk / Symbol</th><th>Side</th><th>Entry</th><th>Mark</th><th>P&L</th><th>R</th><th>Risk</th><th>Age</th><th>State</th></tr></thead><tbody>${data.positions.map(x => `<tr><td>${x.desk} · <b>${x.symbol}</b></td><td>${x.side}</td><td>${x.entry}</td><td>${x.mark}</td><td class="${x.pnl>=0?"positive":"negative"}">${money(x.pnl)}</td><td>${x.r.toFixed(2)}R</td><td>${x.risk.toFixed(2)}%</td><td>${x.age}</td><td>${x.state}</td></tr>`).join("")}</tbody></table>`;
  $("#capacityStats").innerHTML = [kv("Open risk",`${data.riskStats.portfolioOpenRisk}%`),kv("Gross exposure",`${data.riskStats.grossExposure}%`),kv("USD contribution",`${data.riskStats.usdContribution}%`)].join("");

  function heatClass(value){return value>.25?"positive-risk":value<-.25?"negative-risk":"neutral-risk"}
  $("#riskHeatmap").innerHTML = data.riskHeatmap.map((x,index) => {const col=Math.max(2,Math.round(x.size/3.2));const row=Math.max(2,Math.round(x.size/5));return `<div class="heat-tile ${heatClass(x.value)}" style="grid-column:span ${col};grid-row:span ${row}" title="${x.label}: ${x.risk}% risk contribution"><small>${x.label}</small><strong>${x.symbol}</strong><span>${pct(x.value)}</span><small>RISK ${x.risk}%</small></div>`}).join("");
  $("#riskStats").innerHTML = [kv("Portfolio open risk",`${data.riskStats.portfolioOpenRisk}%`),kv("Gross exposure",`${data.riskStats.grossExposure}%`),kv("Net exposure",`${data.riskStats.netExposure}%`),kv("USD contribution",`${data.riskStats.usdContribution}%`),kv("Max pair correlation",data.riskStats.maxPairCorrelation),kv("Simultaneous loss freq",`${data.riskStats.simultaneousLossFreq}%`),kv("VaR 95",`${data.riskStats.var95}%`),kv("Expected shortfall",`${data.riskStats.expectedShortfall}%`)].join("");
  const corr=[1,.44,.31,.18,.52,.22,.44,1,.28,.36,.81,.19,.31,.28,1,.41,.24,.33,.18,.36,.41,1,.37,.29,.52,.81,.24,.37,1,.43,.22,.19,.33,.29,.43,1];
  $("#correlationMatrix").innerHTML = corr.map(v => `<div class="corr-cell" style="--a:${(.08+v*.42).toFixed(2)}">${v.toFixed(2)}</div>`).join("");

  $("#performanceStats").innerHTML = data.performance.stats.map(([label,value]) => `<div class="stat-block"><span>${label}</span><b>${value}</b></div>`).join("");
  $("#equityBars").innerHTML = data.performance.returns.map(v => `<div class="equity-bar" style="height:${20+v*18}%"><span>${v.toFixed(1)}%</span></div>`).join("");
  $("#deskAttribution").innerHTML = data.performance.deskAttribution.map(x => `<div class="attrib-row"><div class="attrib-head"><b>${x.id}</b><span>${money(x.pnl)} · ${x.pct}%</span></div><div class="bar-track"><div class="bar-fill" style="width:${x.pct*2.7}%"></div></div></div>`).join("");

  $("#researchQueue").innerHTML = data.researchQueue.map(x => `<div class="research-item"><header><b>${x.id} · ${x.title}</b><span>${x.stage}</span></header><p>Impact ${x.impact} · ${x.progress}% complete</p><div class="progress"><span style="width:${x.progress}%"></span></div></div>`).join("");
  $("#evidenceList").innerHTML = data.evidence.map(x => `<div class="evidence-item"><header><b>${x.state}</b><span>${x.confidence}% confidence</span></header><p>${x.claim}</p><small>${x.age} old</small></div>`).join("");
  $("#researchStats").innerHTML = [kv("Completed",data.research.completed),kv("Active",data.research.active),kv("Promoted",data.research.promoted),kv("Rejected",data.research.rejected),kv("Holdout",`${data.research.holdoutPass}/${data.research.holdoutTotal}`)].join("");

  const c=data.challenge;
  $("#challengeScore").innerHTML = `<div class="challenge-card"><h3>${c.target}</h3><div class="challenge-cols"><div><b>INCUMBENT</b>${kv("Return",pct(c.incumbent.ret))}${kv("DD",`${c.incumbent.dd}%`)}${kv("PF",c.incumbent.pf)}${kv("Sharpe",c.incumbent.sharpe)}</div><div><b>CHALLENGER</b>${kv("Return",pct(c.challenger.ret))}${kv("DD",`${c.challenger.dd}%`)}${kv("PF",c.challenger.pf)}${kv("Sharpe",c.challenger.sharpe)}</div></div><p>Day ${c.day}/${c.length} · Verdict: <b>${c.verdict}</b></p></div>`;

  $("#systemRows").innerHTML = `<div class="system-row head"><span>Component</span><span>State</span><span>Latency</span><span>CPU</span><span>RAM</span></div>${data.systems.map(x => `<div class="system-row"><b>${x.name}</b><span class="state-${x.state}">${x.state}</span><span>${x.latency}</span><span>${x.cpu}%</span><span>${x.ram} MB</span></div>`).join("")}`;
  $("#auditRows").innerHTML = data.audit.map(([time,event,level]) => `<div class="audit-row"><time>${time}</time><span>${event}</span><span class="${level==="CRITICAL"?"negative":level==="RISK"?"state-CAUTION":""}">${level}</span></div>`).join("");

  document.addEventListener("click",event => {
    const orbitTarget=event.target.closest("[data-orbit-desk]");
    if(orbitTarget) descendIntoDesk(orbitTarget.dataset.orbitDesk);
    const matrixTarget=event.target.closest("[data-matrix-desk]");
    if(matrixTarget) descendIntoDesk(matrixTarget.dataset.matrixDesk);
    const workspaceTarget=event.target.closest("[data-workspace]");
    if(workspaceTarget){document.querySelectorAll("[data-workspace]").forEach(button=>button.classList.toggle("active",button===workspaceTarget));document.querySelectorAll(".workspace").forEach(section=>section.classList.toggle("active",section.id===workspaceTarget.dataset.workspace));}
    const commandTarget=event.target.closest("[data-command]");
    if(commandTarget){pendingCommand=commandTarget.dataset.command;$("#dialogTitle").textContent=pendingCommand.replaceAll("_"," ");$("#dialogCopy").textContent="This UI laboratory has no Dusty Core connection. Confirming records a local mock audit event only; no broker, MT5 terminal, authorization lease, or execution path is touched.";$("#commandDialog").showModal();}
  });
  $("#backToFirm").addEventListener("click",()=>{const scene=$("#coreScene");scene.classList.add("zooming");window.setTimeout(()=>{renderFirmOrbit();scene.classList.remove("zooming")},360)});
  $("#confirmCommand").addEventListener("click",()=>{if(!pendingCommand)return;$("#auditTail").textContent=`Audit: ${pendingCommand} mock-confirmed at ${new Date().toLocaleTimeString()}`;pendingCommand=null;});
  function setMode(mode){const analytical=mode==="analytical";document.body.classList.toggle("analytical-mode",analytical);document.body.classList.toggle("spatial-mode",!analytical);$("#modeButton").textContent=analytical?"F3 SPATIAL":"F2 ANALYTICAL";$("#auditTail").textContent=`Audit: display mode changed to ${mode.toUpperCase()}`;}
  $("#modeButton").addEventListener("click",()=>setMode(document.body.classList.contains("analytical-mode")?"spatial":"analytical"));
  window.addEventListener("keydown",event=>{if(event.key==="F2"){event.preventDefault();setMode("analytical")}if(event.key==="F3"){event.preventDefault();setMode("spatial")}});
  function updateClock(){const time=new Intl.DateTimeFormat("en-US",{hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).format(new Date());$("#clock").textContent=`${time} LOCAL`;}
  updateClock();window.setInterval(updateClock,1000);
})();