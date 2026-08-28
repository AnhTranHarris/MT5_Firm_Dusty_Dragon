(() => {
  "use strict";

  /*
   * UI-lab animation governor.
   *
   * The Trading Floor renderer uses requestAnimationFrame continuously. That is
   * appropriate while the spatial surface is visible, but it should not spend a
   * full 60 FPS budget when the user is on another workspace, in Analytical
   * mode, looking at a detail overlay, or when the document is backgrounded.
   *
   * This wrapper preserves requestAnimationFrame semantics for the prototype
   * while adapting cadence to actual UX need. CSS animations remain native.
   */
  const nativeRequest = window.requestAnimationFrame.bind(window);
  const nativeCancel = window.cancelAnimationFrame.bind(window);
  const scheduled = new Map();
  let nextId = 1;

  function targetFrameMs() {
    if (document.hidden) return 1000; // effectively asleep in background tabs

    const command = document.querySelector("#command");
    const commandActive = Boolean(command?.classList.contains("active"));
    if (!commandActive) return 250; // renderer stays alive but nearly idle

    if (document.body.classList.contains("analytical-mode")) return 250;

    const detail = document.querySelector("#floorDetail");
    if (detail && !detail.hidden) return 100;

    const viewport = document.querySelector("#tradingFloorViewport");
    if (viewport?.classList.contains("dragging")) return 1000 / 60;

    // Slow orbital motion does not need 60 FPS. 30 FPS is visually continuous
    // here and roughly halves canvas draw pressure on ordinary hardware.
    return 1000 / 30;
  }

  window.requestAnimationFrame = callback => {
    const id = nextId++;
    let nativeId = 0;
    let lastDelivery = performance.now();

    const pump = now => {
      if (!scheduled.has(id)) return;
      const interval = targetFrameMs();
      if (now - lastDelivery >= interval) {
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
})();
