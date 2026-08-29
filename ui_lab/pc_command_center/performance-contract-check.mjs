import fs from "node:fs";
import vm from "node:vm";

const root = new URL("./", import.meta.url);
const sandbox = { window: {} };
vm.createContext(sandbox);

for (const file of ["mock-data.js", "performance-mock-history.js"]) {
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
for (const horizon of requiredHorizons) {
  const series = performance.horizonSeries?.[horizon];
  if (!Array.isArray(series) || series.length < 2) {
    throw new Error(`${horizon} must contain at least two explicit history points`);
  }

  let previousMs = -Infinity;
  for (const point of series) {
    const pointMs = Date.parse(point.atUtc);
    if (!Number.isFinite(pointMs) || typeof point.atUtc !== "string" || !point.atUtc.endsWith("Z")) {
      throw new Error(`${horizon} contains a non-UTC timestamp`);
    }
    if (pointMs <= previousMs) throw new Error(`${horizon} timestamps must be strictly increasing`);
    if (pointMs > asOfMs) throw new Error(`${horizon} contains future data after asOfUtc`);
    if (!Number.isFinite(Number(point.cumulativeReturnPct))) {
      throw new Error(`${horizon} contains a non-finite cumulative return`);
    }
    previousMs = pointMs;
  }

  const last = series.at(-1);
  if (Date.parse(last.atUtc) !== asOfMs) {
    throw new Error(`${horizon} must terminate exactly at performance.asOfUtc in the UI lab`);
  }
}

const monthReturn = Number(performance.horizonSeries.month.at(-1).cumulativeReturnPct);
if (Math.abs(monthReturn - Number(data.firm.pnlMonthPct)) > 1e-9) {
  throw new Error("monthly history endpoint must reconcile to firm.pnlMonthPct");
}

if (performance.historyProvenance !== "MOCK_SIMULATED") {
  throw new Error("UI-lab performance history must be explicitly marked MOCK_SIMULATED");
}

console.log("performance contract OK");
