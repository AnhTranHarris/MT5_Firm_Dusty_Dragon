(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * CONTRACTOR REPOSITORY MANAGER — UI LAB / PRODUCTION HANDOFF NOTES
   * ----------------------------------------------------------------
   * PURPOSE
   * Dusty may use several independently installed contractor repositories. The
   * UI names contractors by CAPABILITY ROLE rather than upstream project brand:
   *   VIBE      -> QUANT RESEARCH & STRATEGY ENGINE
   *   KRONOS    -> TIME-SERIES FORECASTING ENGINE
   *   AUTOMATON -> AUTONOMOUS RESEARCH ORCHESTRATOR
   * The upstream repository remains visible as implementation identity. This
   * separation lets Dusty support multiple repos that can satisfy the same role.
   * Discovery is automatic; selection is human-confirmed. A discovered Git repo
   * receives ZERO execution/trading authority merely because it is selected.
   *
   * PRODUCTION DISCOVERY CONTRACT (Windows helper/service, never browser UI)
   * 1) Search only bounded roots: Dusty-configured contractor roots, previously
   *    approved repo paths, GitHub Desktop/known developer roots if explicitly
   *    configured, and user-selected folders. Do NOT recursively crawl C:\.
   * 2) Candidate marker may be a .git DIRECTORY OR .git FILE. Git worktrees,
   *    submodules and --separate-git-dir can legitimately use a .git file.
   *    Validate through Git, not filesystem assumptions:
   *      git -C <candidate> rev-parse --show-toplevel
   *      git -C <candidate> rev-parse --absolute-git-dir
   *      git -C <candidate> rev-parse --is-inside-work-tree
   *    Git docs: https://git-scm.com/docs/git-rev-parse
   * 3) Read identity through Git configuration/commands, not by parsing .git
   *    internals. Capture canonical worktree path, absolute git-dir, HEAD commit,
   *    current branch/detached state, and all remotes. A normal GitHub clone
   *    usually creates remote 'origin', but do NOT assume origin exists or that
   *    it uniquely identifies a contractor.
   *    GitHub clone docs:
   *      https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository
   *    GitHub remote docs:
   *      https://docs.github.com/en/get-started/git-basics/about-remote-repositories
   * 4) Classify contractor ROLE from an explicit Dusty adapter manifest when
   *    available (future dusty-contractor.json), then adapter probe/signature.
   *    Never classify solely from folder/repository name. Multiple repos of the
   *    same role are valid; selection is per contractor role.
   * 5) Before activation verify adapter/API compatibility, expected entrypoints,
   *    pinned commit/version policy, dependency/environment health, and optional
   *    integrity allow-list. A repo being a valid Git working tree != trusted or
   *    compatible code.
   * 6) Never auto-pull, auto-checkout, auto-reset, auto-install dependencies, or
   *    execute arbitrary repo scripts during discovery. Git fetch/pull changes
   *    network/local state and belongs behind explicit update policy.
   * 7) Run contractors out-of-process with least privilege, bounded CPU/RAM/time,
   *    explicit IPC/schema contracts and no broker credentials. Contractor output
   *    is research evidence/input; Dusty's authoritative risk/execution pipeline
   *    remains the only path to broker writes.
   *
   * WINDOWS NOTES
   * Windows Search can accelerate user-scoped discovery only for indexed roots;
   * it is not a complete source of truth. Prefer a small persisted contractor
   * registry plus bounded scans. Avoid expensive whole-disk recursive polling.
   * Microsoft Search protocol/index references:
   *   https://learn.microsoft.com/en-us/windows/win32/shell/search-protocol
   *   https://learn.microsoft.com/en-us/windows/win32/search/getting-started-with-parameter-value-arguments
   * App Paths is useful for installed APPLICATION executables, not a registry of
   * arbitrary Git working trees:
   *   https://learn.microsoft.com/en-us/windows/win32/shell/app-registration
   *
   * METAQUOTES BOUNDARY
   * Contractors must never select or infer an MT5 instance themselves. Dusty's
   * terminal manager binds explicit terminal executable/account identity. The
   * MetaQuotes Python API supports initialize(path, ...); path-less discovery is
   * ambiguous when multiple terminals exist:
   *   https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
   *   https://www.mql5.com/en/book/advanced/python/python_init
   *
   * COMMUNITY DIAGNOSTIC CONTEXT (non-authoritative; never auto-apply)
   * Git users note that .git may legitimately be a file for worktrees/separate
   * git dirs: https://www.reddit.com/r/git/comments/17hpwha/
   * MT5 users commonly use separate install folders for concurrent terminals:
   * https://www.reddit.com/r/metatrader/comments/1denbb4/
   * These reinforce path/instance identity but are not production specifications.
   */

  const ROLE_LABELS = Object.freeze({
    VIBE:"QUANT RESEARCH & STRATEGY ENGINE",
    KRONOS:"TIME-SERIES FORECASTING ENGINE",
    AUTOMATON:"AUTONOMOUS RESEARCH ORCHESTRATOR"
  });

  const repos = [
    {id:"CTR-01",type:"VIBE",name:"HKUDS/Vibe-Trading",path:"D:\\Dusty\\contractors\\Vibe-Trading",origin:"https://github.com/HKUDS/Vibe-Trading.git",commit:"8f41c2a",state:"ACTIVE",selected:true},
    {id:"CTR-02",type:"VIBE",name:"Vibe-Trading-lab",path:"D:\\Research\\Vibe-Trading-lab",origin:"https://github.com/example/Vibe-Trading-lab.git",commit:"32aa17d",state:"AVAILABLE",selected:false},
    {id:"CTR-03",type:"KRONOS",name:"shiyu-coder/Kronos",path:"D:\\Dusty\\contractors\\Kronos",origin:"https://github.com/shiyu-coder/Kronos.git",commit:"6d901be",state:"ACTIVE",selected:true},
    {id:"CTR-04",type:"KRONOS",name:"Kronos-experimental",path:"C:\\Users\\Trader\\source\\Kronos-experimental",origin:"git@github.com:example/Kronos-experimental.git",commit:"d901ce4",state:"UNVERIFIED",selected:false},
    {id:"CTR-05",type:"AUTOMATON",name:"Conway-Research/automaton",path:"D:\\Dusty\\contractors\\automaton",origin:"https://github.com/Conway-Research/automaton.git",commit:"2ba910f",state:"ACTIVE",selected:true}
  ];

  const panel = document.createElement("article");
  panel.className = "panel contractor-manager";
  panel.innerHTML = `
    <header><span>CONTRACTOR REPOSITORIES</span><div class="contractor-actions"><span id="contractorState">3 ACTIVE</span><button type="button" id="contractorRescan" class="ghost tiny-button">RESCAN · MOCK</button></div></header>
    <div class="contractor-summary">
      <div><span>DISCOVERED REPOS</span><b id="contractorFound">5</b></div>
      <div><span>CAPABILITY ROLES</span><b id="contractorTypes">3</b></div>
      <div><span>SELECTED</span><b id="contractorSelected">3</b></div>
      <div><span>UNVERIFIED</span><b id="contractorUnverified" class="state-CAUTION">1</b></div>
    </div>
    <div id="contractorRows" class="contractor-repo-rows"></div>
    <p id="contractorNote" class="contractor-policy"><b>DISCOVERY ≠ TRUST:</b> Dusty may locate multiple implementations of the same capability role. Human selection chooses the adapter candidate; compatibility verification and sandbox policy still gate activation. No contractor receives MT5 credentials or broker-write authority.</p>`;

  const terminalManager = layout.querySelector(".terminal-manager");
  if (terminalManager) terminalManager.insertAdjacentElement("afterend", panel);
  else layout.append(panel);

  const stateClass = state => `contractor-state-${state.toLowerCase()}`;
  const types = () => [...new Set(repos.map(repo => repo.type))];
  const roleLabel = repo => ROLE_LABELS[repo.type] || "SPECIALIST CONTRACTOR";

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
    panel.querySelector("#contractorNote").innerHTML = `<b>MOCK RESCAN COMPLETE:</b> ${repos.length} Git working trees across ${types().length} contractor capability roles. Production discovery will use configured roots + persisted paths, validate candidates with Git commands, and will not execute, pull, reset, install, or trust discovered code during the scan.`;
    window.DUSTY_SYSTEM_VIEW?.fit();
  });

  render();
})();
