(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * SYSTEM VIEWPORT + DISPLAY GOVERNOR — UI LAB
   * -------------------------------------------
   * The System workspace is a fixed cockpit surface. Presentation pressure is
   * solved by wrapping, responsive reflow, and panel collapse — never page-level
   * scrolling. Collapse is presentation state only and must never change MT5,
   * execution, risk, reconciliation, or telemetry behavior.
   *
   * IMPORTANT DISPLAY SEMANTICS
   * ---------------------------
   * "NO MOTION" is a GLOBAL Dusty Dragon UI policy. It disables decorative
   * animation/transitions across every workspace, not merely the Trading Floor.
   * The Trading Floor is the one special case where merely freezing the JARVIS
   * solar system would leave a misleading/non-interactive spatial snapshot.
   * Therefore, whenever NO MOTION is active, the orbital Canvas + spatial cubes
   * are hidden and the existing analytical hierarchy tree is shown instead.
   *
   * In other words:
   *   global UI            -> animation/transition disabled
   *   Trading Floor        -> hierarchy tree replaces orbital solar system
   *   trading/risk/backend -> completely unaffected
   *
   * Accessibility / Windows references retained for the native-app handoff:
   * - Windows contrast themes:
   *   https://learn.microsoft.com/en-us/windows/apps/design/accessibility/high-contrast-themes
   * - Web forced-colors detection used by this prototype:
   *   https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/forced-colors
   * - User contrast preference:
   *   https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-contrast
   * - Reduced motion:
   *   https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion
   *
   * Production Windows app: detect the user's contrast/motion preference through
   * native framework/system APIs, use system/theme resources rather than hard-
   * coded colors, and treat accessibility preference as stronger than cosmetic
   * rendering preference.
   */

  const PANEL_META = [
    ["capacity-panel", 100, "TRADING CAPACITY"],
    ["terminal-manager", 95, "MT5 TERMINAL MANAGER"],
    ["qualification-panel", 90, "LAYER 0 · PROGRESSIVE BOOTSTRAP"],
    ["hardware-panel", 85, "PC HARDWARE SNAPSHOT"],
    ["system-table", 80, "SYSTEM / INFRASTRUCTURE"],
    ["resource-load-panel", 75, "RESOURCE LOAD"],
    ["render-priority-panel", 72, "DISPLAY GOVERNOR"],
    ["provisioning-panel", 65, "DESK PROVISIONING / CAPACITY STATE"],
    ["audit-panel", 40, "AUDIT TAIL"]
  ];

  const DEFAULT_COLLAPSED = new Set(["provisioning-panel", "audit-panel"]);

  let decorated = false;
  let initialStateApplied = false;
  let fitting = false;
  let fitTimer = 0;

  function directHeader(panel) {
    return panel.querySelector(":scope > header") || panel.querySelector(":scope > .capacity-head");
  }

  function classifyStaticPanels() {
    layout.querySelectorAll(":scope > .panel").forEach(panel => {
      const headerText = directHeader(panel)?.textContent?.toUpperCase() || "";
      if (headerText.includes("RESOURCE LOAD")) panel.classList.add("resource-load-panel");
      if (headerText.includes("RENDER PRIORITY") || headerText.includes("DISPLAY GOVERNOR")) panel.classList.add("render-priority-panel");
    });
  }

  function metaFor(panel) {
    const found = PANEL_META.find(([className]) => panel.classList.contains(className));
    if (found) return {priority: found[1], title: found[2]};
    const title = directHeader(panel)?.textContent?.trim().replace(/\s+/g, " ") || "SYSTEM PANEL";
    return {priority: 50, title};
  }

  function setCollapsed(panel, collapsed, reason = "manual") {
    panel.classList.toggle("system-collapsed", collapsed);
    panel.dataset.collapseReason = collapsed ? reason : "";
    const toggle = panel.querySelector(":scope > header .system-collapse-toggle, :scope > .capacity-head .system-collapse-toggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", String(!collapsed));
      toggle.setAttribute("aria-label", `${collapsed ? "Expand" : "Collapse"} ${panel.dataset.systemTitle || "System panel"}`);
      toggle.title = collapsed ? "Expand panel" : "Collapse panel";
      toggle.textContent = "⌄";
    }
  }

  function decoratePanel(panel) {
    if (panel.dataset.systemCollapsible === "true") return;
    const meta = metaFor(panel);
    const header = directHeader(panel);
    if (!header) return;

    panel.dataset.systemCollapsible = "true";
    panel.dataset.systemPriority = String(meta.priority);
    panel.dataset.systemTitle = meta.title;
    header.classList.add("system-panel-header");

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "system-collapse-toggle";
    toggle.setAttribute("aria-label", `Collapse ${meta.title}`);
    toggle.setAttribute("aria-expanded", "true");
    toggle.textContent = "⌄";
    header.append(toggle);

    toggle.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      const willCollapse = !panel.classList.contains("system-collapsed");
      setCollapsed(panel, willCollapse, "manual");
      if (!willCollapse) scheduleFit(panel);
    });
  }

  function applyInitialPanelState() {
    if (initialStateApplied) return;
    layout.querySelectorAll(":scope > .panel").forEach(panel => {
      const shouldCollapse = [...DEFAULT_COLLAPSED].some(className => panel.classList.contains(className));
      setCollapsed(panel, shouldCollapse, shouldCollapse ? "startup" : "");
    });
    initialStateApplied = true;
  }

  function decorateAll() {
    classifyStaticPanels();
    layout.querySelectorAll(":scope > .panel").forEach(decoratePanel);
    decorated = true;
  }

  function buildRenderGovernor() {
    classifyStaticPanels();
    const panel = layout.querySelector(".render-priority-panel");
    if (!panel || panel.dataset.renderGovernor === "true") return;
    panel.dataset.renderGovernor = "true";
    panel.innerHTML = `
      <header><span>DISPLAY GOVERNOR</span><span id="renderProfileState">AUTO · SPATIAL FULL</span></header>
      <div class="render-governor-body">
        <div class="render-mode-switch" role="group" aria-label="Display governor mode">
          <button type="button" data-render-mode="auto" class="active">AUTO</button>
          <button type="button" data-render-mode="manual">MANUAL</button>
        </div>
        <label class="render-profile-label">DISPLAY PROFILE
          <select id="renderProfile" disabled>
            <option value="spatial-full">SPATIAL FULL</option>
            <option value="spatial-reduced">SPATIAL REDUCED</option>
            <option value="no-motion">NO MOTION · TREE FLOOR</option>
            <option value="high-contrast">HIGH CONTRAST · NO MOTION</option>
          </select>
        </label>
        <div class="render-signals">
          <span>WINDOWS CONTRAST <b id="renderContrastSignal">NORMAL</b></span>
          <span>REDUCED MOTION <b id="renderMotionSignal">NO</b></span>
          <span>GUI POLICY <b id="renderPolicySignal">FULL EFFECTS</b></span>
        </div>
        <p id="renderGovernorNote">AUTO preserves accessibility first, then reduces cosmetic rendering before trading-critical compute.</p>
      </div>`;

    let mode = "auto";
    let manualProfile = "spatial-full";
    const forced = matchMedia("(forced-colors: active)");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const contrastMore = matchMedia("(prefers-contrast: more)");
    const select = panel.querySelector("#renderProfile");
    const buttons = [...panel.querySelectorAll("[data-render-mode]")];

    function autoProfile() {
      if (forced.matches) return "high-contrast";
      if (reduced.matches) return "no-motion";
      if (window.innerWidth < 1000 || window.innerHeight < 650) return "spatial-reduced";
      return "spatial-full";
    }

    function applyProfile(profile) {
      const noMotion = profile === "no-motion" || profile === "high-contrast";
      document.body.classList.toggle("render-spatial-reduced", profile === "spatial-reduced");
      document.body.classList.toggle("render-analytical-lite", profile === "no-motion");
      document.body.classList.toggle("render-high-contrast", profile === "high-contrast");
      document.body.classList.toggle("render-no-motion", noMotion);
      panel.querySelector("#renderProfileState").textContent = `${mode.toUpperCase()} · ${profile.replaceAll("-", " ").toUpperCase()}`;
      panel.querySelector("#renderPolicySignal").textContent = profile === "spatial-full"
        ? "FULL EFFECTS"
        : profile === "spatial-reduced"
          ? "REDUCED EFFECTS"
          : profile === "no-motion"
            ? "GLOBAL STATIC · TREE FLOOR"
            : "SYSTEM CONTRAST · STATIC";
      select.value = profile;
    }

    function render() {
      panel.querySelector("#renderContrastSignal").textContent = forced.matches || contrastMore.matches ? "HIGH" : "NORMAL";
      panel.querySelector("#renderMotionSignal").textContent = reduced.matches ? "YES" : "NO";
      select.disabled = mode === "auto";
      buttons.forEach(button => button.classList.toggle("active", button.dataset.renderMode === mode));
      const profile = mode === "auto" ? autoProfile() : manualProfile;
      applyProfile(profile);
      panel.querySelector("#renderGovernorNote").innerHTML = mode === "auto"
        ? `<b>AUTO:</b> accessibility wins first. Reduced-motion disables decorative motion across the entire Dusty UI; the Trading Floor alone swaps its JARVIS solar system for the hierarchy tree. Forced colors additionally use the Windows/system contrast palette.`
        : `<b>MANUAL:</b> choose presentation only. NO MOTION disables decorative animation across every workspace and replaces the Trading Floor solar system with its hierarchy tree; it never changes desk capacity, trading authority, or risk controls.`;
      scheduleFit(panel);
    }

    buttons.forEach(button => button.addEventListener("click", () => { mode = button.dataset.renderMode; render(); }));
    select.addEventListener("change", () => { manualProfile = select.value; render(); });
    [forced, reduced, contrastMore].forEach(query => query.addEventListener?.("change", render));
    window.addEventListener("resize", render);
    render();
  }

  function syncWorkspaceBodyState() {
    document.body.classList.toggle("system-workspace-active", system.classList.contains("active"));
  }

  function overflows() {
    if (!system.classList.contains("active")) return false;
    const layoutRect = layout.getBoundingClientRect();
    const panels = [...layout.querySelectorAll(":scope > .panel")];
    const bottom = panels.reduce((max, panel) => Math.max(max, panel.getBoundingClientRect().bottom), layoutRect.top);
    const right = panels.reduce((max, panel) => Math.max(max, panel.getBoundingClientRect().right), layoutRect.left);
    return bottom > layoutRect.bottom + 1 || right > layoutRect.right + 1 || layout.scrollHeight > layout.clientHeight + 1 || layout.scrollWidth > layout.clientWidth + 1;
  }

  function expandedPanels(except = null) {
    return [...layout.querySelectorAll(":scope > .panel:not(.system-collapsed)")]
      .filter(panel => panel !== except)
      .sort((a, b) => Number(a.dataset.systemPriority || 50) - Number(b.dataset.systemPriority || 50));
  }

  function fitToViewport(preferredPanel = null) {
    if (fitting || !system.classList.contains("active")) return;
    fitting = true;
    try {
      if (!decorated) decorateAll();
      const candidates = expandedPanels(preferredPanel);
      let guard = candidates.length + 2;
      while (overflows() && candidates.length && guard-- > 0) setCollapsed(candidates.shift(), true, "auto-fit");
      if (overflows() && preferredPanel && !preferredPanel.classList.contains("system-collapsed")) setCollapsed(preferredPanel, true, "auto-fit");
    } finally {
      fitting = false;
    }
  }

  function scheduleFit(preferredPanel = null) {
    clearTimeout(fitTimer);
    fitTimer = window.setTimeout(() => fitToViewport(preferredPanel), 40);
  }

  function expandAllAndFit() {
    layout.querySelectorAll(":scope > .panel").forEach(panel => setCollapsed(panel, false));
    scheduleFit();
  }

  function collapseAll() {
    layout.querySelectorAll(":scope > .panel").forEach(panel => setCollapsed(panel, true, "manual"));
  }

  function addViewTools() {
    if (system.querySelector(".system-view-tools")) return;
    const tools = document.createElement("div");
    tools.className = "system-view-tools";
    tools.innerHTML = `<button type="button" data-system-fit>FIT VIEW</button><button type="button" data-system-expand>EXPAND</button><button type="button" data-system-collapse>COLLAPSE</button>`;
    system.append(tools);
    tools.querySelector("[data-system-fit]").addEventListener("click", () => scheduleFit());
    tools.querySelector("[data-system-expand]").addEventListener("click", expandAllAndFit);
    tools.querySelector("[data-system-collapse]").addEventListener("click", collapseAll);
  }

  const observer = new MutationObserver(() => {
    decorateAll();
    buildRenderGovernor();
    if (!initialStateApplied) applyInitialPanelState();
    scheduleFit();
    if (layout.querySelectorAll(":scope > .panel").length >= 9) observer.disconnect();
  });
  observer.observe(layout, {childList:true});

  buildRenderGovernor();
  addViewTools();
  decorateAll();
  applyInitialPanelState();
  syncWorkspaceBodyState();

  const resizeObserver = new ResizeObserver(() => scheduleFit());
  resizeObserver.observe(system);

  const classObserver = new MutationObserver(() => {
    syncWorkspaceBodyState();
    if (system.classList.contains("active")) scheduleFit();
  });
  classObserver.observe(system, {attributes:true, attributeFilter:["class"]});

  document.addEventListener("click", event => {
    if (event.target.closest('[data-workspace="system"]')) scheduleFit();
  });
  window.addEventListener("resize", () => scheduleFit());

  window.DUSTY_SYSTEM_VIEW = Object.freeze({fit: () => scheduleFit(), collapseAll, expandAll: expandAllAndFit});
})();