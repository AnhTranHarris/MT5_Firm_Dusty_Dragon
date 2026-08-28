(() => {
  "use strict";

  /* UI-lab animation governor. Keep canvas cadence proportional to UX need. */
  const nativeRequest = window.requestAnimationFrame.bind(window);
  const nativeCancel = window.cancelAnimationFrame.bind(window);
  const scheduled = new Map();
  let nextId = 1;

  function targetFrameMs() {
    if (document.hidden) return 1000;
    const command = document.querySelector("#command");
    if (!command?.classList.contains("active")) return 250;
    if (document.body.classList.contains("analytical-mode")) return 250;
    const detail = document.querySelector("#floorDetail");
    if (detail && !detail.hidden) return 100;
    const viewport = document.querySelector("#tradingFloorViewport");
    if (viewport?.classList.contains("dragging")) return 1000 / 60;
    return 1000 / 30;
  }

  window.requestAnimationFrame = callback => {
    const id = nextId++;
    let nativeId = 0;
    let lastDelivery = performance.now();
    const pump = now => {
      if (!scheduled.has(id)) return;
      if (now - lastDelivery >= targetFrameMs()) {
        scheduled.delete(id);
        callback(now);
        return;
      }
      nativeId = nativeRequest(pump);
      scheduled.set(id, nativeId);
    };
    nativeId = nativeRequest(pump);
    scheduled.set(id, nativeId);
    return id;
  };

  window.cancelAnimationFrame = id => {
    const nativeId = scheduled.get(id);
    if (nativeId !== undefined) nativeCancel(nativeId);
    scheduled.delete(id);
  };

  /*
   * Performance UI v3 is intentionally isolated from the trading/runtime core.
   * It is presentation-only progressive disclosure: Investor -> Quant and
   * Firm -> Portfolio/Layer -> Desk. Loading after DOMContentLoaded guarantees
   * mock-data, hierarchy and the base app have initialized before replacement.
   * Native Windows handoff: keep this view-model boundary; never let a UI scope
   * selector mutate broker, risk, execution, or ledger state.
   */
  window.addEventListener("DOMContentLoaded", () => {
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "performance-dashboard-v30.css";
    document.head.append(style);
    const script = document.createElement("script");
    script.src = "performance-dashboard-v30.js";
    script.defer = true;
    document.body.append(script);
  }, {once:true});
})();
