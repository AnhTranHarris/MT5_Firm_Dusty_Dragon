(() => {
  "use strict";
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
   * Performance is read-only presentation. v3.7 consumes dated UTC cumulative-
   * return series from a canonical read model. The UI never derives authoritative
   * quarterly/annual/5Y results from MTD/WTD values and never touches broker,
   * risk, ledger, objective, or execution authority.
   */
  window.addEventListener(
    "DOMContentLoaded",
    () => {
      [
        "performance-dashboard-v30.css",
        "performance-quant-v32.css",
        "performance-timeframe-v36.css",
        "performance-layout-v36.css"
      ].forEach(href => {
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = href;
        document.head.append(style);
      });

      const dashboard = document.createElement("script");
      dashboard.src = "performance-dashboard-v32.js";
      dashboard.onload = () => {
        const timeframe = document.createElement("script");
        timeframe.src = "performance-timeframe-v37.js";
        timeframe.defer = true;
        document.body.append(timeframe);
      };
      document.body.append(dashboard);
    },
    { once: true }
  );
})();
