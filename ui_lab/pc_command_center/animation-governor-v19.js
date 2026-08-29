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
   * Performance v4.1 keeps one synchronized scope and one four-slot diagnostic
   * rail. Investor/Quant lens changes replace rail semantics in place; they do
   * not create a second dashboard or alter Core/MT5 authority.
   */
  window.addEventListener(
    "DOMContentLoaded",
    () => {
      [
        "performance-dashboard-v30.css",
        "performance-quant-v32.css",
        "performance-timeframe-v36.css",
        "performance-layout-v36.css",
        "performance-scope-v38.css",
        "performance-panel-sync-v39.css"
      ].forEach(href => {
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = href;
        document.head.append(style);
      });

      const scopeFixture = document.createElement("script");
      scopeFixture.src = "performance-scope-mock-v39.js";
      scopeFixture.onload = () => {
        const quantFixture = document.createElement("script");
        quantFixture.src = "performance-quant-scope-mock-v40.js";
        quantFixture.onload = () => {
          const dashboard = document.createElement("script");
          dashboard.src = "performance-dashboard-v33.js";
          dashboard.onload = () => {
            const timeframe = document.createElement("script");
            timeframe.src = "performance-timeframe-v38.js";
            timeframe.onload = () => {
              const panelSync = document.createElement("script");
              panelSync.src = "performance-panel-sync-v39.js";
              panelSync.onload = () => {
                const quantSync = document.createElement("script");
                quantSync.src = "performance-quant-sync-v41.js";
                quantSync.defer = true;
                document.body.append(quantSync);
              };
              document.body.append(panelSync);
            };
            document.body.append(timeframe);
          };
          document.body.append(dashboard);
        };
        document.body.append(quantFixture);
      };
      document.body.append(scopeFixture);
    },
    { once: true }
  );
})();