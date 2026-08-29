(() => {
  "use strict";

  const root = document.querySelector("#performance .performance-layout");
  const data = window.DUSTY_MOCK;
  if (!root || !data?.performance) return;

  const perf = data.performance;
  const policy = data.performancePolicy || {};
  const FY_MONTH = 9;
  const DAY_MS = 86_400_000;
  const MORPH_MS = 460;
  const monthlyObjective = Number(
    policy.objective?.monthlyEffectivePct ?? data.firm?.monthlyTargetPct ?? 5
  );
  const drawdownWatchPct = Number(policy.risk?.drawdownWatchPct ?? 5);
  const asOf = resolveAsOf(perf.asOfUtc);

  const panel = root.querySelector("#perfChartPanel");
  const chart = root.querySelector("#perfGrowthChart");
  const readout = root.querySelector("#perfChartReadout");
  if (!panel || !chart || !readout) return;

  const labels = ["MONTHLY", "QUARTERLY", "ANNUAL", "5 YEAR"];
  const builders = [buildMonth, buildQuarter, buildYear, buildFiveYear];
  let selected = 0;
  let rendering = false;
  let morphTimer = 0;
  let morphToken = 0;

  const controls = document.createElement("div");
  controls.className = "perf-timeframe-slider-control";
  controls.innerHTML = `
    <div class="perf-timeframe-heading">
      <span>REPORTING HORIZON</span>
      <strong id="perfTimeframeValue">MONTHLY</strong>
    </div>
    <div class="perf-timeframe-slider-wrap">
      <input id="perfTimeframeSlider" type="range" min="0" max="3" step="1" value="0"
        aria-label="Investor reporting horizon" aria-valuetext="Monthly">
      <div class="perf-timeframe-slider-labels" aria-hidden="true">
        ${labels.map(label => `<span>${label}</span>`).join("")}
      </div>
    </div>`;
  panel.querySelector("header")?.insertAdjacentElement("afterend", controls);

  const legend = document.createElement("div");
  legend.className = "perf-investor-legend";
  legend.innerHTML = `
    <span><i class="legend-actual-bar"></i>ACTUAL CAPITAL / RETURN</span>
    <span><i class="legend-line"></i>ABSOLUTE-RETURN OBJECTIVE</span>
    <span><i class="legend-today"></i>AS-OF DATE</span>
    <span><i class="legend-hwm"></i>HIGH-WATER MARK</span>
    <span><i class="legend-floor"></i>DRAWDOWN WATCH FLOOR</span>
    <span class="perf-benchmark-state">BENCHMARK · ${policy.benchmark?.status || "UNSELECTED"}</span>`;
  controls.insertAdjacentElement("afterend", legend);

  const staticControls = document.createElement("div");
  staticControls.className = "perf-timeframe-static-controls";
  staticControls.setAttribute("role", "group");
  staticControls.setAttribute("aria-label", "Investor reporting horizon");
  staticControls.innerHTML = labels
    .map(
      (label, index) =>
        `<button type="button" data-timeframe="${index}" ${
          index === 0 ? 'class="active" aria-pressed="true"' : 'aria-pressed="false"'
        }>${label}</button>`
    )
    .join("");
  chart.insertAdjacentElement("afterend", staticControls);

  const ribbon = document.createElement("div");
  ribbon.className = "perf-capital-depth-ribbon";
  readout.insertAdjacentElement("afterend", ribbon);

  const slider = controls.querySelector("#perfTimeframeSlider");
  const valueLabel = controls.querySelector("#perfTimeframeValue");
  const buttons = [...staticControls.querySelectorAll("[data-timeframe]")];
  const reduceMotionQuery = matchMedia("(prefers-reduced-motion: reduce)");

  function buildMonth() {
    const start = new Date(asOf.getFullYear(), asOf.getMonth(), 1);
    const end = endOfMonth(asOf);
    return horizon("month", "MONTHLY", start, end, compound(1), "1-MONTH EFFECTIVE OBJECTIVE");
  }

  function buildQuarter() {
    const { start, end, quarter, fiscalStart } = quarterBounds(asOf);
    return horizon("quarter", "QUARTERLY", start, end, compound(3), `${fiscalYearLabel(fiscalStart)} · Q${quarter}`);
  }

  function buildYear() {
    const start = fiscalYearStart(asOf);
    const end = fiscalYearEnd(start);
    return horizon("year", "ANNUAL", start, end, compound(12), `${fiscalYearLabel(start)} · OCT-SEP`);
  }

  function buildFiveYear() {
    const start = fiscalYearStart(asOf);
    start.setFullYear(start.getFullYear() - 4);
    const end = fiscalYearEnd(new Date(start.getFullYear() + 4, start.getMonth(), 1));
    return horizon("fiveYear", "5 YEAR", start, end, compound(60), `${fiscalYearLabel(start)} → FY${end.getFullYear()}`);
  }

  function horizon(id, label, start, end, target, note) {
    return {
      id,
      label,
      start,
      end,
      target,
      note,
      actual: normalizedSeries(id, start, end)
    };
  }

  function normalizedSeries(id, start, end) {
    const canonical = perf.horizonSeries?.[id];
    if (Array.isArray(canonical) && canonical.length) {
      return canonical
        .map(point => normalizeCanonicalPoint(point))
        .filter(Boolean)
        .filter(point => point.date >= start && point.date <= end && point.date <= asOf)
        .sort((a, b) => a.date - b.date);
    }

    // Legacy monthly mock compatibility only. Production should not emit this shape.
    if (id === "month" && Array.isArray(perf.returns) && perf.returns.length) {
      const visibleEnd = new Date(Math.min(asOf.getTime(), end.getTime()));
      return perf.returns
        .map((value, index, source) => ({
          date: new Date(
            start.getTime() +
              ((visibleEnd.getTime() - start.getTime()) * index) /
                Math.max(1, source.length - 1)
          ),
          value: Number(value)
        }))
        .filter(point => Number.isFinite(point.value));
    }

    return [];
  }

  function normalizeCanonicalPoint(point) {
    if (!point || typeof point !== "object") return null;
    const date = parseUtc(point.atUtc);
    const value = Number(point.cumulativeReturnPct);
    if (!date || !Number.isFinite(value)) return null;
    return { date, value };
  }

  function context(config) {
    const scope = root.querySelector("#perfScope")?.value || "firm";
    if (scope === "layer") {
      return {
        available: false,
        reason: "No authoritative Layer aggregate capital history is exposed by the current read model."
      };
    }

    if (scope === "desk") {
      const id = root.querySelector("#perfEntity")?.value;
      const desk = (data.desks || []).find(item => item.id === id);
      if (!desk) return { available: false, reason: "Selected desk read model is unavailable." };
      return {
        available: true,
        label: id,
        equity: numberOrNull(desk.equity),
        currentDd: numberOrNull(desk.dd),
        realized: numberOrNull(desk.mtd),
        objective: null,
        actual: [],
        provenance: "CURRENT DESK SNAPSHOT"
      };
    }

    const actual = config.actual || [];
    const realized = actual.length
      ? actual[actual.length - 1].value
      : config.id === "month"
        ? numberOrNull(data.firm?.pnlMonthPct)
        : null;

    return {
      available: true,
      label: "FIRM",
      equity: numberOrNull(data.firm?.equity),
      currentDd: numberOrNull(data.firm?.drawdownPct),
      realized,
      objective: config.target,
      actual,
      provenance: perf.historyProvenance || "READ_MODEL"
    };
  }

  function capitalReferences(ctx) {
    if (!ctx.available || ctx.equity == null || ctx.realized == null || ctx.realized <= -100) {
      return {};
    }
    const startCapital = ctx.equity / (1 + ctx.realized / 100);
    const hwm =
      ctx.currentDd != null && ctx.currentDd >= 0 && ctx.currentDd < 100
        ? ctx.equity / (1 - ctx.currentDd / 100)
        : null;
    const watchFloor = hwm == null ? null : hwm * (1 - drawdownWatchPct / 100);
    return {
      startCapital,
      hwm,
      watchFloor,
      hwmReturn: hwm == null ? null : (hwm / startCapital - 1) * 100,
      watchFloorReturn:
        watchFloor == null ? null : (watchFloor / startCapital - 1) * 100
    };
  }

  function render(config = builders[selected](), updateReadout = true) {
    if (rendering) return;
    rendering = true;
    try {
      const ctx = context(config);
      const refs = capitalReferences(ctx);
      chart.innerHTML = buildSvg(config, panel.classList.contains("expanded"), ctx, refs);
      if (updateReadout) renderReadout(config, ctx, refs);
    } finally {
      rendering = false;
    }
  }

  function buildSvg(config, expanded, ctx, refs) {
    if (!ctx.available) {
      return `<div class="perf-chart-unavailable"><strong>CAPITAL PATH UNAVAILABLE</strong><span>${ctx.reason}</span></div>`;
    }

    const width = expanded ? 1180 : 900;
    const height = expanded ? 470 : 300;
    const pad = { l: expanded ? 74 : 62, r: expanded ? 84 : 72, t: 34, b: expanded ? 72 : 60 };
    const actual = ctx.actual || [];
    const objective = ctx.objective;
    const values = [
      0,
      ctx.realized,
      objective,
      refs.hwmReturn,
      refs.watchFloorReturn,
      ...actual.map(point => point.value)
    ].filter(Number.isFinite);

    let min = Math.min(0, ...values);
    let max = Math.max(1, ...values);
    const valueRange = Math.max(1, max - min);
    min -= valueRange * 0.1;
    max += valueRange * 0.13;

    const span = Math.max(DAY_MS, config.end - config.start);
    const x = date =>
      pad.l + clamp((date - config.start) / span, 0, 1) * (width - pad.l - pad.r);
    const y = value => pad.t + ((max - value) / (max - min)) * (height - pad.t - pad.b);
    const currentDate = new Date(clamp(asOf.getTime(), config.start.getTime(), config.end.getTime()));
    const currentX = x(currentDate);
    const baselineY = y(0);
    const rightMoney = value =>
      refs.startCapital == null ? null : refs.startCapital * (1 + value / 100);

    const gridValues = Array.from({ length: 6 }, (_, index) => min + ((max - min) * index) / 5);
    const grids = gridValues
      .map(
        value => `<g>
          <line class="chart-gridline" x1="${pad.l}" x2="${width - pad.r}" y1="${y(value)}" y2="${y(value)}"/>
          <text class="chart-axis-label" x="${pad.l - 9}" y="${y(value) + 4}" text-anchor="end">${value.toFixed(Math.abs(max - min) >= 100 ? 0 : 1)}%</text>
          ${
            refs.startCapital == null
              ? ""
              : `<text class="chart-capital-axis" x="${width - pad.r + 9}" y="${y(value) + 4}">${money(rightMoney(value))}</text>`
          }
        </g>`
      )
      .join("");

    const plotWidth = Math.max(1, currentX - pad.l);
    const barWidth = Math.max(4, Math.min(expanded ? 32 : 24, (plotWidth / Math.max(1, actual.length)) * 0.62));
    const bars = actual
      .map((point, index) => {
        const py = y(point.value);
        const top = Math.min(py, baselineY);
        const barHeight = Math.max(1, Math.abs(baselineY - py));
        const bx = clamp(
          Math.min(x(point.date) - barWidth / 2, currentX - barWidth),
          pad.l,
          width - pad.r - barWidth
        );
        return `<rect class="investor-actual-bar ${index === actual.length - 1 ? "investor-current-bar" : ""}" x="${bx}" y="${top}" width="${barWidth}" height="${barHeight}" rx="2"><title>${formatDate(point.date)} · actual ${percent(point.value)}</title></rect>`;
      })
      .join("");

    const objectivePoints =
      objective == null
        ? ""
        : Array.from({ length: 81 }, (_, index) => {
            const fraction = index / 80;
            const date = new Date(config.start.getTime() + span * fraction);
            return `${x(date)},${y(objectiveAt(objective, fraction))}`;
          }).join(" ");
    const objectiveLine =
      objective == null
        ? ""
        : `<polyline class="investor-target-line" points="${objectivePoints}"/>`;

    const objectiveToday =
      objective == null ? null : objectiveAt(objective, elapsed(config.start, config.end, asOf));
    const gap =
      ctx.realized == null || objectiveToday == null ? null : ctx.realized - objectiveToday;
    const gapMark = buildGapMark(currentX, y, ctx.realized, objectiveToday, gap);
    const protection = buildProtectionBand(pad, currentX, y, refs);
    const dateAxis = buildDateAxis(config, x, height, pad);

    const badgeWidth = 110;
    const badgeHeight = 22;
    const badgeX = clamp(currentX - badgeWidth / 2, pad.l, width - pad.r - badgeWidth);
    const badgeY = pad.t - badgeHeight;
    const todayMark = `<g class="chart-today">
      <rect x="${badgeX}" y="${badgeY}" width="${badgeWidth}" height="${badgeHeight}" rx="3"/>
      <text x="${badgeX + badgeWidth / 2}" y="${badgeY + 15}" text-anchor="middle">AS OF · ${formatShortDate(asOf)}</text>
      <line x1="${currentX}" x2="${currentX}" y1="${badgeY + badgeHeight - 2}" y2="${height - pad.b}"/>
    </g>`;

    const rangeLabels = `<text class="chart-range-label" x="${pad.l}" y="${height - 9}">${formatDate(config.start)}</text>
      <text class="chart-range-label" x="${width - pad.r}" y="${height - 9}" text-anchor="end">${formatDate(config.end)}</text>`;
    const title = `<text class="chart-axis-title chart-axis-title-left" x="${pad.l}" y="${pad.t - 12}">CUMULATIVE RETURN</text>`;

    return `<svg class="investor-detail-chart investor-depth-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${config.label} Dusty Dragon capital and objective view. Green vertical bars are actual cumulative returns through the as-of date; objective, high-water mark and drawdown-watch floor are separate.">${grids}${protection}${bars}${objectiveLine}${gapMark}${todayMark}${dateAxis}${rangeLabels}${title}</svg>`;
  }

  function buildGapMark(currentX, y, realized, objectiveToday, gap) {
    if (gap == null) return "";
    const middleY = (y(realized) + y(objectiveToday)) / 2;
    const boxWidth = 58;
    const boxHeight = 18;
    const boxX = currentX - 74;
    const boxY = middleY - boxHeight / 2;
    return `<g class="chart-objective-gap">
      <line x1="${currentX - 10}" x2="${currentX - 10}" y1="${y(realized)}" y2="${y(objectiveToday)}"/>
      <rect class="chart-objective-gap-box" x="${boxX}" y="${boxY}" width="${boxWidth}" height="${boxHeight}" rx="3"/>
      <text class="chart-objective-gap-value" x="${boxX + boxWidth / 2}" y="${boxY + 12}" text-anchor="middle">${gap >= 0 ? "+" : ""}${gap.toFixed(2)} pts</text>
    </g>`;
  }

  function buildProtectionBand(pad, currentX, y, refs) {
    if (refs.hwmReturn == null || refs.watchFloorReturn == null) return "";
    return `<g class="chart-capital-protection">
      <rect x="${pad.l}" y="${y(refs.hwmReturn)}" width="${Math.max(0, currentX - pad.l)}" height="${Math.max(0, y(refs.watchFloorReturn) - y(refs.hwmReturn))}"/>
      <line class="chart-hwm-line" x1="${pad.l}" x2="${currentX}" y1="${y(refs.hwmReturn)}" y2="${y(refs.hwmReturn)}"/>
      <text class="chart-ref-label chart-hwm-label" x="${pad.l + 6}" y="${y(refs.hwmReturn) - 5}">HWM ${money(refs.hwm)}</text>
      <line class="chart-watch-floor" x1="${pad.l}" x2="${currentX}" y1="${y(refs.watchFloorReturn)}" y2="${y(refs.watchFloorReturn)}"/>
      <text class="chart-ref-label chart-floor-label" x="${pad.l + 6}" y="${y(refs.watchFloorReturn) + 13}">WATCH FLOOR ${money(refs.watchFloor)}</text>
    </g>`;
  }

  function buildDateAxis(config, x, height, pad) {
    const ticks = dateTicks(config);
    return ticks
      .map(
        (date, index) => `<g class="chart-date-tick">
          <line x1="${x(date)}" x2="${x(date)}" y1="${height - pad.b}" y2="${height - pad.b + 5}"/>
          <text class="chart-axis-label chart-date-label" x="${x(date)}" y="${height - pad.b + 20}" text-anchor="middle">${dateLabel(config, date, index, ticks.length)}</text>
        </g>`
      )
      .join("");
  }

  function renderReadout(config, ctx, refs) {
    if (!ctx.available) {
      readout.innerHTML = `<div><b>—</b><span>ACTUAL</span></div><div><b>—</b><span>OBJECTIVE</span></div><div><b>—</b><span>VARIANCE</span></div><p>${ctx.reason}</p>`;
      ribbon.innerHTML = `<div><span>DATA COVERAGE</span><b>UNAVAILABLE</b><small>no synthetic aggregate</small></div>`;
      return;
    }

    const objectiveToday =
      ctx.objective == null ? null : objectiveAt(ctx.objective, elapsed(config.start, config.end, asOf));
    const delta =
      ctx.realized == null || objectiveToday == null ? null : ctx.realized - objectiveToday;

    readout.innerHTML = `<div><b>${percent(ctx.realized)}</b><span>REALIZED · AS OF ${formatShortDate(asOf)}</span></div>
      <div><b>${percent(objectiveToday)}</b><span>OBJECTIVE AT AS-OF</span></div>
      <div><b class="${delta == null ? "" : delta >= 0 ? "positive" : "caution"}">${
        delta == null ? "—" : `${delta >= 0 ? "+" : ""}${delta.toFixed(2)} pts`
      }</b><span>VARIANCE TO OBJECTIVE</span></div>
      <p>${ctx.provenance === "MOCK_SIMULATED" ? "Simulated UI-lab history. " : ""}Green vertical bars show observed cumulative performance through the as-of date. Objective, HWM and drawdown-watch floor remain independent references.</p>`;

    const endpoint =
      refs.startCapital == null || ctx.objective == null
        ? null
        : refs.startCapital * (1 + ctx.objective / 100);
    ribbon.innerHTML = `<div><span>PERIOD START CAPITAL</span><b>${money(refs.startCapital)}</b><small>derived from current equity and cumulative return</small></div>
      <div><span>CURRENT HIGH-WATER MARK</span><b>${money(refs.hwm)}</b><small>${
        ctx.currentDd == null ? "drawdown unavailable" : `${ctx.currentDd.toFixed(2)}% current drawdown`
      }</small></div>
      <div><span>${drawdownWatchPct.toFixed(1)}% DRAWDOWN WATCH FLOOR</span><b>${money(refs.watchFloor)}</b><small>policy reference from current HWM</small></div>
      <div><span>HORIZON OBJECTIVE CAPITAL</span><b>${money(endpoint)}</b><small>${
        ctx.objective == null ? "no scope-specific objective" : `${percent(ctx.objective)} cumulative objective`
      }</small></div>`;
  }

  function syncControls() {
    valueLabel.textContent = labels[selected];
    slider.value = String(selected);
    slider.setAttribute("aria-valuetext", labels[selected]);
    buttons.forEach((button, index) => {
      const active = index === selected;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function select(index) {
    cancelMorph();
    selected = clamp(index, 0, 3);
    syncControls();
    render(builders[selected]());
  }

  function animateTo(index) {
    const destination = clamp(index, 0, 3);
    if (destination === selected) return;
    if (noMotion()) {
      select(destination);
      return;
    }

    cancelMorph();
    const token = morphToken;
    const from = builders[selected]();
    const to = builders[destination]();
    const started = performance.now();
    selected = destination;
    syncControls();

    const step = () => {
      if (token !== morphToken) return;
      if (noMotion()) {
        render(builders[selected]());
        return;
      }
      const progress = clamp((performance.now() - started) / MORPH_MS, 0, 1);
      render(blendConfigs(from, to, progress), progress >= 1);
      if (progress < 1) morphTimer = setTimeout(step, 16);
      else {
        morphTimer = 0;
        render(builders[selected]());
      }
    };
    step();
  }

  function blendConfigs(from, to, progress) {
    const t = smooth(progress);
    const start = new Date(lerp(from.start.getTime(), to.start.getTime(), t));
    const end = new Date(lerp(from.end.getTime(), to.end.getTime(), t));
    const count = Math.max(from.actual.length, to.actual.length);
    const actual = count
      ? Array.from({ length: count }, (_, index) => {
          const fraction = index / Math.max(1, count - 1);
          const fromValue = sampleSeries(from.actual, fraction);
          const toValue = sampleSeries(to.actual, fraction);
          const value =
            fromValue == null
              ? toValue
              : toValue == null
                ? fromValue
                : lerp(fromValue, toValue, t);
          return {
            date: new Date(lerp(start.getTime(), Math.min(asOf.getTime(), end.getTime()), fraction)),
            value
          };
        }).filter(point => point.value != null)
      : [];
    return {
      id: t < 0.5 ? from.id : to.id,
      label: t < 0.5 ? from.label : to.label,
      start,
      end,
      target: lerp(from.target, to.target, t),
      actual,
      note: t < 0.5 ? from.note : to.note,
      transitioning: true
    };
  }

  function sampleSeries(series, fraction) {
    if (!series.length) return null;
    if (series.length === 1) return Number(series[0].value);
    const position = clamp(fraction, 0, 1) * (series.length - 1);
    const left = Math.floor(position);
    const right = Math.min(series.length - 1, left + 1);
    return lerp(Number(series[left].value), Number(series[right].value), position - left);
  }

  function cancelMorph() {
    morphToken += 1;
    if (morphTimer) clearTimeout(morphTimer);
    morphTimer = 0;
  }

  function noMotion() {
    return document.body.classList.contains("render-no-motion") || reduceMotionQuery.matches;
  }

  function dateTicks(config) {
    if (config.transitioning) {
      const span = config.end - config.start;
      return [0, 0.25, 0.5, 0.75, 1].map(
        fraction => new Date(config.start.getTime() + span * fraction)
      );
    }
    if (config.id === "month") {
      return [
        config.start,
        new Date(config.start.getFullYear(), config.start.getMonth(), 8),
        new Date(config.start.getFullYear(), config.start.getMonth(), 15),
        new Date(config.start.getFullYear(), config.start.getMonth(), 22),
        config.end
      ];
    }
    if (config.id === "quarter") {
      return [
        config.start,
        new Date(config.start.getFullYear(), config.start.getMonth() + 1, 1),
        new Date(config.start.getFullYear(), config.start.getMonth() + 2, 1),
        config.end
      ];
    }
    if (config.id === "year") {
      return [0, 2, 4, 6, 8, 10, 11].map(
        month => new Date(config.start.getFullYear(), config.start.getMonth() + month, 1)
      );
    }
    return [0, 1, 2, 3, 4].map(
      year => new Date(config.start.getFullYear() + year, config.start.getMonth(), 1)
    );
  }

  function dateLabel(config, date, index, count) {
    const endpoint = index === 0 || index === count - 1;
    if (config.transitioning) {
      return endpoint
        ? formatDate(date)
        : date.toLocaleDateString(undefined, { month: "short", year: "2-digit" }).toUpperCase();
    }
    if (config.id === "month") {
      return endpoint
        ? `${date.toLocaleDateString(undefined, { month: "short" }).toUpperCase()} ${date.getDate()}`
        : String(date.getDate()).padStart(2, "0");
    }
    if (config.id === "quarter") {
      return endpoint
        ? formatShortDate(date)
        : date.toLocaleDateString(undefined, { month: "short" }).toUpperCase();
    }
    if (config.id === "year") {
      return date.toLocaleDateString(undefined, { month: "short" }).toUpperCase();
    }
    return `FY${fiscalYearEnd(date).getFullYear()}`;
  }

  function quarterBounds(date) {
    const fiscalStart = fiscalYearStart(date);
    const monthIndex =
      (date.getFullYear() - fiscalStart.getFullYear()) * 12 +
      date.getMonth() -
      fiscalStart.getMonth();
    const quarter = Math.floor(monthIndex / 3);
    return {
      start: new Date(fiscalStart.getFullYear(), fiscalStart.getMonth() + quarter * 3, 1),
      end: new Date(fiscalStart.getFullYear(), fiscalStart.getMonth() + quarter * 3 + 3, 0),
      quarter: quarter + 1,
      fiscalStart
    };
  }

  function fiscalYearStart(date) {
    return new Date(
      date.getMonth() >= FY_MONTH ? date.getFullYear() : date.getFullYear() - 1,
      FY_MONTH,
      1
    );
  }

  function fiscalYearEnd(start) {
    return new Date(start.getFullYear() + 1, FY_MONTH, 0);
  }

  function fiscalYearLabel(start) {
    return `FY${fiscalYearEnd(start).getFullYear()}`;
  }

  function endOfMonth(date) {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
  }

  function compound(months) {
    return (Math.pow(1 + monthlyObjective / 100, months) - 1) * 100;
  }

  function objectiveAt(horizonReturn, fraction) {
    return (
      Math.pow(1 + Math.max(-0.999999, horizonReturn / 100), clamp(fraction, 0, 1)) - 1
    ) * 100;
  }

  function elapsed(start, end, at) {
    return clamp((at - start) / Math.max(DAY_MS, end - start), 0, 1);
  }

  function resolveAsOf(raw) {
    const parsed = parseUtc(raw);
    if (parsed) return parsed;
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function parseUtc(raw) {
    if (typeof raw !== "string" || !raw.endsWith("Z")) return null;
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function numberOrNull(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function percent(value, digits = 2) {
    return value == null ? "—" : `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(digits)}%`;
  }

  function money(value) {
    return value == null
      ? "—"
      : Number(value).toLocaleString(undefined, {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 0
        });
  }

  function formatDate(date) {
    return date
      .toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
      .toUpperCase();
  }

  function formatShortDate(date) {
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" }).toUpperCase();
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function smooth(t) {
    return t * t * (3 - 2 * t);
  }

  slider.addEventListener("input", event => animateTo(Number(event.target.value) || 0));
  buttons.forEach((button, index) => button.addEventListener("click", () => select(index)));
  const scheduleRender = () => setTimeout(() => render(builders[selected]()), 0);
  root.querySelector("#perfScope")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfEntity")?.addEventListener("change", scheduleRender);
  root.querySelector("#perfExpandChart")?.addEventListener("click", scheduleRender);
  window.addEventListener("dusty:performance-chart-resize", scheduleRender);
  new MutationObserver(() => {
    if (noMotion()) cancelMorph();
    syncControls();
    render(builders[selected]());
  }).observe(document.body, { attributes: true, attributeFilter: ["class"] });

  window.DUSTY_PERFORMANCE_TIMEFRAME = Object.freeze({
    version: "3.7",
    objectiveType: "ABSOLUTE_RETURN_OBJECTIVE",
    actualMark: "VERTICAL_BARS",
    historyContract: "DATED_CUMULATIVE_RETURN_SERIES_UTC",
    compounding: "GEOMETRIC",
    syntheticHorizonActuals: false
  });

  syncControls();
  render();
})();
