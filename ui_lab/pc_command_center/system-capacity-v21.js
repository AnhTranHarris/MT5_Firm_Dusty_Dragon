(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  const MOCK_PC = {
    cpu:["AMD Ryzen 7 7700","8 cores / 16 threads","Mock hardware profile"],
    gpu:["NVIDIA RTX 3060","12 GB VRAM","UI / research acceleration"],
    ram:["32 GB DDR5","~24 GB usable target","8 GB reserved for OS / safety"],
    storage:["1 TB NVMe SSD","PCIe 4.0","Database + market-data working set"],
    os:["Windows 11 Pro 64-bit","Mock build 24H2","MT5 host environment"],
    network:["1 GbE / Wi-Fi 6","Low-latency wired preferred","Broker connectivity"],
    runtime:["Python 3.11 x64","Dusty runtime","Mock UI profile"],
    display:["1920 × 1080","Spatial Full capable","Single-monitor baseline"]
  };

  /*
   * Capacity is a machine-scheduling envelope, never trading authority.
   * Production Auto should derive safe capacity from rolling telemetry (p95/p99
   * CPU pressure, memory/paging, disk latency, MT5 responsiveness, broker/data
   * latency, reconciliation backlog, thermals) and maintain reserve.
   *
   * Crucially, Auto activates min(provisioned eligible desks, proven-safe PC
   * capacity). A powerful PC does not manufacture desks or broker accounts.
   */
  const MODEL = {workloadBudget:55,mt5Cost:7,symbolCost:1.5,maxMt5:7,maxSymbols:24,provenSafeMt5:5,autoSymbols:12};
  let eligibleDeskCount = 1; // progressive first-launch mock: D01 only

  const hardware = document.createElement("article");
  hardware.className = "panel hardware-panel";
  hardware.innerHTML = `<header><span>PC HARDWARE SNAPSHOT</span><span>STATIC MOCK PROFILE</span></header><div class="hardware-grid">${Object.entries(MOCK_PC).map(([key,[name,detail,note]])=>`<div class="hardware-item"><span>${key.toUpperCase()}</span><b>${name}</b><small>${detail}<br>${note}</small></div>`).join("")}</div><div class="hardware-disclaimer">This UI lab does not inspect your real PC. Production Dusty should populate this panel from a constrained local, read-only hardware inventory service.</div>`;

  const capacity = document.createElement("article");
  capacity.className = "panel capacity-panel";
  capacity.innerHTML = `
    <div class="capacity-head"><div><span class="eyebrow">COMPUTE CAPACITY GOVERNOR</span><strong>MT5 DESK + SYMBOL CONCURRENCY ENVELOPE</strong></div><div class="capacity-mode" role="group" aria-label="Capacity mode"><button id="capacityAuto" class="active">AUTO</button><button id="capacityManual">MANUAL</button></div></div>
    <div class="capacity-summary"><div><span>ACTIVE MT5 DESKS</span><b id="capMt5">—</b></div><div><span>ACTIVE SYMBOLS</span><b id="capSymbols">—</b></div><div><span>TRADE ENVELOPES</span><b id="capTrades">—</b></div><div><span>COMPUTE HEADROOM</span><b id="capHeadroom">—</b></div></div>
    <div class="capacity-controls">
      <section class="capacity-control"><header><b>CONCURRENT MT5 DESKS / INSTANCES</b><strong id="mt5Value">1</strong></header><input id="mt5Slider" type="range" min="1" max="7" step="1" value="1" disabled><div class="range-scale"><span>1</span><span>1 desk = 1 account = 1 MT5 terminal instance</span><span>7</span></div></section>
      <section class="capacity-control"><header><b>CONCURRENT TRADED SYMBOLS</b><strong id="symbolValue">12</strong></header><input id="symbolSlider" type="range" min="1" max="24" step="1" value="12" disabled><div class="range-scale"><span>1</span><span>More symbols consume data/strategy compute</span><span>24</span></div></section>
    </div>
    <div class="capacity-budget"><div class="capacity-budget-bar"><div id="capacityBudgetFill" class="capacity-budget-fill"></div></div><div class="capacity-budget-labels"><span id="capacityLoad">WORKLOAD —</span><span>RESERVED OS / RISK / EXECUTION HEADROOM</span></div></div>
    <p id="capacityNote" class="capacity-note"></p>`;

  layout.prepend(capacity); layout.prepend(hardware);
  const $ = selector => capacity.querySelector(selector);
  const autoButton=$("#capacityAuto"),manualButton=$("#capacityManual"),mt5Slider=$("#mt5Slider"),symbolSlider=$("#symbolSlider");
  let mode="auto";
  const workload=(mt5,symbols)=>mt5*MODEL.mt5Cost+symbols*MODEL.symbolCost;
  const maxSymbolsFor=mt5=>Math.max(1,Math.min(MODEL.maxSymbols,Math.floor((MODEL.workloadBudget-mt5*MODEL.mt5Cost)/MODEL.symbolCost)));
  const maxMt5For=symbols=>Math.max(1,Math.min(MODEL.maxMt5,eligibleDeskCount,Math.floor((MODEL.workloadBudget-symbols*MODEL.symbolCost)/MODEL.mt5Cost)));
  const autoMt5=()=>Math.max(1,Math.min(MODEL.provenSafeMt5,eligibleDeskCount));

  function reconcile(changed){
    let mt5=Number(mt5Slider.value),symbols=Number(symbolSlider.value);
    if(mode==="auto"){mt5=autoMt5();symbols=Math.min(MODEL.autoSymbols,maxSymbolsFor(mt5));}
    else if(changed==="mt5")symbols=Math.min(symbols,maxSymbolsFor(mt5));
    else if(changed==="symbols")mt5=Math.min(mt5,maxMt5For(symbols));
    mt5=Math.min(mt5,Math.max(1,eligibleDeskCount));
    mt5Slider.value=mt5;symbolSlider.value=symbols;
    symbolSlider.max=maxSymbolsFor(mt5);mt5Slider.max=Math.max(1,maxMt5For(symbols));render();
  }

  function render(){
    const mt5=Number(mt5Slider.value),symbols=Number(symbolSlider.value),used=workload(mt5,symbols),headroom=Math.max(0,MODEL.workloadBudget-used),loadPct=Math.min(100,used/MODEL.workloadBudget*100),tradeEnvelopes=Math.min(symbols*2,mt5*6);
    $("#mt5Value").textContent=mt5;$("#symbolValue").textContent=symbols;$("#capMt5").textContent=`${mt5} active · ${eligibleDeskCount} provisioned`;$("#capSymbols").textContent=`${symbols} / ${MODEL.maxSymbols}`;$("#capTrades").textContent=`≤ ${tradeEnvelopes}`;$("#capHeadroom").textContent=`${Math.round(headroom/MODEL.workloadBudget*100)}%`;$("#capacityLoad").textContent=`MODELED WORKLOAD ${Math.round(loadPct)}%`;
    const fill=$("#capacityBudgetFill");fill.style.width=`${loadPct}%`;fill.classList.toggle("caution",loadPct>88);
    $("#capacityNote").innerHTML=mode==="auto"?`<b>AUTO:</b> PC proven-safe ceiling is ${MODEL.provenSafeMt5} MT5 desks, but only ${eligibleDeskCount} desk(s) are currently provisioned. Dusty therefore runs ${mt5}, preserving smooth weekly operating headroom. Hardware throughput never creates missing desks.`:`<b>MANUAL:</b> only provisioned desks may be selected. MT5 and symbol sliders share one compute envelope; decreasing capacity sheds newest/deepest eligible desks first, while desks with unresolved obligations must drain safely before terminal release.`;
  }

  function setMode(next){mode=next;const manual=mode==="manual";autoButton.classList.toggle("active",!manual);manualButton.classList.toggle("active",manual);mt5Slider.disabled=!manual;symbolSlider.disabled=!manual;reconcile();}
  autoButton.addEventListener("click",()=>setMode("auto"));manualButton.addEventListener("click",()=>setMode("manual"));mt5Slider.addEventListener("input",()=>reconcile("mt5"));symbolSlider.addEventListener("input",()=>reconcile("symbols"));

  // Small lab API lets the provisioning panel notify the capacity governor
  // without coupling either module to the other's DOM implementation.
  window.DUSTY_CAPACITY={setEligibleDeskCount(count){eligibleDeskCount=Math.max(1,Number(count)||1);reconcile();},getMode(){return mode;}};
  setMode("auto");
})();