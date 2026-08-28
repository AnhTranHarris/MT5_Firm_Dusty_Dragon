(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * EXTERNAL CAPABILITY REPOSITORIES — UI LAB / PRODUCTION HANDOFF NOTES
   * -------------------------------------------------------------------
   * Dusty may discover multiple independently installed implementations for
   * replaceable EXTERNAL capability roles. Current runtime contractor roles:
   *   VIBE   -> QUANT RESEARCH & STRATEGY ENGINE
   *   KRONOS -> TIME-SERIES FORECASTING ENGINE
   *
   * IMPORTANT ARCHITECTURE LINEAGE BOUNDARY
   * Conway-Research/automaton is NOT an operational contractor dependency.
   * Automaton is an architectural donor/reference: Dusty translates selected
   * evolutionary ideas (resource pressure, lineage, controlled challenger
   * evolution, persistence/memory and governance concepts) into Dusty-native
   * subsystems. It must not appear in the selectable contractor runtime pool.
   * The UI therefore reports it separately as ARCHITECTURE LINEAGE with status
   * ADAPTED INTO DUSTY CORE. A local reference clone may exist for engineering
   * study, but Dusty does not require or execute it to operate.
   *
   * PRODUCTION DISCOVERY CONTRACT (Windows helper/service, never browser UI)
   * 1) Search only bounded roots: Dusty-configured contractor roots, previously
   *    approved repo paths and user-selected development folders. Do NOT crawl C:\.
   * 2) Candidate marker may be a .git DIRECTORY OR .git FILE. Validate through:
   *      git -C <candidate> rev-parse --show-toplevel
   *      git -C <candidate> rev-parse --absolute-git-dir
   *      git -C <candidate> rev-parse --is-inside-work-tree
   *    https://git-scm.com/docs/git-rev-parse
   * 3) Capture canonical worktree, git-dir, HEAD, branch/detached state and all
   *    remotes through Git. Never assume remote 'origin' proves identity.
   *    https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository
   *    https://docs.github.com/en/get-started/git-basics/about-remote-repositories
   * 4) Classify runtime capability from a future Dusty adapter manifest plus
   *    adapter probe/signature, never merely folder/repository name.
   * 5) Verify adapter/API compatibility, expected entrypoints, pinned revision,
   *    dependency/environment health and isolation policy before activation.
   * 6) Discovery never auto-pulls, checks out, resets, installs or executes code.
   * 7) Contractors run out-of-process with bounded resources and no broker creds.
   *
   * WINDOWS / METAQUOTES NOTES
   * Windows Search is optional acceleration for indexed roots, not inventory:
   *   https://learn.microsoft.com/en-us/windows/win32/shell/search-protocol
   * MT5 identity remains owned by Dusty's Terminal Manager; external contractors
   * never infer/select terminals. MetaQuotes supports explicit initialize(path):
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
   *
   * COMMUNITY DIAGNOSTIC CONTEXT (non-authoritative)
   * .git file/worktree case: https://www.reddit.com/r/git/comments/17hpwha/
   * Multiple MT5 installs: https://www.reddit.com/r/metatrader/comments/1denbb4/
   */

  const ROLE_LABELS = Object.freeze({
    VIBE:"QUANT RESEARCH & STRATEGY ENGINE",
    KRONOS:"TIME-SERIES FORECASTING ENGINE"
  });

  const repos = [
    {id:"CTR-01",type:"VIBE",name:"HKUDS/Vibe-Trading",path:"D:\\Dusty\\contractors\\Vibe-Trading",origin:"https://github.com/HKUDS/Vibe-Trading.git",commit:"8f41c2a",state:"ACTIVE",selected:true},
    {id:"CTR-02",type:"VIBE",name:"Vibe-Trading-lab",path:"D:\\Research\\Vibe-Trading-lab",origin:"https://github.com/example/Vibe-Trading-lab.git",commit:"32aa17d",state:"AVAILABLE",selected:false},
    {id:"CTR-03",type:"KRONOS",name:"shiyu-coder/Kronos",path:"D:\\Dusty\\contractors\\Kronos",origin:"https://github.com/shiyu-coder/Kronos.git",commit:"6d901be",state:"ACTIVE",selected:true},
    {id:"CTR-04",type:"KRONOS",name:"Kronos-experimental",path:"C:\\Users\\Trader\\source\\Kronos-experimental",origin:"git@github.com:example/Kronos-experimental.git",commit:"d901ce4",state:"UNVERIFIED",selected:false}
  ];

  const lineage = [
    {id:"ARC-01",name:"Conway-Research/automaton",role:"EVOLUTIONARY ARCHITECTURE REFERENCE",integration:"ADAPTED INTO DUSTY CORE",runtime:"NO RUNTIME DEPENDENCY",local:"OPTIONAL REFERENCE CLONE"}
  ];

  const panel = document.createElement("article");
  panel.className = "panel contractor-manager";
  panel.innerHTML = `
    <header><span>EXTERNAL CAPABILITY REPOSITORIES</span><div class="contractor-actions"><span id="contractorState">2 ACTIVE</span><button type="button" id="contractorRescan" class="ghost tiny-button">RESCAN · MOCK</button></div></header>
    <div class="contractor-summary">
      <div><span>DISCOVERED REPOS</span><b id="contractorFound">4</b></div>
      <div><span>CAPABILITY ROLES</span><b id="contractorTypes">2</b></div>
      <div><span>SELECTED</span><b id="contractorSelected">2</b></div>
      <div><span>UNVERIFIED</span><b id="contractorUnverified" class="state-CAUTION">1</b></div>
    </div>
    <div id="contractorRows" class="contractor-repo-rows"></div>
    <p id="contractorNote" class="contractor-policy"><b>DISCOVERY ≠ TRUST:</b> Dusty may locate multiple implementations of the same external capability role. Human selection chooses the adapter candidate; compatibility verification and sandbox policy still gate activation. No external repository receives MT5 credentials or broker-write authority.</p>`;

  const lineagePanel = document.createElement("article");
  lineagePanel.className = "panel contractor-manager architecture-lineage";
  lineagePanel.innerHTML = `
    <header><span>ARCHITECTURE LINEAGE</span><span>REFERENCE · NON-RUNTIME</span></header>
    <div class="contractor-summary">
      <div><span>UPSTREAM REFERENCES</span><b>${lineage.length}</b></div>
      <div><span>RUNTIME DEPENDENCIES</span><b>0</b></div>
      <div><span>DUSTY-NATIVE</span><b class="state-NORMAL">YES</b></div>
      <div><span>EXECUTION AUTHORITY</span><b>NONE</b></div>
    </div>
    <div class="contractor-repo-rows">${lineage.map(item => `
      <div class="contractor-repo-row architecture-reference">
        <b>${item.id}</b>
        <span><strong>${item.name}</strong><small>${item.local}</small></span>
        <span class="contractor-origin"><strong class="contractor-role">${item.role}</strong><small>${item.runtime}</small></span>
        <span class="contractor-state-active">REFERENCE</span>
        <label><strong>${item.integration}</strong><small>NOT SELECTABLE</small></label>
      </div>`).join("")}</div>
    <p class="contractor-policy"><b>LINEAGE ≠ CONTRACTOR:</b> Automaton informs Dusty's evolutionary/corporate operating architecture. Production Dusty uses its own governed implementations; an Automaton checkout is optional engineering reference material and is never activated as a trading/research contractor.</p>`;

  const terminalManager = layout.querySelector(".terminal-manager");
  if (terminalManager) {
    terminalManager.insertAdjacentElement("afterend", panel);
    panel.insertAdjacentElement("afterend", lineagePanel);
  } else {
    layout.append(panel, lineagePanel);
  }

  const stateClass = state => `contractor-state-${state.toLowerCase()}`;
  const types = () => [...new Set(repos.map(repo => repo.type))];
  const roleLabel = repo => ROLE_LABELS[repo.type] || "SPECIALIST CAPABILITY ENGINE";

  function render() {
    panel.querySelector("#contractorFound").textContent = repos.length;
    panel.querySelector("#contractorTypes").textContent = types().length;
    panel.querySelector("#contractorSelected").textContent = repos.filter(repo => repo.selected).length;
    panel.querySelector("#contractorUnverified").textContent = repos.filter(repo => repo.state === "UNVERIFIED").length;
    panel.querySelector("#contractorState").textContent = `${repos.filter(repo => repo.selected && repo.state === "ACTIVE").length} ACTIVE`;
    panel.querySelector("#contractorRows").innerHTML = repos.map(repo => `
      <div class="contractor-repo-row" data-contractor-id="${repo.id}">
        <b>${repo.id}</b>
        <span><strong>${repo.name}</strong><small>${repo.path}</small></span>
        <span class="contractor-origin"><strong class="contractor-role">${roleLabel(repo)}</strong><small title="${repo.origin}">${repo.origin}</small></span>
        <span class="${stateClass(repo.state)}">${repo.state}</span>
        <label><select aria-label="Use ${repo.name} as ${roleLabel(repo)}"><option value="off"${repo.selected ? "" : " selected"}>AVAILABLE</option><option value="on"${repo.selected ? " selected" : ""}>SELECTED</option></select><small>HEAD ${repo.commit}</small></label>
      </div>`).join("");

    panel.querySelectorAll(".contractor-repo-row select").forEach(select => {
      select.addEventListener("change", event => {
        const row = event.target.closest(".contractor-repo-row");
        const repo = repos.find(item => item.id === row?.dataset.contractorId);
        if (!repo) return;
        if (event.target.value === "on" && repo.state === "UNVERIFIED") {
          event.target.value = "off";
          panel.querySelector("#contractorNote").innerHTML = `<b>SELECTION BLOCKED · MOCK:</b> ${repo.name} is discovered but UNVERIFIED. Production Dusty must validate its Git identity, ${roleLabel(repo)} adapter contract, compatibility and isolation policy before it can become selectable.`;
          return;
        }
        repo.selected = event.target.value === "on";
        repo.state = repo.selected ? "ACTIVE" : "AVAILABLE";
        render();
        window.DUSTY_SYSTEM_VIEW?.fit();
      });
    });
  }

  panel.querySelector("#contractorRescan").addEventListener("click", () => {
    panel.querySelector("#contractorNote").innerHTML = `<b>MOCK RESCAN COMPLETE:</b> ${repos.length} Git working trees across ${types().length} external capability roles. Architecture-lineage references are intentionally excluded from runtime contractor discovery. Production discovery will use configured roots + persisted paths and will not execute, pull, reset, install, or trust discovered code during the scan.`;
    window.DUSTY_SYSTEM_VIEW?.fit();
  });

  render();
})();
