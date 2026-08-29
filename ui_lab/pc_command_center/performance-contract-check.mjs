import fs from "node:fs";
import vm from "node:vm";

const root = new URL("./", import.meta.url);
const sandbox = { window: {} };
vm.createContext(sandbox);

for (const file of [
  "mock-data.js",
  "performance-mock-history.js",
  "performance-scope-mock-v39.js",
  "performance-quant-scope-mock-v40.js",
]) {
  const source = fs.readFileSync(new URL(file, root), "utf8");
  vm.runInContext(source, sandbox, { filename: file });
}

const data = sandbox.window.DUSTY_MOCK;
if (!data?.performance) throw new Error("performance payload missing");

const performance = data.performance;
const asOfMs = Date.parse(performance.asOfUtc);
if (!Number.isFinite(asOfMs) || !performance.asOfUtc.endsWith("Z")) {
  throw new Error("performance.asOfUtc must be a valid UTC ISO timestamp ending in Z");
}

const requiredHorizons = ["month", "quarter", "year", "fiveYear"];
const requiredMetricKeys = [
  "equity", "freeMargin", "mtdReturnPct", "currentDrawdownPct",
  "maxDrawdownPct", "openRiskPct", "winRatePct", "profitFactor", "sharpe",
  "expectancyR", "grossExposurePct", "netExposurePct", "unresolvedExecutions",
  "activeDesks", "totalDesks"
];
const requiredQuantKeys = [
  "sharpe", "sortino", "recovery", "expectancyR", "profitFactor", "avgWin",
  "avgLoss", "var95Pct", "expectedShortfallPct", "maxPairCorrelation", "trades"
];

function validateSeries(series, label) {
  if (!Array.isArray(series) || series.length < 2) {
    throw new Error(`${label} must contain at least two explicit history points`);
  }
  let previousMs = -Infinity;
  for (const point of series) {
    const pointMs = Date.parse(point.atUtc);
    if (!Number.isFinite(pointMs) || typeof point.atUtc !== "string" || !point.atUtc.endsWith("Z")) {
      throw new Error(`${label} contains a non-UTC timestamp`);
    }
    if (pointMs <= previousMs) throw new Error(`${label} timestamps must be strictly increasing`);
    if (pointMs > asOfMs) throw new Error(`${label} contains future data after asOfUtc`);
    if (!Number.isFinite(Number(point.cumulativeReturnPct))) {
      throw new Error(`${label} contains a non-finite cumulative return`);
    }
    previousMs = pointMs;
  }
  if (Date.parse(series.at(-1).atUtc) !== asOfMs) {
    throw new Error(`${label} must terminate exactly at performance.asOfUtc in the UI lab`);
  }
}

function validatePanelMetrics(metrics, label) {
  if (!metrics || typeof metrics !== "object") throw new Error(`${label} panel metrics missing`);
  for (const key of requiredMetricKeys) {
    if (!Number.isFinite(Number(metrics[key]))) throw new Error(`${label}.${key} must be finite`);
  }
  const equity = Number(metrics.equity);
  if (equity < 0 || Number(metrics.freeMargin) < 0) throw new Error(`${label} capital values cannot be negative`);
  if (metrics.netPnl != null && !Number.isFinite(Number(metrics.netPnl))) throw new Error(`${label}.netPnl must be finite when supplied`);
  if (metrics.netPnl == null && equity !== 0) throw new Error(`${label}.netPnl may be unavailable only for a zero-equity inactive scope`);
  if (Number(metrics.activeDesks) < 0 || Number(metrics.activeDesks) > Number(metrics.totalDesks)) throw new Error(`${label} active desk count invalid`);
}

function validateQuantMetrics(metrics, label) {
  if (!metrics || typeof metrics !== "object") throw new Error(`${label} quant metrics missing`);
  for (const key of requiredQuantKeys) {
    if (!Number.isFinite(Number(metrics[key]))) throw new Error(`${label}.${key} must be finite`);
  }
  for (const key of ["fees", "netPnl", "volatilityTargetPct"]) {
    if (metrics[key] != null && !Number.isFinite(Number(metrics[key]))) throw new Error(`${label}.${key} must be finite when supplied`);
  }
  if (Number(metrics.var95Pct) < 0 || Number(metrics.expectedShortfallPct) < Number(metrics.var95Pct)) {
    throw new Error(`${label} tail metrics are inconsistent`);
  }
  if (Number(metrics.maxPairCorrelation) < -1 || Number(metrics.maxPairCorrelation) > 1) {
    throw new Error(`${label}.maxPairCorrelation must be within [-1,1]`);
  }
  if (!metrics.benchmark || typeof metrics.benchmark.status !== "string") throw new Error(`${label} benchmark state missing`);
}

