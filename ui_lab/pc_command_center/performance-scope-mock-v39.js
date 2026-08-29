(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const perf = data?.performance;
  if (!data || !perf?.horizonSeries) return;

  /*
   * UI-LAB ONLY — HIERARCHICAL PERFORMANCE FIXTURE v3.9
   * -----------------------------------------------------
   * Exercises one shared Firm -> Portfolio -> Layer/Desk selection across every
   * investor panel. None of these scope metrics are broker truth. Production must
   * replace this fixture with immutable Dusty Core read models built from persisted
   * MT5 observations, reconciled capital flows, executions, and risk state.
   */

  const HORIZONS = ["month", "quarter", "year", "fiveYear"];
  const portfolioNames = {
    1: "PORTFOLIO 1 · GENERALIST",
    2: "PORTFOLIO 2 · STYLE",
    3: "PORTFOLIO 3 · SECTOR",
    4: "PORTFOLIO 4 · SYMBOL"
  };

  const finite = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    const parsed = Number(String(value ?? "").replace(/[^0-9.+-]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  const clonePoint = point => ({ atUtc: point.atUtc, cumulativeReturnPct: Number(point.cumulativeReturnPct) });
  const openingCapital = (equity, returnPct) => equity > 0 && returnPct > -100 ? equity / (1 + returnPct / 100) : null;

  function makeDeskSeries(portfolio, deskNumber, horizon) {
    const base = perf.horizonSeries[horizon].map(clonePoint);
    const seed = portfolio * 17 + deskNumber * 11 + HORIZONS.indexOf(horizon) * 7;
    const factor = 0.54 + portfolio * 0.085 + deskNumber * 0.028;
    const amplitude = 0.07 + portfolio * 0.018 + deskNumber * 0.009;
    const sourceDesk = portfolio === 1 ? data.desks?.[deskNumber - 1] : null;
    const explicitMonthlyEndpoint = horizon === "month" ? finite(sourceDesk?.mtd) : null;

    const transformed = base.map((point, index) => {
      if (index === 0) return { ...point, cumulativeReturnPct: 0 };
      const progress = index / Math.max(1, base.length - 1);
      const wave = Math.sin((index + seed) * 1.31) * amplitude * progress;
      return {
        atUtc: point.atUtc,
        cumulativeReturnPct: Number((point.cumulativeReturnPct * factor + wave).toFixed(4))
      };
    });

    if (explicitMonthlyEndpoint != null) {
      const current = Number(transformed.at(-1).cumulativeReturnPct);
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
    const preReturnEquity = base * (0.82 + portfolio * 0.08 + deskNumber * 0.025);
    const endpoint = Number(monthSeries.at(-1)?.cumulativeReturnPct || 0);
    return {
      equity: Number((preReturnEquity * (1 + endpoint / 100)).toFixed(2)),
      currentDrawdownPct: Number((0.55 + ((portfolio * 7 + deskNumber * 3) % 24) / 10).toFixed(2)),
      state: "SIMULATED"
    };
  }

  function deskPanelMetrics(portfolio, deskNumber, snapshot, monthSeries) {
    const source = portfolio === 1 ? data.desks?.[deskNumber - 1] : null;
    const ret = Number(monthSeries.at(-1)?.cumulativeReturnPct || 0);
    const opening = openingCapital(snapshot.equity, ret);
    const freeMarginRatio = Math.max(0.69, 0.94 - portfolio * 0.025 - deskNumber * 0.012);
    return {
      equity: snapshot.equity,
      freeMargin: Number((snapshot.equity * freeMarginRatio).toFixed(2)),
      mtdReturnPct: ret,
      netPnl: opening == null ? null : Number((snapshot.equity - opening).toFixed(2)),
      currentDrawdownPct: snapshot.currentDrawdownPct,
      maxDrawdownPct: Number(Math.max(snapshot.currentDrawdownPct, finite(source?.dd) || 0, 0.8 + portfolio * 0.55 + deskNumber * 0.16).toFixed(2)),
      openRiskPct: Number((finite(source?.risk) ?? (0.42 + portfolio * 0.11 + deskNumber * 0.075)).toFixed(2)),
      winRatePct: Number((56.2 + portfolio * 1.15 + deskNumber * 0.82).toFixed(1)),
      profitFactor: Number((finite(source?.pf) ?? (1.29 + portfolio * 0.08 + deskNumber * 0.045)).toFixed(2)),
      sharpe: Number((finite(source?.sharpe) ?? (0.88 + portfolio * 0.09 + deskNumber * 0.055)).toFixed(2)),
      expectancyR: Number((0.11 + portfolio * 0.025 + deskNumber * 0.018).toFixed(2)),
      grossExposurePct: Number((8.5 + portfolio * 1.2 + deskNumber * 0.72).toFixed(1)),
      netExposurePct: Number((2.1 + portfolio * 0.7 + deskNumber * 0.43).toFixed(1)),
      unresolvedExecutions: 0,
      activeDesks: ["FAULT", "UNBOUND"].includes(snapshot.state) ? 0 : 1,
      totalDesks: 1
    };
  }

  function aggregateSeries(desks, horizon) {
    const series = desks.map(entity => entity.horizonSeries[horizon]);
    const weights = desks.map(entity => Math.max(0, Number(entity.snapshot.equity || 0)));
    const denominator = weights.reduce((sum, value) => sum + value, 0) || desks.length;
    return series[0].map((point, index) => ({
      atUtc: point.atUtc,
      cumulativeReturnPct: Number((desks.reduce((sum, _entity, deskIndex) => {
        const weight = denominator === desks.length ? 1 : weights[deskIndex];
        return sum + Number(series[deskIndex][index].cumulativeReturnPct) * weight;
      }, 0) / denominator).toFixed(4))
    }));
  }

  function weighted(desks, key) {
    const weights = desks.map(entity => Math.max(0, Number(entity.snapshot.equity || 0)));
    const denominator = weights.reduce((sum, value) => sum + value, 0);
    if (!denominator) return null;
    return desks.reduce((sum, entity, index) => sum + Number(entity.panelMetrics[key] || 0) * weights[index], 0) / denominator;
  }

  function layerPanelMetrics(desks, layerSeries, layerSnapshot) {
    return {
      equity: layerSnapshot.equity,
      freeMargin: Number(desks.reduce((sum, entity) => sum + Number(entity.panelMetrics.freeMargin || 0), 0).toFixed(2)),
      mtdReturnPct: Number(layerSeries.month.at(-1)?.cumulativeReturnPct || 0),
      netPnl: Number(desks.reduce((sum, entity) => sum + Number(entity.panelMetrics.netPnl || 0), 0).toFixed(2)),
      currentDrawdownPct: layerSnapshot.currentDrawdownPct,
      maxDrawdownPct: Number(Math.max(...desks.map(entity => Number(entity.panelMetrics.maxDrawdownPct || 0))).toFixed(2)),
      openRiskPct: Number((weighted(desks, "openRiskPct") || 0).toFixed(2)),
      winRatePct: Number((weighted(desks, "winRatePct") || 0).toFixed(1)),
      profitFactor: Number((weighted(desks, "profitFactor") || 0).toFixed(2)),
      sharpe: Number((weighted(desks, "sharpe") || 0).toFixed(2)),
      expectancyR: Number((weighted(desks, "expectancyR") || 0).toFixed(2)),
      grossExposurePct: Number((weighted(desks, "grossExposurePct") || 0).toFixed(1)),
      netExposurePct: Number((weighted(desks, "netExposurePct") || 0).toFixed(1)),
      unresolvedExecutions: desks.reduce((sum, entity) => sum + Number(entity.panelMetrics.unresolvedExecutions || 0), 0),
      activeDesks: desks.filter(entity => !["FAULT", "UNBOUND"].includes(entity.snapshot.state)).length,
      totalDesks: desks.length
    };
  }

  function attributionRows(desks) {
    const raw = desks.map((entity, index) => ({
      id: `D${String(index + 1).padStart(2, "0")}`,
      label: `DESK ${index + 1}`,
      pnl: Number(entity.panelMetrics.netPnl || 0),
      state: entity.snapshot.state
    }));
    const total = raw.reduce((sum, row) => sum + row.pnl, 0);
    return raw.map(row => ({ ...row, sharePct: Math.abs(total) < 1e-9 ? 0 : Number((row.pnl / total * 100).toFixed(2)) }));
  }

  const portfolios = {};
  for (let portfolio = 1; portfolio <= 4; portfolio += 1) {
    const deskEntities = [];
    for (let deskNumber = 1; deskNumber <= 6; deskNumber += 1) {
      const horizonSeries = Object.fromEntries(HORIZONS.map(horizon => [horizon, makeDeskSeries(portfolio, deskNumber, horizon)]));
      const snapshot = deskSnapshot(portfolio, deskNumber, horizonSeries.month);
      deskEntities.push({
        id: `desk${deskNumber}`,
        label: `DESK ${deskNumber}`,
        provenance: "MOCK_SCOPE_SIMULATED",
        snapshot,
        panelMetrics: deskPanelMetrics(portfolio, deskNumber, snapshot, horizonSeries.month),
        horizonSeries
      });
    }

    const layerSeries = Object.fromEntries(HORIZONS.map(horizon => [horizon, aggregateSeries(deskEntities, horizon)]));
    const layerSnapshot = {
      equity: Number(deskEntities.reduce((sum, entity) => sum + entity.snapshot.equity, 0).toFixed(2)),
      currentDrawdownPct: Number(Math.max(...deskEntities.map(entity => entity.snapshot.currentDrawdownPct)).toFixed(2)),
      state: "SIMULATED"
    };
    const layer = {
      id: "layer",
      label: "LAYER",
      provenance: "MOCK_SCOPE_SIMULATED",
      snapshot: layerSnapshot,
      panelMetrics: layerPanelMetrics(deskEntities, layerSeries, layerSnapshot),
      horizonSeries: layerSeries
    };

    portfolios[portfolio] = {
      id: `portfolio${portfolio}`,
      label: portfolioNames[portfolio],
      entities: { layer, ...Object.fromEntries(deskEntities.map(entity => [entity.id, entity])) },
      attribution: { desks: attributionRows(deskEntities) }
    };
  }

  const firmNetPnl = finite((perf.stats || []).find(([label]) => label === "Net P&L")?.[1]) || 0;
  const portfolioWeights = Object.values(portfolios).map(item => Math.max(0.01, Math.abs(Number(item.entities.layer.panelMetrics.netPnl || 0))));
  const portfolioWeightTotal = portfolioWeights.reduce((sum, value) => sum + value, 0) || 1;
  const firmAttribution = Object.values(portfolios).map((item, index) => {
    const pnl = firmNetPnl * portfolioWeights[index] / portfolioWeightTotal;
    return {
      id: `P${index + 1}`,
      label: `PORTFOLIO ${index + 1}`,
      pnl: Number(pnl.toFixed(2)),
      sharePct: Number((pnl / (firmNetPnl || 1) * 100).toFixed(2))
    };
  });

  window.DUSTY_PERFORMANCE_SCOPE_MOCK = Object.freeze({
    contractVersion: "UI_LAB_SCOPE_2",
    asOfUtc: perf.asOfUtc,
    provenance: "MOCK_SCOPE_SIMULATED",
    portfolios,
    firmAttribution: { portfolios: firmAttribution }
  });
})();