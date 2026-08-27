(() => {
  const data = window.DUSTY_MOCK;
  const brokerProfiles = {
    IC: { broker: "IC Markets", accountType: "MT5 Raw Spread", server: "ICMarketsSC-Demo", environment: "DEMO" },
    FP: { broker: "FP Markets", accountType: "MT5 Standard", server: "FPMarkets-Demo", environment: "DEMO" },
    PEPPER: { broker: "Pepperstone", accountType: "MT5 Razor", server: "Pepperstone-Demo", environment: "DEMO" }
  };

  data.desks.forEach((desk, index) => Object.assign(desk, index % 3 === 0 ? brokerProfiles.IC : index % 3 === 1 ? brokerProfiles.FP : brokerProfiles.PEPPER, {
    accountAlias: `${desk.id}-A${String(index + 1).padStart(2, "0")}`,
    mt5Mode: desk.id === "G06" ? "DEMO / SESSION FAULT" : "DEMO / VERIFIED"
  }));

  const styleNames = ["TREND", "MEAN REVERSION", "BREAKOUT", "SWING", "MOMENTUM", "RANGE"];
  const sectors = ["FX", "METALS", "INDICES", "ENERGY", "FX-B", "METALS-B"];
  const symbols = {
    FX: ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY", "GBPJPY"],
    "FX-B": ["AUDUSD", "NZDUSD", "EURJPY", "USDCHF", "EURGBP", "CADJPY"],
    METALS: ["XAUUSD", "XAGUSD", "XAUEUR", "XAUJPY", "XAGAUD", "XAGJPY"],
    "METALS-B": ["XAUUSD", "XAGUSD", "XAUGBP", "XAUAUD", "XAGGBP", "XAGEUR"],
    INDICES: ["US500", "NAS100", "US30", "GER40", "UK100", "JP225"],
    ENERGY: ["WTI", "BRENT", "NATGAS", "WTI-H1", "BRENT-H4", "NATGAS-D1"]
  };
  const brokers = [brokerProfiles.IC, brokerProfiles.FP, brokerProfiles.PEPPER];

  function mkDesk(id, name, layer, parentId, slot, profile, state = "NORMAL") {
    const base = 4850 + layer * 340 + slot * 73;
    return {
      id, name, layer, parentId, state,
      broker: profile.broker,
      accountType: profile.accountType,
      server: profile.server,
      environment: profile.environment,
      accountAlias: `${id}-A${String(slot).padStart(2, "0")}`,
      equity: base,
      today: ((slot % 5) - 1) * 0.17,
      mtd: 1.7 + (slot % 6) * 0.43,
      dd: 0.7 + (slot % 7) * 0.31,
      pf: 1.22 + (slot % 5) * 0.13,
      sharpe: 0.82 + (slot % 6) * 0.12,
      risk: 0.42 + (slot % 5) * 0.11,
      graduation: layer === 0 ? "DEMO PROOF" : layer === 1 ? "GENERALIST" : layer === 2 ? "STYLE" : layer === 3 ? "SECTOR" : "SYMBOL",
      progress: 52 + (slot * 7) % 47
    };
  }

  const nodes = [];
  for (let i = 0; i < 6; i++) nodes.push(mkDesk(`D0${i + 1}`, `Demo Proof ${i + 1}`, 0, "L0", i + 1, brokers[i % brokers.length], i === 5 ? "FAULT" : "NORMAL"));

  data.desks.forEach((desk, i) => nodes.push({ ...desk, name: `Generalist ${i + 1}`, layer: 1, parentId: "FIRM" }));

  styleNames.forEach((style, i) => nodes.push(mkDesk(`S${String(i + 1).padStart(2, "0")}`, style, 2, "L2", i + 1, brokers[i % brokers.length], i === 4 ? "CAUTION" : "NORMAL")));

  styleNames.forEach((style, styleIndex) => {
    sectors.forEach((sector, sectorIndex) => {
      const sectorId = `L3-${styleIndex + 1}-${sectorIndex + 1}`;
      nodes.push(mkDesk(sectorId, `${style} / ${sector}`, 3, `S${String(styleIndex + 1).padStart(2, "0")}`, sectorIndex + 1, brokers[(styleIndex + sectorIndex) % brokers.length]));
      const symbolList = symbols[sector] || symbols.FX;
      symbolList.forEach((symbol, symbolIndex) => nodes.push(mkDesk(`L4-${styleIndex + 1}-${sectorIndex + 1}-${symbolIndex + 1}`, `${style} / ${sector} / ${symbol}`, 4, sectorId, symbolIndex + 1, brokers[(styleIndex + sectorIndex + symbolIndex) % brokers.length])));
    });
  });

  data.hierarchy = {
    layers: [
      { id: "L0", layer: 0, name: "Layer 0 — Adversarial Demo Laboratory", kind: "layer", childIds: nodes.filter(n => n.layer === 0).map(n => n.id) },
      { id: "L1", layer: 1, name: "Layer 1 — Generalist Live Floor", kind: "layer", childIds: data.desks.map(d => d.id) },
      { id: "L2", layer: 2, name: "Layer 2 — Earned Style Specialists", kind: "layer", childIds: nodes.filter(n => n.layer === 2).map(n => n.id) },
      { id: "L3", layer: 3, name: "Layer 3 — Broker-Aware Sector Specialists", kind: "layer", childIds: nodes.filter(n => n.layer === 3).map(n => n.id) },
      { id: "L4", layer: 4, name: "Layer 4 — Symbol Specialists", kind: "layer", childIds: nodes.filter(n => n.layer === 4).map(n => n.id) }
    ],
    nodes,
    styleNames,
    sectors,
    note: "UI-lab seed only. Layer 2 styles are illustrative earned winners; Layer 3 sector selection is broker-aware and permits differentiated duplicate sectors; Layer 4 symbols are illustrative specializations."
  };
})();
