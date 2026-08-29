import fs from "node:fs";
import vm from "node:vm";

const context={window:{DUSTY_MOCK:{performance:{asOfUtc:"2026-08-29T20:30:00Z"}}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(new URL("./capital-planning-mock-v33.js",import.meta.url),"utf8"),context);
const model=context.window.DUSTY_CAPITAL_PLANNING_MOCK;
if(!model) throw new Error("capital planning mock missing");
if(model.contractVersion!=="UI_LAB_CAPITAL_PLANNING_1") throw new Error("unexpected capital planning contractVersion");
const ladder=[...model.milestonePattern];
if(ladder.length<4) throw new Error("milestone ladder too short");
if(ladder.some((v,i)=>!Number.isFinite(v)||v<=0||(i>0&&v<=ladder[i-1]))) throw new Error("milestone ladder must be finite, positive, strictly increasing");
if(ladder.at(-1)!==50_000_000) throw new Error("firm master goal must terminate ladder at $50M");
const monthly=[...model.monthlyGainGoals];
if(monthly.join(",")!=="5000,10000,15000") throw new Error("monthly realized gain goals must be 5K/10K/15K");
for(const key of ["recognizedRealizedGainUsd","monthRecognizedRealizedGainUsd"]){if(!Number.isFinite(model[key])||model[key]<0)throw new Error(`${key} must be finite and nonnegative`);}
console.log("capital planning contract OK");
