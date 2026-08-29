(() => {
  "use strict";
  const root = document.querySelector("#performance .performance-layout");
  if (!root) return;

  function ensureBadge() {
    const scopeState = root.querySelector("#perfCapitalScopeState");
    if (!scopeState) return null;
    let badge = root.querySelector("#perfCapitalScopeHealth");
    if (!badge) {
      badge = document.createElement("span");
      badge.id = "perfCapitalScopeHealth";
      badge.className = "perf-capital-scope-health state-normal";
      badge.setAttribute("aria-label", "Selected scope operational state");
      scopeState.insertAdjacentElement("afterend", badge);
    }
    return badge;
  }

  function render(detail = {}) {
    const badge = ensureBadge();
    if (!badge) return;
    const tone = ["normal","caution","fault","parked","unprovisioned"].includes(detail.stateTone) ? detail.stateTone : "unprovisioned";
    badge.className = `perf-capital-scope-health state-${tone}`;
    badge.textContent = detail.state || "UNPROVISIONED";
    badge.title = `${detail.label || "Selected scope"} · ${badge.textContent}`;
  }

  window.addEventListener("dusty:performance-scope-synchronized", event => render(event.detail));

  // Panel sync may have completed before this small presentation adapter loads.
  const sync = window.DUSTY_PERFORMANCE_PANEL_SYNC;
  if (sync?.selection && sync?.canonicalState) {
    const selection = sync.selection();
    const scopeMock = window.DUSTY_PERFORMANCE_SCOPE_MOCK;
    const state = selection.portfolio === 0
      ? window.DUSTY_MOCK?.firm?.state
      : scopeMock?.portfolios?.[selection.portfolio]?.entities?.[selection.entity]?.snapshot?.state;
    const canonical = sync.canonicalState(state);
    render({ state:canonical.term, stateTone:canonical.tone, label:selection.portfolio === 0 ? "FIRM" : `PORTFOLIO ${selection.portfolio} · ${selection.entity.toUpperCase()}` });
  }
})();
