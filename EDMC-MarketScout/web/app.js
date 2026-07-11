let rows = [];
let selectedIndex = -1;
let lastVersion = null;
let currentView = "stations";
let displayColumns = [];
let watchedCommodities = ["Palladium", "Gold", "Silver"];
let allCommodities = [];

function $(id) { return document.getElementById(id); }
function fmt(v) { return v === null || v === undefined || v === "" ? "—" : String(v); }
function num(v) { const n = Number(v); return Number.isFinite(n) ? n : null; }
function money(v) { const n = num(v); return n === null ? "—" : Math.round(n).toLocaleString(); }
function shortTime(v) { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleTimeString(); }
function localDateTime(v) { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString(); }
function q(params) { return new URLSearchParams(params).toString(); }
function safeId(s) { return String(s).replace(/[^A-Za-z0-9_-]/g, "_"); }
function escapeHtml(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c])); }

function stationParams() {
  return {
    system: $("systemFilter").value,
    station: $("stationFilter").value,
    economy: $("economyFilter").value,
    state: $("stateFilter").value,
    source: $("sourceFilter").value,
    include_fc: $("includeFc").checked ? "1" : "0",
    limit: $("limitRows").value || "1000"
  };
}

function rowFlag(row) {
  const priceThreshold = Number($("priceThreshold").value || 6000);
  const supplyThreshold = Number($("supplyThreshold").value || 10000);
  const cheap = [];
  const strong = [];
  for (const m of watchedCommodities) {
    const buy = num(row[`${m}_buy`]);
    const supply = num(row[`${m}_supply`]);
    if (buy !== null && buy > 0 && buy <= priceThreshold) {
      cheap.push(m);
      if (supply !== null && supply >= supplyThreshold) strong.push(m);
    }
  }
  if (strong.length) return { cls: "strong", text: "★★ " + strong.slice(0, 3).join(", ") };
  if (cheap.length) return { cls: "cheap", text: "★ " + cheap.slice(0, 3).join(", ") };
  return { cls: "", text: "" };
}

function commodityCell(row, commodity, side) {
  const price = money(row[`${commodity}_${side}`]);
  const qtyName = side === "buy" ? "supply" : "demand";
  const qty = money(row[`${commodity}_${qtyName}`]);
  return `<div class="price"><div class="cellMain">${price}</div><div class="cellSub">${qtyName}: ${qty}</div></div>`;
}

function bestBuyCell(row) {
  if (!row.best_buy_commodity) return "—";
  return `<div class="price"><div class="cellMain">${escapeHtml(row.best_buy_commodity)} @ ${money(row.best_buy_price)}</div><div class="cellSub">supply: ${money(row.best_buy_supply)} · score: ${money(row.best_buy_score)}</div></div>`;
}


function stationDedupeKey(row) {
  const system = String(row.system || "").trim().toLowerCase();
  const station = String(row.station || "").trim().toLowerCase();
  return `${system}|${station}`;
}

function rowDateScore(v) {
  if (!v) return 0;
  const t = new Date(v).getTime();
  return Number.isFinite(t) ? t : 0;
}

function rowQualityScore(row) {
  let score = 0;
  if (row.station_visit) score += 1_000_000_000_000_000;
  score += rowDateScore(row.market_updated);
  score += Math.max(0, Number(row.best_buy_score || 0));
  if (row.source === "local_visit") score += 1_000_000;
  return score;
}

function dedupeStationRows(inputRows) {
  const byKey = new Map();
  for (const row of inputRows || []) {
    const key = stationDedupeKey(row);
    if (!key || key === "|") continue;
    const current = byKey.get(key);
    if (!current || rowQualityScore(row) > rowQualityScore(current)) {
      byKey.set(key, row);
    }
  }
  return Array.from(byKey.values());
}

function renderTable() {
  const tbody = $("stationTable").querySelector("tbody");
  tbody.innerHTML = "";
  rows.forEach((row, idx) => {
    const flag = rowFlag(row);
    const tr = document.createElement("tr");
    if (flag.cls) tr.classList.add(flag.cls);
    if (idx === selectedIndex) tr.classList.add("selected");
    const commodityTds = displayColumns.map(col => `<td>${commodityCell(row, col.commodity, col.side)}</td>`).join("");
    tr.innerHTML = `
      <td class="flag">${escapeHtml(flag.text)}</td>
      <td><div class="systemName">${escapeHtml(fmt(row.system))}</div><div class="stationName">${escapeHtml(fmt(row.station))} <span class="stationMeta">| Pad ${escapeHtml(fmt(row.pad))}</span></div></td>
      <td><div class="cellMain">${escapeHtml(fmt(row.state))}</div><div class="cellSub">${escapeHtml(fmt(row.economies))}</div></td>
      <td>${bestBuyCell(row)}</td>
      ${commodityTds}
      <td><div>${escapeHtml(localDateTime(row.market_updated))}</div><div class="cellSub">Visit: ${escapeHtml(localDateTime(row.station_visit))}</div></td>
    `;
    tr.addEventListener("click", () => { selectedIndex = idx; renderTable(); renderDetails(row); });
    tbody.appendChild(tr);
  });
  $("statusText").textContent = `${rows.length} rows · ${new Date().toLocaleTimeString()}`;
  if (selectedIndex >= rows.length) selectedIndex = -1;
}

