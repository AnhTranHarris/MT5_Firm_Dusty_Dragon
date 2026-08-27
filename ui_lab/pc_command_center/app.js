(() => {
  const data = window.DUSTY_MOCK;
  const money = value => value.toLocaleString(undefined, { style: "currency", currency: "USD" });
  const pct = value => `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  const serviceStrip = document.querySelector("#serviceStrip");
  const firmMetrics = document.querySelector("#firmMetrics");
  const incidentList = document.querySelector("#incidentList");
  const timeline = document.querySelector("#timeline");
  const deskNodes = document.querySelector("#deskNodes");
  const deskMatrix = document.querySelector("#deskMatrix");
  const deskDossier = document.querySelector("#deskDossier");
  const focusLabel = document.querySelector("#focusLabel");
  const researchDelta = document.querySelector("#researchDelta");
  const rejectedSummary = document.querySelector("#rejectedSummary");
  const dialog = document.querySelector("#commandDialog");
  const dialogTitle = document.querySelector("#dialogTitle");
  const dialogCopy = document.querySelector("#dialogCopy");
  const confirmCommand = document.querySelector("#confirmCommand");
  const auditTail = document.querySelector("#auditTail");
  const modeButton = document.querySelector("#modeButton");
  let pendingCommand = null;

  function metric(label, value, note = "") {
    return `<div class="metric"><label>${label}</label><strong>${value}</strong><small>${note}</small></div>`;
  }

  function kv(label, value) {
    return `<div class="kv"><span>${label}</span><span>${value}</span></div>`;
  }

  serviceStrip.innerHTML = data.services.map(([name, state]) =>
    `<span class="service-pill"><b>${name}</b> <span class="state-${state}">● ${state}</span></span>`
  ).join("");

  firmMetrics.innerHTML = [
    metric("FIRM EQUITY", money(data.firm.equity), `${money(data.firm.pnl24h)} / 24H`),
    metric("MTD GROWTH", pct(data.firm.pnlMonthPct), `${data.firm.monthlyTargetPct.toFixed(1)}% objective`),
    metric("DRAWDOWN", `${data.firm.drawdownPct.toFixed(2)}%`, "NORMAL"),
    metric("OPEN RISK", `${data.firm.openRiskPct.toFixed(2)}%`, "CAUTION: USD cluster"),
    metric("FREE MARGIN", money(data.firm.freeMargin), "analytical aggregate"),
    metric("EXECUTION", "READY 5/6", "G06 fault-latched")
  ].join("");

  incidentList.innerHTML = data.incidents.map((item, index) => `
    <div class="incident" data-incident="${index}">
      <span class="severity ${item.severity}">${item.severity}</span>
      <b>${item.title}</b><p>${item.detail}</p>
    </div>`).join("");

  timeline.innerHTML = data.overnight.map(([time, event]) =>
    `<div class="timeline-row"><time>${time}</time><span>${event}</span></div>`
  ).join("");

  researchDelta.innerHTML = [
    kv("Jobs completed", data.research.completed),
    kv("Candidates promoted", data.research.promoted),
    kv("Candidates rejected", data.research.rejected),
    kv("Holdout", `${data.research.holdoutPass}/${data.research.holdoutTotal} PASS`),
    kv("Challenge", `Day ${data.research.challengeDay}/${data.research.challengeLength}`)
  ].join("");

  rejectedSummary.innerHTML = [
    kv("Total rejected", data.rejected.total),
    kv("Portfolio capacity", data.rejected.portfolioCapacity),
    kv("Desk risk", data.rejected.deskRisk),
    kv("Correlation", data.rejected.correlation),
    kv("Avoided loss", money(data.rejected.avoidedLoss)),
    kv("Missed profit", money(data.rejected.missedProfit)),
    kv("Governance value", money(data.rejected.avoidedLoss - data.rejected.missedProfit))
  ].join("");

  function stateClass(state) {
    if (state === "CAUTION") return "caution";
    if (state === "FAULT") return "fault";
    return "normal";
  }

  deskNodes.innerHTML = data.desks.map(desk => `
    <button class="desk-node ${stateClass(desk.state)}" data-desk="${desk.id}">
      <span>${desk.id}</span><b>${desk.state}</b>
    </button>`).join("");

  deskMatrix.innerHTML = data.desks.map(desk => `
    <div class="desk-tile" data-desk="${desk.id}">
      <b>${desk.id}</b> <span class="state-${desk.state}">● ${desk.state}</span>
      <small>${desk.state === "FAULT" ? "EXECUTION BLOCKED" : `Equity ${money(desk.equity)}`}</small>
      <div class="numbers"><span>MTD ${pct(desk.mtd)}</span><span>DD ${desk.dd.toFixed(2)}%</span><span>PF ${desk.pf.toFixed(2)}</span><span>Risk ${desk.risk.toFixed(2)}%</span></div>
    </div>`).join("");

  function focusDesk(id) {
    const desk = data.desks.find(item => item.id === id);
    document.querySelectorAll(".desk-node").forEach(node => node.classList.toggle("focused", node.dataset.desk === id));
    if (!desk) {
      focusLabel.textContent = "FIRM SELECTED";
      deskDossier.innerHTML = metric("FIRM", data.firm.state, "Select a desk for exact telemetry");
      return;
    }
    focusLabel.textContent = `${desk.id} / ${desk.state}`;
    deskDossier.innerHTML = [
      metric("EQUITY", money(desk.equity), "independent desk capital"),
      metric("TODAY", pct(desk.today), "realized + floating"),
      metric("MTD", pct(desk.mtd), `PF ${desk.pf.toFixed(2)} · Sharpe ${desk.sharpe.toFixed(2)}`),
      metric("RISK / DD", `${desk.risk.toFixed(2)}% / ${desk.dd.toFixed(2)}%`, desk.state)
    ].join("");
  }

  document.addEventListener("click", event => {
    const deskTarget = event.target.closest("[data-desk]");
    if (deskTarget) focusDesk(deskTarget.dataset.desk);

    const workspaceTarget = event.target.closest("[data-workspace]");
    if (workspaceTarget) {
      document.querySelectorAll("[data-workspace]").forEach(button => button.classList.toggle("active", button === workspaceTarget));
      document.querySelectorAll(".workspace").forEach(section => section.classList.toggle("active", section.id === workspaceTarget.dataset.workspace));
    }

    const commandTarget = event.target.closest("[data-command]");
    if (commandTarget) {
      pendingCommand = commandTarget.dataset.command;
      dialogTitle.textContent = pendingCommand.replaceAll("_", " ");
      dialogCopy.textContent = "This UI laboratory has no Dusty Core connection. Confirming records a local mock audit event only; no broker, MT5 terminal, authorization lease, or execution path is touched.";
      dialog.showModal();
    }
  });

  confirmCommand.addEventListener("click", () => {
    if (!pendingCommand) return;
    const stamp = new Date().toLocaleTimeString();
    auditTail.textContent = `Audit: ${pendingCommand} mock-confirmed at ${stamp}`;
    pendingCommand = null;
  });

  function setMode(mode) {
    const analytical = mode === "analytical";
    document.body.classList.toggle("analytical-mode", analytical);
    document.body.classList.toggle("spatial-mode", !analytical);
    modeButton.textContent = analytical ? "F3 SPATIAL" : "F2 ANALYTICAL";
    auditTail.textContent = `Audit: display mode changed to ${mode.toUpperCase()}`;
  }

  modeButton.addEventListener("click", () => setMode(document.body.classList.contains("analytical-mode") ? "spatial" : "analytical"));
  window.addEventListener("keydown", event => {
    if (event.key === "F2") { event.preventDefault(); setMode("analytical"); }
    if (event.key === "F3") { event.preventDefault(); setMode("spatial"); }
  });

  function updateClock() {
    const time = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date());
    document.querySelector("#clock").textContent = `${time} LOCAL`;
  }
  updateClock();
  window.setInterval(updateClock, 1000);
  focusDesk("G04");
})();