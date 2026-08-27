window.DUSTY_MOCK = {
  contractVersion: "1",
  generatedAt: "2026-08-27T06:31:42-05:00",
  firm: {
    name: "Dusty Dragon", state: "OPERATIONAL", balance: 27418.22, equity: 27371.11,
    freeMargin: 25182.44, pnl24h: 318.72, pnlWeekPct: 1.84, pnlMonthPct: 3.82,
    monthlyTargetPct: 5.0, drawdownPct: 1.14, openRiskPct: 2.17, unresolvedExecutions: 0
  },
  services: [["CAPITAL","NORMAL"],["EXECUTION","NORMAL"],["RISK","CAUTION"],["DATA","NORMAL"],["RESEARCH","DEGRADED"],["INFRA","NORMAL"]],
  desks: [
    {id:"G01",state:"NORMAL",equity:6172.14,today:.44,mtd:4.32,dd:.86,pf:1.82,sharpe:1.44,risk:.72,graduation:"MULTIDAY",progress:86},
    {id:"G02",state:"NORMAL",equity:5841.33,today:.81,mtd:4.08,dd:1.21,pf:1.71,sharpe:1.36,risk:.88,graduation:"MULTIDAY",progress:79},
    {id:"G03",state:"NORMAL",equity:5104.08,today:.12,mtd:3.31,dd:1.48,pf:1.56,sharpe:1.19,risk:.63,graduation:"HOLD 2D",progress:71},
    {id:"G04",state:"CAUTION",equity:4978.41,today:-.31,mtd:2.12,dd:5.13,pf:1.12,sharpe:.78,risk:1.24,graduation:"MULTIDAY",progress:64},
    {id:"G05",state:"NORMAL",equity:5275.20,today:.21,mtd:3.72,dd:1.09,pf:1.63,sharpe:1.27,risk:.75,graduation:"HOLD 2D",progress:68},
    {id:"G06",state:"FAULT",equity:0,today:0,mtd:0,dd:0,pf:0,sharpe:0,risk:0,graduation:"BLOCKED",progress:42}
  ],
  deskSystems: ["POSITIONS","RISK","RESEARCH","EXECUTION","GRADUATION","KNOWLEDGE"],
  incidents: [
    {severity:"CRITICAL",title:"G06 session fault latched",detail:"Broker connectivity recovered; execution remains blocked until a verified session rebuild."},
    {severity:"RISK",title:"USD concentration elevated",detail:"Four desks currently share meaningful USD downside exposure. Three valid opportunities were rejected."},
    {severity:"WATCH",title:"G04 entered CAUTION",detail:"Rolling drawdown reached 5.13%. Desk remains active under reduced new-risk authority."}
  ],
  overnight: [["00:12","Research batch started"],["00:41","Kronos forecast batch completed"],["01:03","EURUSD candidate rejected — portfolio capacity"],["01:17","G02 entered XAUUSD"],["02:31","G04 drawdown entered CAUTION"],["03:44","G02 XAUUSD closed +1.31R"],["04:58","MT5 G06 disconnect"],["04:59","G06 session fault LATCHED"],["05:01","Broker recovered; execution remained BLOCKED"],["05:37","Holdout batch 14/16 passed"],["06:31","CEO session opened"]],
  ticker: ["Firm equity $27,371.11 · +$318.72 / 24H","G04 CAUTION · rolling DD 5.13%","G06 execution blocked · session rebuild required","USD risk cluster elevated · 3 opportunities rejected","Research: 17 jobs complete · 14/16 holdout PASS","Layer 0 challenge · Day 11 / 30 · verdict TOO EARLY","Generalist expansion: G01 7/7 · G02 7/7 · G03 4/7"],
  research: {completed:17,promoted:3,rejected:8,active:6,challengeDay:11,challengeLength:30,holdoutPass:14,holdoutTotal:16},
  rejected: {total:14,deskRisk:3,portfolioCapacity:4,correlation:2,evidence:2,executionUnsafe:1,cost:2,avoidedLoss:183,missedProfit:91},
  positions: [
    {desk:"G01",symbol:"EURUSD",side:"LONG",entry:1.16842,mark:1.16918,pnl:42.60,r:.48,risk:.36,age:"2h 14m",state:"VALID"},
    {desk:"G02",symbol:"XAUUSD",side:"LONG",entry:3421.6,mark:3435.8,pnl:91.20,r:1.12,risk:.41,age:"4h 02m",state:"VALID"},
    {desk:"G03",symbol:"GBPJPY",side:"SHORT",entry:201.82,mark:201.61,pnl:27.40,r:.31,risk:.29,age:"1h 26m",state:"VALID"},
    {desk:"G04",symbol:"US500",side:"LONG",entry:6478.2,mark:6469.7,pnl:-38.10,r:-.44,risk:.18,age:"48m",state:"CAUTION"}
  ],
  watchlist: [
    {symbol:"EURUSD",price:"1.16918",move:.34,spread:"0.7",regime:"TREND"},{symbol:"GBPUSD",price:"1.35241",move:-.18,spread:"0.9",regime:"RANGE"},{symbol:"USDJPY",price:"147.62",move:.26,spread:"0.8",regime:"TREND"},{symbol:"XAUUSD",price:"3435.80",move:1.14,spread:"18",regime:"MOMENTUM"},{symbol:"US500",price:"6469.7",move:-.43,spread:"0.6",regime:"RISK-OFF"},{symbol:"BTCUSD",price:"118420",move:2.08,spread:"34",regime:"BREAKOUT"}
  ],
  decisions: [
    {time:"06:17",symbol:"EURUSD",desk:"G01",result:"APPROVED",score:82,reason:"Trend + momentum aligned; portfolio capacity available."},
    {time:"06:08",symbol:"XAUUSD",desk:"G02",result:"APPROVED",score:88,reason:"Breakout continuation; cost and risk gates passed."},
    {time:"05:56",symbol:"AUDUSD",desk:"G05",result:"REJECTED",score:79,reason:"Portfolio USD concentration gate."},
    {time:"05:41",symbol:"GBPJPY",desk:"G03",result:"APPROVED",score:76,reason:"Mean-reversion evidence passed; low correlation contribution."}
  ],
  riskHeatmap: [
    {symbol:"USD",label:"USD FACTOR",value:-1.8,risk:23,size:22},{symbol:"XAU",label:"GOLD",value:2.7,risk:16,size:17},{symbol:"EUR",label:"EUR",value:1.1,risk:12,size:14},{symbol:"JPY",label:"JPY",value:-.9,risk:10,size:12},{symbol:"GBP",label:"GBP",value:.6,risk:9,size:11},{symbol:"US500",label:"US INDEX",value:-2.1,risk:15,size:16},{symbol:"BTC",label:"CRYPTO",value:3.2,risk:8,size:10},{symbol:"AUD",label:"AUD",value:-.4,risk:6,size:8},{symbol:"OIL",label:"ENERGY",value:1.6,risk:5,size:8},{symbol:"CHF",label:"CHF",value:.2,risk:4,size:7},{symbol:"CAD",label:"CAD",value:-.2,risk:4,size:7},{symbol:"NZD",label:"NZD",value:.8,risk:3,size:6}
  ],
  riskStats: {grossExposure:18.4,netExposure:7.9,portfolioOpenRisk:2.17,usdContribution:23,maxPairCorrelation:.81,simultaneousLossFreq:12.4,expectedShortfall:1.72,var95:1.21},
  performance: {
    stats:[ ["Net P&L","+$3,297.04"],["Trades","138"],["Win rate","61.6%"],["Profit Factor","1.71"],["Expectancy","+0.27R"],["Sharpe","1.36"],["Sortino","1.88"],["Recovery Factor","3.42"],["Max DD","5.13%"],["Avg Win","+$68.24"],["Avg Loss","-$39.71"],["Fees / swap","-$126.88"] ],
    returns:[1.2,1.8,1.4,2.6,2.1,3.0,2.7,3.5,3.1,3.82],
    deskAttribution:[{id:"G01",pnl:921,pct:28},{id:"G02",pnl:842,pct:26},{id:"G03",pnl:603,pct:18},{id:"G04",pnl:211,pct:6},{id:"G05",pnl:720,pct:22}]
  },
  researchQueue: [
    {id:"R-1842",title:"XAU H1 breakout persistence",stage:"HOLDOUT",progress:82,impact:"HIGH"},{id:"R-1847",title:"EURUSD low-vol trend filter",stage:"WALK-FORWARD",progress:64,impact:"MED"},{id:"R-1851",title:"GBPJPY adverse-excursion model",stage:"BACKTEST",progress:41,impact:"HIGH"},{id:"R-1854",title:"US500 opening-range regime",stage:"RESEARCH",progress:27,impact:"MED"},{id:"R-1858",title:"Kronos H4 horizon calibration",stage:"PEER TEST",progress:73,impact:"HIGH"}
  ],
  evidence: [
    {claim:"XAU breakout continuation improves above volatility percentile 68",state:"VALIDATED",confidence:87,age:"4d"},
    {claim:"EURUSD H1 Kronos horizon adds value in low-vol trend",state:"PEER_TESTING",confidence:72,age:"1d"},
    {claim:"US500 first-hour reversal filter",state:"REJECTED",confidence:31,age:"2d"},
    {claim:"GBPJPY stop-distance regime adjustment",state:"OBSERVED",confidence:66,age:"6h"}
  ],
  challenge: {target:"LAYER 1 / GENERALIST",day:11,length:30,incumbent:{ret:3.82,dd:1.14,pf:1.71,sharpe:1.36},challenger:{ret:4.11,dd:1.08,pf:1.76,sharpe:1.42},verdict:"TOO EARLY"},
  systems: [
    {name:"Dusty Core",state:"HEALTHY",latency:"4 ms",cpu:11,ram:420},{name:"MT5 G01",state:"HEALTHY",latency:"31 ms",cpu:7,ram:188},{name:"MT5 G02",state:"HEALTHY",latency:"29 ms",cpu:6,ram:181},{name:"MT5 G03",state:"HEALTHY",latency:"33 ms",cpu:6,ram:179},{name:"MT5 G04",state:"HEALTHY",latency:"28 ms",cpu:8,ram:193},{name:"MT5 G05",state:"HEALTHY",latency:"35 ms",cpu:6,ram:184},{name:"MT5 G06",state:"FAULT-LATCHED",latency:"—",cpu:1,ram:102},{name:"Research Worker",state:"DEGRADED",latency:"queue 6",cpu:44,ram:1820},{name:"SQLite Ledger",state:"HEALTHY",latency:"2 ms",cpu:1,ram:42},{name:"Market Archive",state:"HEALTHY",latency:"11 ms",cpu:3,ram:318}
  ],
  audit: [["06:31:42","CEO_SESSION_OPEN","INFO"],["05:37:19","HOLDOUT_BATCH_COMPLETE","INFO"],["05:01:04","G06_EXECUTION_BLOCKED","CRITICAL"],["04:59:41","SESSION_FAULT_LATCHED","CRITICAL"],["03:44:11","POSITION_CLOSED_G02_XAUUSD","INFO"],["02:31:07","DESK_G04_CAUTION","RISK"]]
};