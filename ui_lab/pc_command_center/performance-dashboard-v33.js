(() => {
  "use strict";

  /*
   * PERFORMANCE SHELL v3.4
   * ----------------------
   * Owns structure, lens state and chart expansion only. Investor and Quant use
   * the same four physical rail slots so switching lenses preserves information
   * geography instead of appending a second dashboard below the first.
   *
   * Investor values: performance-panel-sync-v39.js
   * Quant values:    performance-quant-sync-v41.js
   * Scope/chart:     performance-timeframe-v38.js
   *
   * Windows migration: keep these rail slots presentation-only. A lens change
   * changes labels/renderers, never Performance scope, MT5, risk or ledger state.
   */

  const root = document.querySelector("#performance .performance-layout");
  if (!root) return;

  let lens = "investor";
  let chartExpanded = false;

  root.innerHTML = `
    <article class="panel perf-commandbar">
      <div class="perf-titleblock">
        <span class="eyebrow">PERFORMANCE</span>
        <strong id="perfScopeTitle">DUSTY DRAGON · FIRM</strong>
        <small id="perfScopeNote">Investor view · synchronized firm read model.</small>
      </div>
      <div class="perf-controls">
        <div class="segmented" aria-label="Performance lens">
          <button type="button" data-lens="investor" class="active" aria-pressed="true">INVESTOR</button>
          <button type="button" data-lens="quant" aria-pressed="false">QUANT</button>
        </div>
      </div>
    </article>
    <section class="perf-headline" id="perfHeadline" aria-label="Performance headline metrics"></section>
    <article class="panel perf-capital" id="perfChartPanel">
      <header>
        <span>CAPITAL & OBJECTIVES</span>
        <span class="perf-chart-actions"><span>REALIZED vs OBJECTIVE</span><button id="perfExpandChart" type="button" aria-expanded="false">EXPAND ↗</button></span>
      </header>
      <div id="perfGrowthChart" class="perf-growth-chart"></div>
      <div id="perfChartReadout" class="perf-chart-readout"></div>
    </article>
    <article class="panel perf-protection perf-lens-panel" data-quant-section="absolute"><header><span data-panel-title>CAPITAL PROTECTION</span><span id="perfProtectionState" data-panel-state>POLICY SNAPSHOT</span></header><div id="perfProtection" class="perf-card-grid"></div></article>
    <article class="panel perf-quality perf-lens-panel" data-quant-section="trade"><header><span data-panel-title>RETURN QUALITY</span><span id="perfQualityState" data-panel-state>OBSERVED METRICS</span></header><div id="perfQuality" class="perf-card-grid"></div></article>
    <article class="panel perf-exposure perf-lens-panel" data-quant-section="tail"><header><span data-panel-title>LIQUIDITY & EXPOSURE</span><span id="perfExposureState" data-panel-state>FIRM FOOTPRINT</span></header><div id="perfExposure" class="perf-card-grid"></div></article>
    <article class="panel perf-contributors perf-lens-panel" data-quant-section="benchmark"><header><span data-panel-title>RETURN ATTRIBUTION</span><span id="perfContributionScope" data-panel-state>RECONCILED</span></header><div id="perfContributors"></div></article>
    <article class="panel perf-investor-notes"><header><span>INVESTOR READOUT</span><span id="perfInvestorState">MEASURED / POLICY-AWARE</span></header><div id="perfInvestorNotes"></div></article>`;

  const lensButtons = [...root.querySelectorAll("[data-lens]")];
  const chartPanel = root.querySelector("#perfChartPanel");
  const expandButton = root.querySelector("#perfExpandChart");

  function setLens(next) {
    lens = next === "quant" ? "quant" : "investor";
    lensButtons.forEach(button => {
      const active = button.dataset.lens === lens;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    document.body.classList.toggle("perf-quant-active", lens === "quant");
    window.dispatchEvent(new CustomEvent("dusty:performance-lens-changed", { detail:{ lens } }));
  }

  function setChartExpanded(expanded) {
    chartExpanded = Boolean(expanded);
    chartPanel.classList.toggle("expanded", chartExpanded);
    expandButton.setAttribute("aria-expanded", String(chartExpanded));
    expandButton.textContent = chartExpanded ? "CLOSE ×" : "EXPAND ↗";
    window.dispatchEvent(new CustomEvent("dusty:performance-chart-resize"));
  }

  lensButtons.forEach(button => button.addEventListener("click", () => setLens(button.dataset.lens)));
  expandButton.addEventListener("click", () => setChartExpanded(!chartExpanded));
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && chartExpanded) setChartExpanded(false);
  });

  window.DUSTY_PERFORMANCE_SHELL = Object.freeze({
    version:"3.4",
    lens:() => lens,
    setLens,
    chartExpanded:() => chartExpanded
  });

  setLens("investor");
})();