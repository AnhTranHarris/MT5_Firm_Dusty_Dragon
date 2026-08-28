(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * UI-LAB ONLY — future native Windows implementation notes
   * ---------------------------------------------------------
   * PRODUCT CONTRACT
   * 1) Discovery and assignment are separate operations. Discovery may be
   *    automatic; assignment is human-confirmed and grants NO trade authority.
   * 2) One active Dusty desk = one broker account = one running MT5 terminal
   *    instance. A terminal is not READY until Dusty's existing account,
   *    DEMO/LIVE, permission, session-latch, reconciliation and execution
   *    verification succeeds.
   * 3) Layer 0 progressively bootstraps. One verified Demo desk is enough to
   *    operate. Six independent qualifying Demo proofs gate the L1 request;
   *    six simultaneous terminals are not a startup requirement.
   * 4) Capacity contraction is newest/deepest-first, but a desk with open market
   *    or reconciliation obligations enters DRAINING and retains its terminal
   *    until broker-safe release is proven.
   *
   * METAQUOTES — authoritative terminal binding/probing
   * - initialize(path, login=..., server=..., timeout=..., portable=...):
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
   *   Prefer EXPLICIT path after discovery. MetaQuotes says path-less initialize
   *   uses an undisclosed auto-discovery algorithm, which is ambiguous when many
   *   terminals exist.
   * - terminal_info() returns connected/trade_allowed/tradeapi_disabled/build,
   *   company, path, data_path, commondata_path, ping, etc. Use it to prove the
   *   selected terminal instance after initialize():
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py
   * - Terminal path/data path semantics:
   *   https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo/cterminalinfopath
   *   https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo/cterminalinfodatapath
   *
   * WINDOWS — candidate discovery, not trust
   * - App Paths registration:
   *   https://learn.microsoft.com/en-us/windows/win32/shell/app-registration
   * - MSI uninstall registration:
   *   https://learn.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key
   * - Running process inspection:
   *   https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-process
   * Production candidate sources should be bounded: stored Dusty assignments,
   * running terminal processes, registry registration, user-approved portable
   * directories, and only then bounded common-location scanning. Never hand the
   * frontend arbitrary filesystem access.
   *
   * DURABLE TERMINAL IDENTITY
   *   normalized_exe_path + normalized_data_path + portable_flag
   * Runtime process identity additionally includes PID + process start time.
   * Do not use filename, broker branding, or PID alone as identity.
   *
   * COMMUNITY DIAGNOSTIC NOTES — NEVER AUTO-APPLY
   * - Users commonly report separate install folders for simultaneous MT5:
   *   https://www.reddit.com/r/metatrader/comments/1denbb4/
   * - A 2025 community report attributes a high-instance ceiling to Windows
   *   desktop heap and suggests SharedSection registry changes:
   *   https://www.reddit.com/r/metatrader/comments/1nwqad6/
   *   Treat this only as a diagnostic lead. Dusty must NEVER modify desktop heap
   *   or similar system registry values automatically.
   *
   * Full implementation checklist and source hierarchy live in
   * PRODUCTION_HANDOFF_NOTES.md. Re-check source docs before production coding.
   */

  const terminals = [
    {id:"MT5-01",label:"IC Markets MetaTrader 5",path:"C:\\Program Files\\IC Markets MT5\\terminal64.exe",broker:"IC Markets",account:"Demo 90128411",environment:"DEMO",state:"ASSIGNED",desk:"D01"},
    {id:"MT5-02",label:"Pepperstone MetaTrader 5",path:"C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe",broker:"Pepperstone",account:"Not logged in",environment:"UNKNOWN",state:"AVAILABLE",desk:null},
    {id:"MT5-03",label:"MetaTrader 5 Portable",path:"D:\\Trading\\MT5-Portable-03\\terminal64.exe",broker:"—",account:"Not logged in",environment:"UNKNOWN",state:"AVAILABLE",desk:null},
    {id:"MT5-04",label:"FP Markets MetaTrader 5",path:"C:\\Program Files\\FP Markets MT5\\terminal64.exe",broker:"FP Markets",account:"Demo 228817",environment:"DEMO",state:"AVAILABLE",desk:null}
  ];

  const desks = [
    {id:"D01",layer:"L0",type:"Demo",state:"ACTIVE",proof:"PASS",terminal:"MT5-01",priority:1},
    {id:"D02",layer:"L0",type:"Demo",state:"NOT PROVISIONED",proof:"—",terminal:null,priority:2},
    {id:"D03",layer:"L0",type:"Demo",state:"NOT PROVISIONED",proof:"—",terminal:null,priority:3},
    {id:"D04",layer:"L0",type:"Demo",state:"NOT PROVISIONED",proof:"—",terminal:null,priority:4},
    {id:"D05",layer:"L0",type:"Demo",state:"NOT PROVISIONED",proof:"—",terminal:null,priority:5},
    {id:"D06",layer:"L0",type:"Demo",state:"NOT PROVISIONED",proof:"—",terminal:null,priority:6},
    {id:"G01",layer:"L1",type:"Generalist",state:"LOCKED",proof:"L0 1/6",terminal:null,priority:7}
  ];

  const qualification = document.createElement("article");
  qualification.className = "panel qualification-panel";
  qualification.innerHTML = `
    <header><span>LAYER 0 · PROGRESSIVE BOOTSTRAP</span><span>NORMAL · BUILDING EVIDENCE</span></header>
    <div class="bootstrap-summary">
      <div><span>ACTIVE DEMO DESKS</span><b id="bootActive">1</b><small>1 valid desk is enough to operate</small></div>
      <div><span>QUALIFIED PROOFS</span><b id="bootProofs">1 / 6</b><small>L1 request gate</small></div>
      <div><span>AVAILABLE TERMINALS</span><b id="bootAvailable">3</b><small>unassigned mock MT5 installs</small></div>
      <div><span>SYSTEM STATE</span><b class="state-NORMAL">NORMAL</b><small>missing desks are not faults</small></div>
    </div>
    <div id="bootstrapDeskRows" class="bootstrap-desk-rows"></div>
    <p class="bootstrap-note"><b>POLICY:</b> Dusty operates smoothly with the Demo capacity actually available. Six independently qualifying Demo desk proofs permit a Layer-1 request; they do not require six simultaneous terminals.</p>`;

  const terminalManager = document.createElement("article");
  terminalManager.className = "panel terminal-manager";
  terminalManager.innerHTML = `
    <header><span>MT5 TERMINAL MANAGER</span><button id="mockRescan" class="ghost tiny-button">RESCAN PC · MOCK</button></header>
    <div class="terminal-summary"><span><b id="terminalFound">4</b> discovered</span><span><b id="terminalAssigned">1</b> assigned</span><span><b id="terminalFree">3</b> available</span></div>
    <div id="terminalRows" class="terminal-rows"></div>
    <div class="terminal-assignment">
      <div><span class="eyebrow">ASSIGNMENT REQUEST</span><strong id="assignmentTitle">D02 · DEMO DESK</strong><small>Assignment requests provisioning only; verification remains mandatory.</small></div>
      <label>DESK<select id="assignmentDesk"></select></label>
      <label>AVAILABLE MT5<select id="assignmentTerminal"></select></label>
      <button id="assignMock">ASSIGN & VERIFY · MOCK</button>
    </div>
    <p id="assignmentStatus" class="terminal-status">Select an unprovisioned desk and an available terminal. No real filesystem, MT5, registry, process-control, or broker calls occur in this lab.</p>`;

  const provisioning = document.createElement("article");
  provisioning.className = "panel provisioning-panel";
  provisioning.innerHTML = `
    <header><span>DESK PROVISIONING / CAPACITY STATE</span><span>OLDEST CORE FIRST · NEWEST/DEEPEST SHEDS FIRST</span></header>
    <div class="provisioning-legend"><span class="state-ACTIVE">● ACTIVE</span><span class="state-DRAINING">● DRAINING</span><span class="state-PARKED">● CAPACITY-PARKED</span><span>○ NOT PROVISIONED</span><span>◆ LOCKED</span></div>
    <div id="provisioningRows" class="provisioning-rows"></div>
    <div class="provisioning-policy"><b>SAFE SHEDDING:</b> a desk with open positions, reconciliation work, or unresolved execution state must enter <b>DRAINING</b>. Resource policy may stop new exposure but cannot terminate the terminal until obligations are safe.</div>`;

  const capacity = layout.querySelector(".capacity-panel");
  const anchor = capacity?.nextSibling || layout.firstChild;
  layout.insertBefore(qualification, anchor);
  layout.insertBefore(terminalManager, anchor);
  layout.insertBefore(provisioning, anchor);

  const stateClass = state => `state-${String(state).replaceAll(" ","-")}`;
  const availableTerminals = () => terminals.filter(t => t.state === "AVAILABLE");
  const provisionableDesks = () => desks.filter(d => d.state === "NOT PROVISIONED");
  const assignedDeskCount = () => desks.filter(d => ["ACTIVE","DRAINING","CAPACITY-PARKED"].includes(d.state) && d.terminal).length;

  function renderDesks() {
    qualification.querySelector("#bootstrapDeskRows").innerHTML = desks.filter(d=>d.layer==="L0").map(d=>`<div class="bootstrap-desk-row"><b>${d.id}</b><span>${d.type}</span><span class="${stateClass(d.state)}">${d.state}</span><span>PROOF ${d.proof}</span><span>${d.terminal || "—"}</span></div>`).join("");
    const proofs = desks.filter(d=>d.layer==="L0"&&d.proof==="PASS").length;
    const active = desks.filter(d=>d.layer==="L0"&&d.state==="ACTIVE").length;
    qualification.querySelector("#bootProofs").textContent = `${proofs} / 6`;
    qualification.querySelector("#bootActive").textContent = active;
    qualification.querySelector("#bootAvailable").textContent = availableTerminals().length;
    provisioning.querySelector("#provisioningRows").innerHTML = desks.map(d=>`<div class="provisioning-row"><b>${d.id}</b><span>${d.layer}</span><span>${d.type}</span><span class="${stateClass(d.state)}">${d.state}</span><span>${d.terminal || "—"}</span><span>${d.layer==="L0" ? `Proof ${d.proof}` : d.state==="LOCKED" ? "Requires 6/6 L0 proofs" : "Eligible"}</span></div>`).join("");
    window.DUSTY_CAPACITY?.setEligibleDeskCount(assignedDeskCount());
  }

  function renderTerminals() {
    terminalManager.querySelector("#terminalRows").innerHTML = terminals.map(t=>`<div class="terminal-row"><b>${t.id}</b><span><strong>${t.label}</strong><small>${t.path}</small></span><span>${t.broker}<small>${t.account}</small></span><span>${t.environment}</span><span class="${stateClass(t.state)}">${t.state}${t.desk?` · ${t.desk}`:""}</span></div>`).join("");
    terminalManager.querySelector("#terminalFound").textContent = terminals.length;
    terminalManager.querySelector("#terminalAssigned").textContent = terminals.filter(t=>t.state==="ASSIGNED").length;
    terminalManager.querySelector("#terminalFree").textContent = availableTerminals().length;
    const deskSelect=terminalManager.querySelector("#assignmentDesk"),terminalSelect=terminalManager.querySelector("#assignmentTerminal"),currentDesk=deskSelect.value,currentTerminal=terminalSelect.value;
    deskSelect.innerHTML=provisionableDesks().map(d=>`<option value="${d.id}">${d.id} · ${d.layer} ${d.type}</option>`).join("")||`<option>No desk requests</option>`;
    terminalSelect.innerHTML=availableTerminals().map(t=>`<option value="${t.id}">${t.id} · ${t.label}</option>`).join("")||`<option>No available terminals</option>`;
    if([...deskSelect.options].some(o=>o.value===currentDesk))deskSelect.value=currentDesk;if([...terminalSelect.options].some(o=>o.value===currentTerminal))terminalSelect.value=currentTerminal;
    const selected=desks.find(d=>d.id===deskSelect.value);terminalManager.querySelector("#assignmentTitle").textContent=selected?`${selected.id} · ${selected.layer} ${selected.type.toUpperCase()} DESK`:"NO DESK REQUEST";terminalManager.querySelector("#assignMock").disabled=!selected||!availableTerminals().length;
  }

  function renderAll(){renderDesks();renderTerminals()}
  terminalManager.querySelector("#assignmentDesk").addEventListener("change",renderTerminals);
  terminalManager.querySelector("#mockRescan").addEventListener("click",()=>{terminalManager.querySelector("#assignmentStatus").textContent="Mock rescan complete: 4 terminal installations found. Production discovery must be performed by a constrained local service using bounded Windows candidate sources, then verified through explicit MetaQuotes terminal binding.";});
  terminalManager.querySelector("#assignMock").addEventListener("click",()=>{
    const desk=desks.find(d=>d.id===terminalManager.querySelector("#assignmentDesk").value),terminal=terminals.find(t=>t.id===terminalManager.querySelector("#assignmentTerminal").value);if(!desk||!terminal||terminal.state!=="AVAILABLE")return;
    terminal.state="ASSIGNED";terminal.desk=desk.id;desk.terminal=terminal.id;desk.state="ACTIVE";
    terminalManager.querySelector("#assignmentStatus").innerHTML=`<b>MOCK VERIFIED:</b> ${terminal.id} assigned to ${desk.id}. In production this state must not be reached until executable/data-path identity, account identity, server, environment, permissions, and session verification all pass.`;renderAll();
  });
  renderAll();
})();