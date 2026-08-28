(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * EXTERNAL CAPABILITY REPOSITORIES — UI LAB / PRODUCTION HANDOFF NOTES
   * -------------------------------------------------------------------
   * Historical Dusty architecture explicitly planned a replaceable contractor
   * boundary that could admit Vibe, Kronos, Qlib, Nautilus and LEAN without
   * redefining Dusty's canonical financial model. Barter and vn.py were retained
   * as research/reference candidates rather than production dependencies.
   *
   * CAPABILITY ROLES
   *   VIBE / QLIB -> QUANT RESEARCH & STRATEGY ENGINE
   *   KRONOS      -> TIME-SERIES FORECASTING ENGINE
   *   NAUTILUS    -> MARKET SIMULATION & TRADING ENGINE
   *   LEAN        -> INDEPENDENT BACKTEST & VALIDATION ENGINE
   *
   * IMPORTANT ARCHITECTURE LINEAGE BOUNDARY
   * Conway-Research/automaton is NOT an operational contractor dependency.
   * Automaton is an architectural donor/reference whose useful evolutionary
   * mechanisms are translated into Dusty-native subsystems.
   *
   * SAFE REPOSITORY DISCOVERY — PRODUCTION WINDOWS APP
   * --------------------------------------------------
   * Discovery belongs in a constrained Windows helper/service, not the GUI.
   * Search only configured/persisted/user-approved roots. Never recursively
   * crawl the whole system drive. A Git worktree may expose .git as a FILE or
   * DIRECTORY, so validate through Git rather than filesystem assumptions:
   *   git -C <candidate> rev-parse --show-toplevel
   *   git -C <candidate> rev-parse --absolute-git-dir
   *   git -C <candidate> rev-parse --is-inside-work-tree
   * Official Git docs: https://git-scm.com/docs/git-rev-parse
   * GitHub clone/remote docs:
   *   https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository
   *   https://docs.github.com/en/get-started/git-basics/about-remote-repositories
   * Community reminder: worktrees isolate files, NOT ports, databases, .env or
   * runtime services. Every active implementation needs its own runtime identity,
   * environment and resource namespace.
   *
   * SAFE CONTRACTOR SWITCHING — NEVER "CHANGE PATH AND HOPE"
   * ---------------------------------------------------------
   * Production switching must be a transaction-like state machine:
   *   1. DISCOVER candidate; do not execute it.
   *   2. VERIFY Git identity + pinned commit + Dusty adapter/schema version.
   *   3. PREPARE isolated runtime (dedicated venv/container/process identity).
   *   4. PROBE health/capabilities against read-only golden data.
   *   5. QUIESCE old contractor: stop NEW jobs, let current job finish/cancel
   *      safely, preserve result/provenance, and wait for zero owned work.
   *   6. START candidate as STANDBY with ZERO broker/MT5 authority.
   *   7. Run compatibility + deterministic golden-result tests.
   *   8. Atomically flip Dusty's contractor-registry active implementation.
   *   9. Observe probation heartbeat/error/resource window.
   *  10. On any failure, flip registry back to the previous pinned implementation.
   *
   * Never overwrite an active contractor installation in place. New upstream
   * revisions become separate immutable candidates identified by repo identity,
   * commit SHA, adapter version, environment fingerprint and schema version.
   * "latest" is never an approved production version.
   *
   * WINDOWS PROCESS CONTAINMENT
   * ---------------------------
   * Use distinct OS processes. Consider Windows Job Objects to track a contractor
   * process tree, account CPU/memory and terminate the whole owned process group
   * during rollback/shutdown. Job Objects associate child processes by default:
   *   https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
   * Do not share mutable .venv/site-packages between alternative implementations.
   * Community experience with parallel Git worktrees repeatedly reports collisions
   * from shared ports/services/environments; repository isolation alone is not
   * runtime isolation.
   *
   * CONTRACTOR DATA/STATE COMPATIBILITY
   * -----------------------------------
   * Dusty owns canonical schemas and durable state. Contractors receive versioned
   * jobs and immutable dataset references and return versioned Evidence objects.
   * They never own the authoritative desk, account, risk or execution ledger.
   * A switch therefore swaps an ADAPTER/WORKER, not Dusty's data model.
   * Persist for every result: contractor role, implementation id, Git SHA,
   * environment fingerprint, adapter/schema version, dataset SHA and job id.
   * Old evidence remains attributable to the old implementation after switching.
   *
   * METAQUOTES BOUNDARY
   * -------------------
   * Switching a research/forecast/validation repo must never alter MT5 bindings.
   * Dusty's Terminal Manager owns explicit MT5 executable/account identity.
   * MetaQuotes supports initialize(path, ...) and recommends explicit path to
   * remove ambiguity when multiple terminals exist; terminal_info() exposes the
   * connected terminal path/data_path/settings for post-bind verification:
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5terminalinfo_py
   * Contractor processes receive no broker credentials and cannot initialize an
   * arbitrary MT5 terminal. ApprovedOrder remains a Dusty-only authority object.
   *
   * REFERENCES / RESEARCH-ONLY CANDIDATES
   * --------------------------------------
   * Barter and vn.py were retained historically as implementation/reference
   * candidates. They stay outside the active contractor pool until a deliberate
   * architecture review assigns a canonical Dusty capability and adapter.
   *
   * Re-check all upstream/current documentation before native implementation.
   */

  const ROLE_LABELS = Object.freeze({
    RESEARCH:"QUANT RESEARCH & STRATEGY ENGINE",
    FORECAST:"TIME-SERIES FORECASTING ENGINE",
    SIMULATION:"MARKET SIMULATION & TRADING ENGINE",
    VALIDATION:"INDEPENDENT BACKTEST & VALIDATION ENGINE"
  });

  const repos = [
    {id:"CTR-01",role:"RESEARCH",name:"HKUDS/Vibe-Trading",path:"D:\\Dusty\\contractors\\Vibe-Trading",origin:"https://github.com/HKUDS/Vibe-Trading.git",commit:"8f41c2a",state:"ACTIVE",selected:true,adapter:"research.v1",resource:"P3 HEAVY"},
    {id:"CTR-02",role:"RESEARCH",name:"microsoft/qlib",path:"D:\\Dusty\\contractors\\qlib",origin:"https://github.com/microsoft/qlib.git",commit:"74ca20f",state:"STANDBY",selected:false,adapter:"research.v1",resource:"P3 HEAVY"},
    {id:"CTR-03",role:"RESEARCH",name:"Vibe-Trading-lab",path:"D:\\Research\\Vibe-Trading-lab",origin:"https://github.com/example/Vibe-Trading-lab.git",commit:"32aa17d",state:"AVAILABLE",selected:false,adapter:"research.v1",resource:"P3 HEAVY"},
    {id:"CTR-04",role:"FORECAST",name:"shiyu-coder/Kronos",path:"D:\\Dusty\\contractors\\Kronos",origin:"https://github.com/shiyu-coder/Kronos.git",commit:"6d901be",state:"ACTIVE",selected:true,adapter:"forecast.v1",resource:"P3 HEAVY"},
    {id:"CTR-05",role:"FORECAST",name:"Kronos-experimental",path:"C:\\Users\\Trader\\source\\Kronos-experimental",origin:"git@github.com:example/Kronos-experimental.git",commit:"d901ce4",state:"UNVERIFIED",selected:false,adapter:"forecast.?",resource:"UNKNOWN"},
    {id:"CTR-06",role:"SIMULATION",name:"nautechsystems/nautilus_trader",path:"D:\\Dusty\\contractors\\nautilus_trader",origin:"https://github.com/nautechsystems/nautilus_trader.git",commit:"1b833ef",state:"STANDBY",selected:false,adapter:"simulation.v1",resource:"P2 MODERATE"},
    {id:"CTR-07",role:"VALIDATION",name:"QuantConnect/Lean",path:"D:\\Dusty\\contractors\\Lean",origin:"https://github.com/QuantConnect/Lean.git",commit:"42efc91",state:"STANDBY",selected:false,adapter:"validation.v1",resource:"P4 EXCLUSIVE"}
  ];

  const references = [
    {id:"ARC-01",name:"Conway-Research/automaton",role:"EVOLUTIONARY ARCHITECTURE REFERENCE",integration:"ADAPTED INTO DUSTY CORE",runtime:"NO RUNTIME DEPENDENCY"},
    {id:"REF-01",name:"barter-rs/barter-rs",role:"EVENT-DRIVEN TRADING FRAMEWORK REFERENCE",integration:"RESEARCH / REFERENCE",runtime:"NOT ACTIVE"},
    {id:"REF-02",name:"vnpy/vnpy",role:"TRADING FRAMEWORK / ADAPTER REFERENCE",integration:"RESEARCH / REFERENCE",runtime:"NOT ACTIVE"}
  ];

  const panel = document.createElement("article");
  panel.className = "panel contractor-manager";
  panel.innerHTML = `
    <header><span>EXTERNAL CAPABILITY REPOSITORIES</span><div class="contractor-actions"><span id="contractorState">2 ACTIVE</span><button type="button" id="contractorRescan" class="ghost tiny-button">RESCAN · MOCK</button></div></header>
    <div class="contractor-summary">
      <div><span>DISCOVERED REPOS</span><b id="contractorFound">7</b></div>
      <div><span>CAPABILITY ROLES</span><b id="contractorTypes">4</b></div>
      <div><span>ACTIVE IMPLEMENTATIONS</span><b id="contractorSelected">2</b></div>
      <div><span>UNVERIFIED</span><b id="contractorUnverified" class="state-CAUTION">1</b></div>
    </div>
    <div id="contractorRows" class="contractor-repo-rows"></div>
    <p id="contractorNote" class="contractor-policy"><b>SWITCH POLICY:</b> one ACTIVE implementation per capability role. Alternatives remain STANDBY/AVAILABLE until verified. Production switching is staged, quiesced, health-tested, registry-atomic and automatically rollback-capable; no repository receives MT5 credentials or broker-write authority.</p>`;

  const referencePanel = document.createElement("article");
  referencePanel.className = "panel contractor-manager architecture-lineage";
  referencePanel.innerHTML = `
    <header><span>ARCHITECTURE / ENGINEERING REFERENCES</span><span>NON-RUNTIME</span></header>
    <div class="contractor-summary">
      <div><span>REFERENCE REPOS</span><b>${references.length}</b></div>
      <div><span>RUNTIME DEPENDENCIES</span><b>0</b></div>
      <div><span>AUTOMATON</span><b class="state-NORMAL">DUSTY-NATIVE</b></div>
      <div><span>EXECUTION AUTHORITY</span><b>NONE</b></div>
    </div>
    <div class="contractor-repo-rows">${references.map(item => `
      <div class="contractor-repo-row architecture-reference">
        <b>${item.id}</b>
        <span><strong>${item.name}</strong><small>OPTIONAL LOCAL REFERENCE</small></span>
        <span class="contractor-origin"><strong class="contractor-role">${item.role}</strong><small>${item.runtime}</small></span>
        <span class="contractor-state-reference">REFERENCE</span>
        <label><strong>${item.integration}</strong><small>NOT SELECTABLE</small></label>
      </div>`).join("")}</div>
    <p class="contractor-policy"><b>REFERENCE ≠ CONTRACTOR:</b> these repositories may inform engineering or future adapter design, but Dusty does not require or execute them merely because a reference checkout exists.</p>`;

  const terminalManager = layout.querySelector(".terminal-manager");
  if (terminalManager) {
    terminalManager.insertAdjacentElement("afterend", panel);
    panel.insertAdjacentElement("afterend", referencePanel);
  } else {
    layout.append(panel, referencePanel);
  }

  const stateClass = state => `contractor-state-${state.toLowerCase()}`;
  const roles = () => [...new Set(repos.map(repo => repo.role))];
  const roleLabel = repo => ROLE_LABELS[repo.role] || "SPECIALIST CAPABILITY ENGINE";
  const activeForRole = role => repos.find(repo => repo.role === role && repo.selected);

  function setRoleImplementation(candidate) {
    const current = activeForRole(candidate.role);
    if (candidate.state === "UNVERIFIED") return {ok:false, reason:"UNVERIFIED"};
    if (current?.id === candidate.id) return {ok:true, reason:"ALREADY_ACTIVE"};

    // UI-LAB simulation of an atomic registry flip. Production MUST execute the
    // staged switching state machine documented above and roll back on probe or
    // probation failure; never stop a healthy incumbent before candidate proof.
    if (current) {
      current.selected = false;
      current.state = "STANDBY";
    }
    candidate.selected = true;
    candidate.state = "ACTIVE";
    return {ok:true, reason:current ? `SWITCHED_FROM_${current.id}` : "ACTIVATED"};
  }

  function render() {
    panel.querySelector("#contractorFound").textContent = repos.length;
    panel.querySelector("#contractorTypes").textContent = roles().length;
    panel.querySelector("#contractorSelected").textContent = repos.filter(repo => repo.selected).length;
    panel.querySelector("#contractorUnverified").textContent = repos.filter(repo => repo.state === "UNVERIFIED").length;
    panel.querySelector("#contractorState").textContent = `${repos.filter(repo => repo.selected && repo.state === "ACTIVE").length} ACTIVE`;
    panel.querySelector("#contractorRows").innerHTML = repos.map(repo => `
      <div class="contractor-repo-row" data-contractor-id="${repo.id}">
        <b>${repo.id}</b>
        <span><strong>${repo.name}</strong><small>${repo.path}</small></span>
        <span class="contractor-origin"><strong class="contractor-role">${roleLabel(repo)}</strong><small title="${repo.origin}">${repo.adapter} · ${repo.resource} · ${repo.origin}</small></span>
        <span class="${stateClass(repo.state)}">${repo.state}</span>
        <label><select aria-label="Implementation state for ${repo.name}"><option value="standby"${repo.selected ? "" : " selected"}>STANDBY</option><option value="active"${repo.selected ? " selected" : ""}>ACTIVE</option></select><small>HEAD ${repo.commit}</small></label>
      </div>`).join("");

    panel.querySelectorAll(".contractor-repo-row select").forEach(select => {
      select.addEventListener("change", event => {
        const row = event.target.closest(".contractor-repo-row");
        const repo = repos.find(item => item.id === row?.dataset.contractorId);
        if (!repo) return;

        if (event.target.value === "active") {
          const result = setRoleImplementation(repo);
          if (!result.ok) {
            event.target.value = "standby";
            panel.querySelector("#contractorNote").innerHTML = `<b>SWITCH BLOCKED · MOCK:</b> ${repo.name} is UNVERIFIED. Production Dusty must prove Git identity, pinned revision, adapter/schema compatibility, isolated runtime health and golden-data behavior before it can enter STANDBY or ACTIVE service.`;
            return;
          }
          panel.querySelector("#contractorNote").innerHTML = `<b>MOCK REGISTRY SWITCH:</b> ${roleLabel(repo)} now points to ${repo.name}. Production would first quiesce the incumbent, start this candidate in isolated STANDBY, run compatibility/golden tests, atomically flip the active registry pointer, observe probation health, and automatically roll back on failure.`;
        } else if (repo.selected) {
          // A capability with no replacement may be intentionally taken offline,
          // but this is a contractor availability change, never trading authority.
          repo.selected = false;
          repo.state = "STANDBY";
          panel.querySelector("#contractorNote").innerHTML = `<b>MOCK ROLE IDLED:</b> ${roleLabel(repo)} has no active implementation. Dusty should mark dependent research/validation capability unavailable and fail closed without affecting MT5 execution or risk controls.`;
        }
        render();
        window.DUSTY_SYSTEM_VIEW?.fit();
      });
    });
  }

  panel.querySelector("#contractorRescan").addEventListener("click", () => {
    panel.querySelector("#contractorNote").innerHTML = `<b>MOCK RESCAN COMPLETE:</b> ${repos.length} candidate Git working trees across ${roles().length} external capability roles. Production scan verifies canonical worktree/Git identity and adapter metadata only; it never executes, pulls, resets, installs, activates, or switches a repository during discovery.`;
    window.DUSTY_SYSTEM_VIEW?.fit();
  });

  render();
})();
