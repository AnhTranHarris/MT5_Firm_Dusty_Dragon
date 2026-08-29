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

  /* Presentation adapters are loaded deterministically so the future
     WinUI/WebView2 host can replace fixtures without changing UI semantics. */
  window.addEventListener("DOMContentLoaded", () => {
    [
      "performance-dashboard-v30.css",
      "performance-quant-v32.css",
      "performance-timeframe-v36.css",
      "performance-layout-v36.css",
      "performance-scope-v38.css",
      "performance-panel-sync-v39.css",
      "hierarchy-tree-density-v30.css",
      "command-capital-milestones-v31.css",
      "command-timeline-v32.css"
    ].forEach(href => {
      const style=document.createElement("link");
      style.rel="stylesheet";
      style.href=href;
      document.head.append(style);
    });

    const load=(src,onload)=>{const script=document.createElement("script");script.src=src;if(onload)script.onload=onload;document.body.append(script);};
    load("hierarchy-tree-density-v30.js");
    load("command-timeline-v32.js");
    load("capital-planning-mock-v33.js",()=>load("command-capital-milestones-v31.js"));
    load("performance-scope-mock-v39.js",()=>load("performance-quant-scope-mock-v40.js",()=>load("performance-dashboard-v33.js",()=>load("performance-timeframe-v38.js",()=>load("performance-panel-sync-v39.js",()=>{
      load("performance-state-language-v310.js",()=>load("performance-quant-sync-v41.js"));
    })))));
  }, { once:true });
})();