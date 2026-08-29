(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const hierarchy = data?.hierarchy;
  const target = document.querySelector("#hierarchyTree");
  if (!data || !hierarchy || !target) return;

  const money = value => Number(value || 0).toLocaleString(undefined, {
    style:"currency", currency:"USD", maximumFractionDigits:0
  });
  const signedPct = value => `${Number(value || 0) >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}%`;
  const clamp = (value,min,max) => Math.min(max,Math.max(min,value));
  const dailyTargetPct = Number(hierarchy.dailyTargetPct || 0.23);

  function entity(id) {
    return window.DUSTY_DESK_STATUS?.get(id) || hierarchy.nodes.find(node => node.id === id) || null;
  }

  function layerChildren(layerNumber) {
    const layer = hierarchy.layers.find(item => item.layer === layerNumber);
    if (!layer) return [];
    return layer.childIds.map(entity).filter(Boolean).slice(0,6);
  }

  function aggregate(children) {
    const active = children.filter(child => child.provisioned !== false && child.mt5Bound !== false);
    const population = active.length ? active : children;
    const equity = population.reduce((sum, child) => sum + Number(child.equity || 0), 0);
    const realized = population.reduce((sum, child) => sum + Number(child.realizedPnlToday || 0), 0);
    const weightedToday = equity > 0
      ? population.reduce((sum, child) => sum + Number(child.today || 0) * Number(child.equity || 0), 0) / equity
      : 0;
    return { realized, today:weightedToday, progress:dailyTargetPct > 0 ? weightedToday / dailyTargetPct * 100 : 0 };
  }

  function deskIdFromRow(row) {
    const explicit = row.dataset.treeDesk || row.dataset.deskId || row.dataset.id;
    if (explicit && entity(explicit)) return explicit;
    const id = row.querySelector("b")?.textContent?.trim();
    return id && entity(id) ? id : null;
  }

  function quickMarkup(model, isLayer = false) {
    const progress = clamp(model.progress, -199, 299);
    const progressClass = progress >= 100 ? "ahead" : progress >= 0 ? "tracking" : "behind";
    return `<div class="tree-quick ${isLayer ? "tree-layer-quick" : "tree-desk-quick"}">
      <span><small>REALIZED</small><b>${money(model.realized)}</b></span>
      <span><small>TODAY</small><b>${signedPct(model.today)}</b></span>
      <span class="tree-target ${progressClass}"><small>DAILY TARGET</small><b>${progress.toFixed(0)}%</b><i><em style="width:${clamp(Math.abs(progress),0,100)}%"></em></i></span>
    </div>`;
  }

  function decorate() {
    target.querySelectorAll(".tree-layer").forEach(section => {
      const head = section.querySelector(".tree-layer-head");
      if (!head) return;
      const raw = head.dataset.treeLayer || head.querySelector("b")?.textContent || "";
      const match = String(raw).match(/(?:LAYER\s*)?(\d+)/i);
      if (!match) return;
      const layerNumber = Number(match[1]);
      const model = aggregate(layerChildren(layerNumber));
      head.querySelector(".tree-layer-quick")?.remove();
      head.insertAdjacentHTML("beforeend", quickMarkup(model,true));
    });

    target.querySelectorAll(".tree-child").forEach(row => {
      const id = deskIdFromRow(row);
      const desk = id ? entity(id) : null;
      if (!desk) return;
      const today = Number(desk.today || 0);
      const model = {
        realized:Number(desk.realizedPnlToday || 0),
        today,
        progress:dailyTargetPct > 0 ? today / dailyTargetPct * 100 : 0
      };
      row.querySelector(".tree-desk-quick")?.remove();
      row.insertAdjacentHTML("beforeend", quickMarkup(model,false));
    });
  }

  let decorating = false;
  function safeDecorate() {
    if (decorating) return;
    decorating = true;
    queueMicrotask(() => {
      try { decorate(); } finally { decorating = false; }
    });
  }

  /* app-v16 replaces the hierarchy root as a whole. Observe only direct root
     replacement so our own quick-data inserts never recursively trigger us. */
  new MutationObserver(mutations => {
    if (mutations.some(mutation => mutation.type === "childList")) safeDecorate();
  }).observe(target,{childList:true});

  document.addEventListener("dusty:desk-status-changed",safeDecorate);
  safeDecorate();

  window.DUSTY_HIERARCHY_QUICK_VIEW = Object.freeze({
    version:"3.0.1",
    dailyTargetPct,
    refresh:safeDecorate
  });
})();