function renderDetails(row) {
  const pane = $("detailsPane");
  const metadata = [
    ["System", row.system], ["Station", row.station], ["Pad", row.pad], ["Type", row.type],
    ["State", row.state], ["Economies", row.economies], ["System Economy", row.system_economy],
    ["Security", row.security], ["Population", money(row.population)], ["Arrival LS", money(row.arrival_ls)],
    ["Fleet Carrier", row.fleet_carrier || "No"], ["Planetary", row.planetary || "No"],
    ["Source", row.source], ["Source Pulled", localDateTime(row.source_pulled)], ["Source Updated", localDateTime(row.source_updated)],
    ["Market Updated", localDateTime(row.market_updated)], ["Station Visit", localDateTime(row.station_visit)],
    ["Best Buy", row.best_buy_commodity ? `${row.best_buy_commodity} @ ${money(row.best_buy_price)} / supply ${money(row.best_buy_supply)} / score ${money(row.best_buy_score)}` : "—"]
  ];
  let html = `<h2>${escapeHtml(fmt(row.system))}</h2><p class="subtitle">${escapeHtml(fmt(row.station))} | Pad ${escapeHtml(fmt(row.pad))}</p>`;
  html += `<dl class="detailGrid">` + metadata.map(([k,v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(fmt(v))}</dd>`).join("") + `</dl>`;
  const detailsCommodities = Array.from(new Set([...watchedCommodities, ...displayColumns.map(c => c.commodity)]));
  for (const m of detailsCommodities) {
    html += `<div class="metalBlock"><h3>${escapeHtml(m)}</h3><dl class="detailGrid">
      <dt>Buy</dt><dd>${money(row[`${m}_buy`])}</dd>
      <dt>Supply</dt><dd>${money(row[`${m}_supply`])}</dd>
      <dt>Sell</dt><dd>${money(row[`${m}_sell`])}</dd>
      <dt>Demand</dt><dd>${money(row[`${m}_demand`])}</dd>
    </dl></div>`;
  }
  pane.innerHTML = html;
}

async function loadStations() {
  currentView = "stations";
  const res = await fetch(`/api/stations?${q(stationParams())}`, { cache: "no-store" });
  const data = await res.json();
  rows = dedupeStationRows(data.rows || []);
  displayColumns = data.display_columns || [];
  watchedCommodities = data.watched_commodities || watchedCommodities;
  selectedIndex = -1;
  resetStationHeaders();
  renderTable();
  $("detailsPane").innerHTML = "<h2>Details</h2><p>Select a row.</p>";
}

function resetStationHeaders() {
  const cols = displayColumns.map(col => `<th>${escapeHtml(col.commodity)} ${col.side === "buy" ? "Buy" : "Sell"}</th>`).join("");
  $("stationTable").querySelector("thead").innerHTML = `<tr>
    <th>Flag</th><th>System / Station</th><th>State / Economy</th><th>Best Buy</th>${cols}<th>Updated</th>
  </tr>`;
}

async function loadJackpots() {
  currentView = "jackpots";
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent($("limitRows").value || "500")}`, { cache: "no-store" });
  const data = await res.json();
  rows = data.rows || [];
  selectedIndex = -1;
  renderJackpotTable();
  $("detailsPane").innerHTML = "<h2>Jackpot History</h2><p>Select a sample.</p>";
}

function histMetalCell(row, metal) {
  return `<div class="price"><div class="cellMain">${money(row[`${metal}_buy`])}</div><div class="cellSub">supply: ${money(row[`${metal}_supply`])}</div></div>`;
}
function renderJackpotTable() {
  const table = $("stationTable");
  table.querySelector("thead").innerHTML = `<tr><th>Status</th><th>System / Station</th><th>Context</th><th>Palladium</th><th>Gold</th><th>Silver</th><th>Sample Time</th><th>Detected</th></tr>`;
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = "";
  rows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    if (row.is_jackpot) tr.classList.add("strong");
    if (idx === selectedIndex) tr.classList.add("selected");
    tr.innerHTML = `<td>${row.is_jackpot ? "Active sample" : "Ended sample"}</td>
      <td><div class="systemName">${escapeHtml(fmt(row.system_name))}</div><div class="stationName">${escapeHtml(fmt(row.station_name))} <span class="stationMeta">| Pad ${escapeHtml(fmt(row.largest_pad))}</span></div></td>
      <td><div class="cellMain">${escapeHtml(fmt(row.station_faction_state))}</div><div class="cellSub">${escapeHtml(fmt(row.station_economies_json))}</div></td>
      <td>${histMetalCell(row, "palladium")}</td><td>${histMetalCell(row, "gold")}</td><td>${histMetalCell(row, "silver")}</td>
      <td>${escapeHtml(localDateTime(row.sample_datetime))}</td><td>${escapeHtml(localDateTime(row.detected_datetime))}</td>`;
    tr.addEventListener("click", () => { selectedIndex = idx; renderJackpotTable(); renderJackpotDetails(row); });
    tbody.appendChild(tr);
  });
  $("statusText").textContent = `${rows.length} jackpot samples · ${new Date().toLocaleTimeString()}`;
}
function renderJackpotDetails(row) { $("detailsPane").innerHTML = `<h2>Jackpot ${escapeHtml(fmt(row.jackpot_id))}</h2><pre>${escapeHtml(JSON.stringify(row, null, 2))}</pre>`; }

