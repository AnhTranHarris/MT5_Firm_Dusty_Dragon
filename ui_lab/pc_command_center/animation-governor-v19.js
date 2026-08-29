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
   * Performance remains read-only presentation. v3.8 adds an independent chart
   * scope selector: Firm or Portfolio 1-4, then Layer / Desk 1-6. UI Lab scope
   * histories are explicitly simulated fixtures. Production must supply immutable
   * Core read models for every scope; presentation never reads MT5 directly.
   */
  window.addEventListener(
    "DOMContentLoaded",
    () => {
      [
        "performance-dashboard-v30.css",
        "performance-quant-v32.css",
        "performance-timeframe-v36.css",
        "performance-layout-v36.css",
        "performance-scope-v38.css"
      ].forEach(href => {
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = href;
        document.head.append(style);
      });

      const scopeFixture = document.createElement("script");
      scopeFixture.src = "performance-scope-mock-v38.js";
      scopeFixture.onload = () => {
        const dashboard = document.createElement("script");
        dashboard.src = "performance-dashboard-v32.js";
        dashboard.onload = () => {
          const timeframe = document.createElement("script");
          timeframe.src = "performance-timeframe-v38.js";
          timeframe.defer = true;
          document.body.append(timeframe);
        };
        document.body.append(dashboard);
      };
      document.body.append(scopeFixture);
    },
    { once: true }
  );
})();