for (const horizon of requiredHorizons) validateSeries(performance.horizonSeries?.[horizon], `firm.${horizon}`);
const monthReturn = Number(performance.horizonSeries.month.at(-1).cumulativeReturnPct);
if (Math.abs(monthReturn - Number(data.firm.pnlMonthPct)) > 1e-9) throw new Error("monthly history endpoint must reconcile to firm.pnlMonthPct");
if (performance.historyProvenance !== "MOCK_SIMULATED") throw new Error("UI-lab performance history must be explicitly marked MOCK_SIMULATED");

const scopeMock = sandbox.window.DUSTY_PERFORMANCE_SCOPE_MOCK;
if (scopeMock?.contractVersion !== "UI_LAB_SCOPE_2") throw new Error("hierarchical performance scope fixture missing or incompatible");
if (scopeMock.asOfUtc !== performance.asOfUtc) throw new Error("scope fixture as-of timestamp must match firm performance as-of timestamp");

for (let portfolio=1; portfolio<=4; portfolio+=1) {
  const portfolioModel = scopeMock.portfolios?.[portfolio];
  const entities = portfolioModel?.entities;
  if (!entities) throw new Error(`portfolio ${portfolio} entities missing`);
  for (const entityId of ["layer","desk1","desk2","desk3","desk4","desk5","desk6"]) {
    const entity = entities[entityId];
    if (!entity) throw new Error(`portfolio ${portfolio} ${entityId} missing`);
    if (entity.provenance !== "MOCK_SCOPE_SIMULATED") throw new Error(`portfolio ${portfolio} ${entityId} must be marked MOCK_SCOPE_SIMULATED`);
    validatePanelMetrics(entity.panelMetrics, `portfolio${portfolio}.${entityId}`);
    for (const horizon of requiredHorizons) validateSeries(entity.horizonSeries?.[horizon], `portfolio${portfolio}.${entityId}.${horizon}`);
  }
  const deskRows = portfolioModel.attribution?.desks;
  if (!Array.isArray(deskRows) || deskRows.length !== 6) throw new Error(`portfolio ${portfolio} attribution must contain exactly six desks`);
  const shareTotal = deskRows.reduce((sum,row)=>sum+Number(row.sharePct||0),0);
  if (Math.abs(shareTotal-100)>0.2) throw new Error(`portfolio ${portfolio} attribution shares must reconcile to 100%`);
}

const firmRows = scopeMock.firmAttribution?.portfolios;
if (!Array.isArray(firmRows) || firmRows.length !== 4) throw new Error("firm attribution must contain exactly four portfolios");
const firmShareTotal = firmRows.reduce((sum,row)=>sum+Number(row.sharePct||0),0);
if (Math.abs(firmShareTotal-100)>0.2) throw new Error("firm attribution shares must reconcile to 100%");

const quantMock = sandbox.window.DUSTY_QUANT_SCOPE_MOCK;
if (quantMock?.contractVersion !== "UI_LAB_QUANT_SCOPE_1") throw new Error("quant scope fixture missing or incompatible");
if (quantMock.asOfUtc !== performance.asOfUtc) throw new Error("quant scope as-of timestamp must match performance as-of timestamp");
validateQuantMetrics(quantMock.firm,"quant.firm");
for (let portfolio=1; portfolio<=4; portfolio+=1) {
  validateQuantMetrics(quantMock.portfolios?.[portfolio]?.layer,`quant.portfolio${portfolio}.layer`);
  for (let desk=1; desk<=6; desk+=1) validateQuantMetrics(quantMock.portfolios?.[portfolio]?.desks?.[`desk${desk}`],`quant.portfolio${portfolio}.desk${desk}`);
}

console.log("performance + quant contracts OK");
