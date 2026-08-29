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
   * Performance UI is intentionally isolated from the trading/runtime core.
   * Native Windows handoff: preserve this read-model/view-state boundary; UI
   * controls never mutate broker, risk, execution, terminal, ledger, benchmark,
   * volatility-target, or return-objective policy. The quant lens measures
   * absolute efficiency separately from benchmark-relative skill. Spatial
   * profiles use the animated timeframe slider; NO MOTION/HIGH CONTRAST swaps
   * to static buttons below the chart.
   */
  window.addEventListener("DOMContentLoaded", () => {
    const style = document.createElement("link");
    style.rel = "stylesheet";
    style.href = "performance-dashboard-v30.css";
    document.head.append(style);

    const quantStyle = document.createElement("link");
    quantStyle.rel = "stylesheet";
    quantStyle.href = "performance-quant-v32.css";
    document.head.append(quantStyle);

    const timeframeStyle = document.createElement("link");
    timeframeStyle.rel = "stylesheet";
    timeframeStyle.href = "performance-timeframe-v34.css";
    document.head.append(timeframeStyle);

    const script = document.createElement("script");
    script.src = "performance-dashboard-v32.js";
    script.onload = () => {
      const timeframeScript = document.createElement("script");
      timeframeScript.src = "performance-timeframe-v34.js";
      timeframeScript.defer = true;
      document.body.append(timeframeScript);
    };
    document.body.append(script);
  }, {once:true});
})();