import fs from "node:fs";
import vm from "node:vm";

const root = new URL("./", import.meta.url);
const sandbox = { window: {} };
vm.createContext(sandbox);

for (const file of [
  "mock-data.js",
  "performance-mock-history.js",
  "performance-scope-mock-v38.js",
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

for (const horizon of requiredHorizons) {
  validateSeries(performance.horizonSeries?.[horizon], `firm.${horizon}`);
}

const monthReturn = Number(performance.horizonSeries.month.at(-1).cumulativeReturnPct);
if (Math.abs(monthReturn - Number(data.firm.pnlMonthPct)) > 1e-9) {
  throw new Error("monthly history endpoint must reconcile to firm.pnlMonthPct");
}
if (performance.historyProvenance !== "MOCK_SIMULATED") {
  throw new Error("UI-lab performance history must be explicitly marked MOCK_SIMULATED");
}

const scopeMock = sandbox.window.DUSTY_PERFORMANCE_SCOPE_MOCK;
if (scopeMock?.contractVersion !== "UI_LAB_SCOPE_1") {
  throw new Error("hierarchical performance scope fixture missing or incompatible");
}
if (scopeMock.asOfUtc !== performance.asOfUtc) {
  throw new Error("scope fixture as-of timestamp must match firm performance as-of timestamp");
}
for (let portfolio = 1; portfolio <= 4; portfolio += 1) {
  const entities = scopeMock.portfolios?.[portfolio]?.entities;
  if (!entities) throw new Error(`portfolio ${portfolio} entities missing`);
  for (const entityId of ["layer", "desk1", "desk2", "desk3", "desk4", "desk5", "desk6"]) {
    const entity = entities[entityId];
    if (!entity) throw new Error(`portfolio ${portfolio} ${entityId} missing`);
    if (entity.provenance !== "MOCK_SCOPE_SIMULATED") {
      throw new Error(`portfolio ${portfolio} ${entityId} must be marked MOCK_SCOPE_SIMULATED`);
    }
    if (!Number.isFinite(Number(entity.snapshot?.equity)) || Number(entity.snapshot.equity) < 0) {
      throw new Error(`portfolio ${portfolio} ${entityId} equity snapshot invalid`);
    }
    for (const horizon of requiredHorizons) {
      validateSeries(entity.horizonSeries?.[horizon], `portfolio${portfolio}.${entityId}.${horizon}`);
    }
  }
}

console.log("performance contract OK");