async function loadLedger() {
  currentView = "ledger";
  const params = {
    commodity: $("ledgerCommodity").value || "",
    event_type: $("ledgerType").value || "Any",
    limit: $("limitRows").value || "1000"
  };
  const res = await fetch(`/api/ledger?${q(params)}`, { cache: "no-store" });
  const data = await res.json();
  rows = data.rows || [];
  selectedIndex = -1;
  renderLedgerTable();
  $("detailsPane").innerHTML = "<h2>Ledger</h2><p>Select a trade.</p>";
}
function renderLedgerTable() {
  const showLifo = $("showLifo").checked;
  $("stationTable").querySelector("thead").innerHTML = `<tr><th>Time</th><th>Type</th><th>System / Station</th><th>Commodity</th><th>Qty</th><th>Unit</th><th>Total</th><th>Avg Paid</th><th>Profit</th><th>Cr/hr</th>${showLifo ? "<th>LIFO avg</th><th>LIFO profit</th>" : ""}</tr>`;
  const tbody = $("stationTable").querySelector("tbody");
  tbody.innerHTML = "";
  rows.forEach((row, idx) => {
    const tr = document.createElement("tr");
    if (idx === selectedIndex) tr.classList.add("selected");
    const tradeType = String(row.event_type || "").toLowerCase();
    if (tradeType === "buy") tr.classList.add("ledgerBuy");
    if (tradeType === "sell") tr.classList.add("ledgerSell");
    if (tradeType === "sell" && num(row.journal_profit) > 0) tr.classList.add("cheap");
    const typeLabel = tradeType === "buy" ? "BUY" : tradeType === "sell" ? "SELL" : fmt(row.event_type);
    const profitClass = num(row.journal_profit) > 0 ? "profit positive" : num(row.journal_profit) < 0 ? "profit negative" : "profit";
    const sideQtyLabel = tradeType === "buy" ? "Supply" : tradeType === "sell" ? "Demand" : "Market";
    const sideQtyValue = tradeType === "buy" ? row.supply_at_trade : tradeType === "sell" ? row.demand_at_trade : null;
    const sideQty = sideQtyValue == null ? "" : `<div class="cellSub">${escapeHtml(sideQtyLabel)}: ${escapeHtml(money(sideQtyValue))}</div>`;
    tr.innerHTML = `<td>${escapeHtml(shortTime(row.event_datetime))}</td><td><span class="tradeType ${escapeHtml(tradeType)}">${escapeHtml(typeLabel)}</span></td>
      <td><div class="cellMain">${escapeHtml(fmt(row.system_name))}</div><div class="cellSub">${escapeHtml(fmt(row.station_name))}</div></td>
      <td><div class="cellMain">${escapeHtml(fmt(row.commodity))}</div>${sideQty}</td><td class="num">${money(row.quantity)}</td><td class="num">${money(row.unit_price)}</td><td class="num">${money(row.total_credits)}</td>
      <td class="num">${money(row.journal_avg_price_paid)}</td><td class="num"><span class="${profitClass}">${money(row.journal_profit)}</span></td><td class="num">${money(row.profit_per_hour ?? row.credits_per_hour)}</td>
      ${showLifo ? `<td class="num">${money(row.ledger_avg_buy_price)}</td><td class="num">${money(row.ledger_profit)}</td>` : ""}`;
    tr.addEventListener("click", () => { selectedIndex = idx; renderLedgerTable(); renderLedgerDetails(row); });
    tbody.appendChild(tr);
  });
  $("statusText").textContent = `${rows.length} trades · ${new Date().toLocaleTimeString()}`;
}
function renderLedgerDetails(row) { $("detailsPane").innerHTML = `<h2>${escapeHtml(fmt(row.event_type)).toUpperCase()} ${escapeHtml(fmt(row.commodity))}</h2><pre>${escapeHtml(JSON.stringify(row, null, 2))}</pre>`; }

