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

  // Resource-capacity model for UX testing only. It expresses PC scheduling
  // capacity, never trading/risk authorization. Production values must be
  // calibrated from measured MT5, strategy, data, and broker workloads.
  const MODEL = {
    workloadBudget:55,
    mt5Cost:7,
    symbolCost:1.5,
    maxMt5:7,
    maxSymbols:24,
    autoMt5:5,
    autoSymbols:12
  };

  const hardware = document.createElement("article");
  hardware.className = "panel hardware-panel";
  hardware.innerHTML = `<header><span>PC HARDWARE SNAPSHOT</span><span>STATIC MOCK PROFILE</span></header><div class="hardware-grid">${Object.entries(MOCK_PC).map(([key,[name,detail,note]])=>`<div class="hardware-item"><span>${key.toUpperCase()}</span><b>${name}</b><small>${detail}<br>${note}</small></div>`).join("")}</div><div class="hardware-disclaimer">This UI lab does not inspect your real PC. Production Dusty should populate this panel from a local, read-only hardware inventory service.</div>`;

  const capacity = document.createElement("article");
  capacity.className = "panel capacity-panel";
  capacity.innerHTML = `
    <div class="capacity-head"><div><span class="eyebrow">COMPUTE CAPACITY GOVERNOR</span><strong>MT5 + SYMBOL CONCURRENCY ENVELOPE</strong></div><div class="capacity-mode" role="group" aria-label="Capacity mode"><button id="capacityAuto" class="active">AUTO</button><button id="capacityManual">MANUAL</button></div></div>
    <div class="capacity-summary">
      <div><span>MT5 TERMINALS</span><b id="capMt5">—</b></div>
      <div><span>ACTIVE SYMBOLS</span><b id="capSymbols">—</b></div>
      <div><span>TRADE ENVELOPES</span><b id="capTrades">—</b></div>
      <div><span>COMPUTE HEADROOM</span><b id="capHeadroom">—</b></div>
    </div>
    <div class="capacity-controls">
      <section class="capacity-control"><header><b>CONCURRENT MT5 ACCOUNTS</b><strong id="mt5Value">5</strong></header><input id="mt5Slider" type="range" min="1" max="7" step="1" value="5" disabled><div class="range-scale"><span>1</span><span>More terminals consume CPU/RAM/I/O</span><span>7</span></div></section>
      <section class="capacity-control"><header><b>CONCURRENT TRADED SYMBOLS</b><strong id="symbolValue">12</strong></header><input id="symbolSlider" type="range" min="1" max="24" step="1" value="12" disabled><div class="range-scale"><span>1</span><span>More symbols consume data/strategy compute</span><span>24</span></div></section>
    </div>
    <div class="capacity-budget"><div class="capacity-budget-bar"><div id="capacityBudgetFill" class="capacity-budget-fill"></div></div><div class="capacity-budget-labels"><span id="capacityLoad">WORKLOAD —</span><span>RESERVED OS / RISK / EXECUTION HEADROOM</span></div></div>
    <p id="capacityNote" class="capacity-note"></p>`;

  layout.prepend(capacity);
  layout.prepend(hardware);

  const $ = selector => capacity.querySelector(selector);
  const autoButton = $("#capacityAuto"), manualButton = $("#capacityManual");
  const mt5Slider = $("#mt5Slider"), symbolSlider = $("#symbolSlider");
  let mode = "auto";

  const workload = (mt5,symbols) => mt5 * MODEL.mt5Cost + symbols * MODEL.symbolCost;
  const maxSymbolsFor = mt5 => Math.max(1,Math.min(MODEL.maxSymbols,Math.floor((MODEL.workloadBudget - mt5 * MODEL.mt5Cost) / MODEL.symbolCost)));
  const maxMt5For = symbols => Math.max(1,Math.min(MODEL.maxMt5,Math.floor((MODEL.workloadBudget - symbols * MODEL.symbolCost) / MODEL.mt5Cost)));

  function reconcile(changed) {
    let mt5 = Number(mt5Slider.value);
    let symbols = Number(symbolSlider.value);
    if (mode === "auto") {
      mt5 = MODEL.autoMt5;
      symbols = MODEL.autoSymbols;
    } else if (changed === "mt5") {
      symbols = Math.min(symbols,maxSymbolsFor(mt5));
    } else if (changed === "symbols") {
      mt5 = Math.min(mt5,maxMt5For(symbols));
    }
    mt5Slider.value = mt5;
    symbolSlider.value = symbols;
    symbolSlider.max = maxSymbolsFor(mt5);
    mt5Slider.max = maxMt5For(symbols);
    render();
  }

  function render() {
    const mt5 = Number(mt5Slider.value);
    const symbols = Number(symbolSlider.value);
    const used = workload(mt5,symbols);
    const headroom = Math.max(0,MODEL.workloadBudget-used);
    const loadPct = Math.min(100,used/MODEL.workloadBudget*100);
    // A trade envelope is a scheduling estimate, not permission to place a
    // trade. Risk controls remain authoritative and can allow fewer or zero.
    const tradeEnvelopes = Math.min(symbols*2,mt5*6);

    $("#mt5Value").textContent = mt5;
    $("#symbolValue").textContent = symbols;
    $("#capMt5").textContent = `${mt5} / ${MODEL.maxMt5}`;
    $("#capSymbols").textContent = `${symbols} / ${MODEL.maxSymbols}`;
    $("#capTrades").textContent = `≤ ${tradeEnvelopes}`;
    $("#capHeadroom").textContent = `${Math.round(headroom/MODEL.workloadBudget*100)}%`;
    $("#capacityLoad").textContent = `MODELED WORKLOAD ${Math.round(loadPct)}%`;
    const fill = $("#capacityBudgetFill");
    fill.style.width = `${loadPct}%`;
    fill.classList.toggle("caution",loadPct>88);
    $("#capacityNote").innerHTML = mode === "auto"
      ? `<b>AUTO:</b> Dusty selects ${mt5} MT5 terminals and ${symbols} concurrently monitored/traded symbols for this mock PC, preserving compute reserve for risk, execution, reconciliation, data, and the GUI. The recommendation should be recalibrated from rolling weekly telemetry in production.`
      : `<b>MANUAL:</b> the sliders share one compute envelope. Increasing MT5 terminals can automatically reduce the maximum symbol count, and increasing symbols can reduce the maximum MT5 count. This governs machine capacity only; it cannot weaken portfolio risk limits or create trading authority.`;
  }

  function setMode(next) {
    mode = next;
    const manual = mode === "manual";
    autoButton.classList.toggle("active",!manual);
    manualButton.classList.toggle("active",manual);
    mt5Slider.disabled = !manual;
    symbolSlider.disabled = !manual;
    if (!manual) {
      mt5Slider.max = MODEL.maxMt5;
      symbolSlider.max = MODEL.maxSymbols;
    }
    reconcile();
  }

  autoButton.addEventListener("click",()=>setMode("auto"));
  manualButton.addEventListener("click",()=>setMode("manual"));
  mt5Slider.addEventListener("input",()=>reconcile("mt5"));
  symbolSlider.addEventListener("input",()=>reconcile("symbols"));
  setMode("auto");
})();
