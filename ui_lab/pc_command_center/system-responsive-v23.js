(() => {
  "use strict";

  const system = document.querySelector("#system");
  const layout = system?.querySelector(".system-layout");
  if (!system || !layout) return;

  /*
   * SYSTEM VIEWPORT GOVERNOR — UI LAB
   * ---------------------------------
   * The System workspace is intentionally treated as a fixed cockpit surface.
   * We do not solve viewport pressure by introducing page scrollbars. Instead:
   *   1. content is allowed to wrap/shrink horizontally;
   *   2. every System panel receives a persistent collapse control;
   *   3. lower-priority panels collapse automatically if the current window
   *      cannot display the expanded composition;
   *   4. a manual expansion is honored, then the lowest-priority *other* panel
   *      is collapsed if necessary to keep the workspace inside the viewport.
   *
   * Future native Windows app translation:
   * preserve the same policy in the view-model/layout layer. Do not make the
   * backend change sampling, MT5, execution, or risk behavior because a panel
   * became collapsed. Collapse is presentation state only.
   */

  const PANEL_META = [
    ["capacity-panel", 100, "COMPUTE CAPACITY GOVERNOR"],
    ["terminal-manager", 95, "MT5 TERMINAL MANAGER"],
    ["qualification-panel", 90, "LAYER 0 · PROGRESSIVE BOOTSTRAP"],
    ["hardware-panel", 85, "PC HARDWARE SNAPSHOT"],
    ["system-table", 80, "SYSTEM / INFRASTRUCTURE"],
    ["resource-load-panel", 70, "RESOURCE LOAD"],
    ["provisioning-panel", 65, "DESK PROVISIONING / CAPACITY STATE"],
    ["audit-panel", 40, "AUDIT TAIL"],
    ["render-priority-panel", 30, "RENDER PRIORITY"]
  ];

  let decorated = false;
  let fitting = false;
  let fitTimer = 0;

  function directHeader(panel) {
    return panel.querySelector(":scope > header") || panel.querySelector(":scope > .capacity-head");
  }

  function classifyStaticPanels() {
    layout.querySelectorAll(":scope > .panel").forEach(panel => {
      const headerText = directHeader(panel)?.textContent?.toUpperCase() || "";
      if (headerText.includes("RESOURCE LOAD")) panel.classList.add("resource-load-panel");
      if (headerText.includes("RENDER PRIORITY")) panel.classList.add("render-priority-panel");
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

    /* Capacity mode buttons live in the same header. Appending the collapse
     * control rather than making the whole header clickable avoids accidental
     * collapse when the operator changes AUTO/MANUAL. */
    header.append(toggle);
    toggle.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      const willCollapse = !panel.classList.contains("system-collapsed");
      setCollapsed(panel, willCollapse, "manual");
      if (!willCollapse) scheduleFit(panel);
    });
  }

  function decorateAll() {
    classifyStaticPanels();
    layout.querySelectorAll(":scope > .panel").forEach(decoratePanel);
    decorated = true;
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

      /* Browser layout is synchronous after class changes when queried through
       * getBoundingClientRect(), so this bounded loop needs no animation frame. */
      const candidates = expandedPanels(preferredPanel);
      let guard = candidates.length + 2;
      while (overflows() && candidates.length && guard-- > 0) {
        setCollapsed(candidates.shift(), true, "auto-fit");
      }

      /* If the preferred panel alone still cannot fit, collapse it last rather
       * than allowing inaccessible off-screen content. Its header stays visible. */
      if (overflows() && preferredPanel && !preferredPanel.classList.contains("system-collapsed")) {
        setCollapsed(preferredPanel, true, "auto-fit");
      }
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

  /* v21/v22 currently execute before this module, but the observer protects the
   * lab if their load order changes during future experiments. */
  const observer = new MutationObserver(() => {
    decorateAll();
    scheduleFit();
    if (layout.querySelectorAll(":scope > .panel").length >= 9) observer.disconnect();
  });
  observer.observe(layout, {childList:true});

  addViewTools();
  decorateAll();
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

  /* Expose presentation controls only; no trading or infrastructure authority. */
  window.DUSTY_SYSTEM_VIEW = Object.freeze({fit: () => scheduleFit(), collapseAll, expandAll: expandAllAndFit});
})();