async function loadCommoditySettings() {
  const [settingsRes, commoditiesRes] = await Promise.all([
    fetch("/api/settings", { cache: "no-store" }),
    fetch("/api/commodities", { cache: "no-store" })
  ]);
  const settings = await settingsRes.json();
  const data = await commoditiesRes.json();
  watchedCommodities = settings.watched_commodities || ["Palladium", "Gold", "Silver"];
  displayColumns = settings.watched_columns || watchedCommodities.map(c => ({commodity: c, side: "buy"}));
  allCommodities = Array.from(new Set([...(data.commodities || []), ...watchedCommodities])).sort();
  renderCommoditySettings();
}

function renderCommoditySettings() {
  const box = $("commoditySettings");
  const filter = ($("commoditySearch").value || "").toLowerCase();
  const shown = allCommodities.filter(c => !filter || c.toLowerCase().includes(filter)).slice(0, 250);
  const colKey = (c, side) => `${c}::${side}`;
  const selectedCols = new Set(displayColumns.map(c => colKey(c.commodity, c.side)));
  box.innerHTML = shown.map(c => {
    const watched = watchedCommodities.includes(c);
    return `<div class="commodityRow">
      <label><input type="checkbox" class="watchCommodity" data-commodity="${escapeHtml(c)}" ${watched ? "checked" : ""}/> ${escapeHtml(c)}</label>
      <label><input type="checkbox" class="showCommodityCol" data-commodity="${escapeHtml(c)}" data-side="buy" ${selectedCols.has(colKey(c, "buy")) ? "checked" : ""}/> Buy col</label>
      <label><input type="checkbox" class="showCommodityCol" data-commodity="${escapeHtml(c)}" data-side="sell" ${selectedCols.has(colKey(c, "sell")) ? "checked" : ""}/> Sell col</label>
    </div>`;
  }).join("");
}

async function saveCommoditySettings() {
  const watched = Array.from(document.querySelectorAll(".watchCommodity:checked")).map(x => x.dataset.commodity);
  const cols = Array.from(document.querySelectorAll(".showCommodityCol:checked")).map(x => ({commodity: x.dataset.commodity, side: x.dataset.side}));
  await fetch("/api/settings", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({watched_commodities: watched, watched_columns: cols}) });
  $("settingsPanel").classList.add("hidden");
  await loadStations();
}

async function pollStatus() {
  if (!$("autoRefresh").checked) return;
  const res = await fetch("/api/status", { cache: "no-store" });
  const data = await res.json();
  if (lastVersion !== null && data.data_version !== lastVersion) {
    if (currentView === "stations") loadStations();
    else if (currentView === "jackpots") loadJackpots();
    else if (currentView === "ledger") loadLedger();
  }
  lastVersion = data.data_version;
}

function wireEvents() {
  $("applyBtn").addEventListener("click", () => currentView === "ledger" ? loadLedger() : currentView === "jackpots" ? loadJackpots() : loadStations());
  $("stationsBtn").addEventListener("click", loadStations);
  $("historyBtn").addEventListener("click", loadJackpots);
  $("ledgerBtn").addEventListener("click", loadLedger);
  $("settingsBtn").addEventListener("click", async () => { $("settingsPanel").classList.toggle("hidden"); await loadCommoditySettings(); });
  $("commoditySearch").addEventListener("input", renderCommoditySettings);
  $("saveSettingsBtn").addEventListener("click", saveCommoditySettings);
  $("closeSettingsBtn").addEventListener("click", () => $("settingsPanel").classList.add("hidden"));
}

wireEvents();
loadCommoditySettings().then(loadStations);
setInterval(pollStatus, 2000);
