(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const perf = data?.performance;
  if (!data || !perf?.horizonSeries) return;

  /*
   * UI-LAB ONLY — HIERARCHICAL PERFORMANCE FIXTURE
   * ------------------------------------------------
   * This file exists solely to exercise Firm -> Portfolio -> Layer/Desk UX before
   * Dusty Core exposes real scope-specific read models. Nothing in this fixture is
   * broker truth and nothing here may be migrated into production seed history.
   *
   * Production contract: Core emits explicit dated UTC series + current snapshot
   * for every scope. The Windows UI only selects among those immutable read models.
   */

  const HORIZONS = ["month", "quarter", "year", "fiveYear"];
  const portfolioNames = {
    1: "PORTFOLIO 1 · GENERALIST",
    2: "PORTFOLIO 2 · STYLE",
    3: "PORTFOLIO 3 · SECTOR",
    4: "PORTFOLIO 4 · SYMBOL"
  };

  const clonePoint = point => ({
    atUtc: point.atUtc,
    cumulativeReturnPct: Number(point.cumulativeReturnPct)
  });

  function makeDeskSeries(portfolio, deskNumber, horizon) {
    const base = perf.horizonSeries[horizon].map(clonePoint);
    const seed = portfolio * 17 + deskNumber * 11 + HORIZONS.indexOf(horizon) * 7;
    const factor = 0.54 + portfolio * 0.085 + deskNumber * 0.028;
    const amplitude = 0.07 + portfolio * 0.018 + deskNumber * 0.009;
    const sourceDesk = portfolio === 1 ? data.desks?.[deskNumber - 1] : null;
    const explicitMonthlyEndpoint = horizon === "month" ? Number(sourceDesk?.mtd) : null;

    const transformed = base.map((point, index) => {
      if (index === 0) return { ...point, cumulativeReturnPct: 0 };
      const progress = index / Math.max(1, base.length - 1);
      const wave = Math.sin((index + seed) * 1.31) * amplitude * progress;
      return {
        atUtc: point.atUtc,
        cumulativeReturnPct: Number((point.cumulativeReturnPct * factor + wave).toFixed(4))
      };
    });

    if (Number.isFinite(explicitMonthlyEndpoint)) {
      const last = transformed.at(-1);
      const current = Number(last.cumulativeReturnPct);
      const delta = explicitMonthlyEndpoint - current;
      transformed.forEach((point, index) => {
        const progress = index / Math.max(1, transformed.length - 1);
        point.cumulativeReturnPct = Number((point.cumulativeReturnPct + delta * progress).toFixed(4));
      });
    }
    return transformed;
  }

  function deskSnapshot(portfolio, deskNumber, monthSeries) {
    if (portfolio === 1 && data.desks?.[deskNumber - 1]) {
      const source = data.desks[deskNumber - 1];
      return {
        equity: Number(source.equity || 0),
        currentDrawdownPct: Number(source.dd || 0),
        state: source.state || "UNKNOWN"
      };
    }

    const base = Number(data.firm?.equity || 0) / 24;
    const equity = base * (0.82 + portfolio * 0.08 + deskNumber * 0.025);
    const endpoint = Number(monthSeries.at(-1)?.cumulativeReturnPct || 0);
    return {
      equity: Number((equity * (1 + endpoint / 100)).toFixed(2)),
      currentDrawdownPct: Number((0.55 + ((portfolio * 7 + deskNumber * 3) % 24) / 10).toFixed(2)),
      state: "SIMULATED"
    };
  }

  function aggregateSeries(desks, horizon) {
    const series = desks.map(entity => entity.horizonSeries[horizon]);
    const weights = desks.map(entity => Math.max(0, Number(entity.snapshot.equity || 0)));
    const denominator = weights.reduce((sum, value) => sum + value, 0) || desks.length;
    return series[0].map((point, index) => ({
      atUtc: point.atUtc,
      cumulativeReturnPct: Number((
        desks.reduce((sum, _entity, deskIndex) => {
          const weight = denominator === desks.length ? 1 : weights[deskIndex];
          return sum + Number(series[deskIndex][index].cumulativeReturnPct) * weight;
        }, 0) / denominator
      ).toFixed(4))
    }));
  }

  const portfolios = {};
  for (let portfolio = 1; portfolio <= 4; portfolio += 1) {
    const deskEntities = [];
    for (let deskNumber = 1; deskNumber <= 6; deskNumber += 1) {
      const horizonSeries = Object.fromEntries(
        HORIZONS.map(horizon => [horizon, makeDeskSeries(portfolio, deskNumber, horizon)])
      );
      deskEntities.push({
        id: `desk${deskNumber}`,
        label: `DESK ${deskNumber}`,
        provenance: "MOCK_SCOPE_SIMULATED",
        snapshot: deskSnapshot(portfolio, deskNumber, horizonSeries.month),
        horizonSeries
      });
    }

    const layerSeries = Object.fromEntries(
      HORIZONS.map(horizon => [horizon, aggregateSeries(deskEntities, horizon)])
    );
    const layerEquity = deskEntities.reduce((sum, entity) => sum + entity.snapshot.equity, 0);
    const layerDrawdown = Math.max(...deskEntities.map(entity => entity.snapshot.currentDrawdownPct));

    portfolios[portfolio] = {
      id: `portfolio${portfolio}`,
      label: portfolioNames[portfolio],
      entities: {
        layer: {
          id: "layer",
          label: "LAYER",
          provenance: "MOCK_SCOPE_SIMULATED",
          snapshot: {
            equity: Number(layerEquity.toFixed(2)),
            currentDrawdownPct: Number(layerDrawdown.toFixed(2)),
            state: "SIMULATED"
          },
          horizonSeries: layerSeries
        },
        ...Object.fromEntries(deskEntities.map(entity => [entity.id, entity]))
      }
    };
  }

  window.DUSTY_PERFORMANCE_SCOPE_MOCK = Object.freeze({
    contractVersion: "UI_LAB_SCOPE_1",
    asOfUtc: perf.asOfUtc,
    provenance: "MOCK_SCOPE_SIMULATED",
    portfolios
  });
})();