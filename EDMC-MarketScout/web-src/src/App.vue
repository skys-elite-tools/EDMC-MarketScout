<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
const lastVersion = ref(null)
const currentView = ref('stations')
const displayColumns = ref([])
const watchedCommodities = ref(['Palladium', 'Gold', 'Silver'])
const allCommodities = ref([])
const settingsVisible = ref(false)
const commoditySearch = ref('')
const statusText = ref('Loading…')
const autoRefresh = ref(true)

const filters = ref({
  system: '',
  station: '',
  economy: 'Extraction, Refinery',
  state: '',
  source: 'Any',
  includeFc: false,
  priceThreshold: 6000,
  supplyThreshold: 10000,
  limit: 1000,
})

const ledgerFilters = ref({
  commodity: '',
  eventType: 'Any',
  showLifo: false,
})

function fmt(v) { return v === null || v === undefined || v === '' ? '—' : String(v) }
function num(v) { const n = Number(v); return Number.isFinite(n) ? n : null }
function money(v) { const n = num(v); return n === null ? '—' : Math.round(n).toLocaleString() }
function shortTime(v) { if (!v) return '—'; const d = new Date(v); return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleTimeString() }
function localDateTime(v) { if (!v) return '—'; const d = new Date(v); return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString() }
function query(params) { return new URLSearchParams(params).toString() }
function stationParams() {
  return {
    system: filters.value.system,
    station: filters.value.station,
    economy: filters.value.economy,
    state: filters.value.state,
    source: filters.value.source,
    include_fc: filters.value.includeFc ? '1' : '0',
    limit: filters.value.limit || '1000',
  }
}

function rowFlag(row) {
  const priceThreshold = Number(filters.value.priceThreshold || 6000)
  const supplyThreshold = Number(filters.value.supplyThreshold || 10000)
  const cheap = []
  const strong = []
  for (const commodity of watchedCommodities.value) {
    const buy = num(row[`${commodity}_buy`])
    const supply = num(row[`${commodity}_supply`])
    if (buy !== null && buy > 0 && buy <= priceThreshold) {
      cheap.push(commodity)
      if (supply !== null && supply >= supplyThreshold) strong.push(commodity)
    }
  }
  if (strong.length) return { cls: 'strong', text: `★★ ${strong.slice(0, 3).join(', ')}` }
  if (cheap.length) return { cls: 'cheap', text: `★ ${cheap.slice(0, 3).join(', ')}` }
  return { cls: '', text: '' }
}

function stationDedupeKey(row) {
  const system = String(row.system || '').trim().toLowerCase()
  const station = String(row.station || '').trim().toLowerCase()
  return `${system}|${station}`
}

function rowDateScore(v) {
  if (!v) return 0
  const t = new Date(v).getTime()
  return Number.isFinite(t) ? t : 0
}

function rowQualityScore(row) {
  let score = 0
  if (row.station_visit) score += 1_000_000_000_000_000
  score += rowDateScore(row.market_updated)
  score += Math.max(0, Number(row.best_buy_score || 0))
  if (row.source === 'local_visit') score += 1_000_000
  return score
}

function dedupeStationRows(inputRows) {
  const byKey = new Map()
  for (const row of inputRows || []) {
    const key = stationDedupeKey(row)
    if (!key || key === '|') continue
    const current = byKey.get(key)
    if (!current || rowQualityScore(row) > rowQualityScore(current)) {
      byKey.set(key, row)
    }
  }
  return Array.from(byKey.values())
}

function commodityCellParts(row, commodity, side) {
  const qtyName = side === 'buy' ? 'supply' : 'demand'
  return {
    price: money(row[`${commodity}_${side}`]),
    qtyName,
    qty: money(row[`${commodity}_${qtyName}`]),
  }
}

function setSelected(idx) {
  selectedIndex.value = idx
}

async function loadStations() {
  currentView.value = 'stations'
  const res = await fetch(`/api/stations?${query(stationParams())}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = dedupeStationRows(data.rows || [])
  displayColumns.value = data.display_columns || []
  watchedCommodities.value = data.watched_commodities || watchedCommodities.value
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} rows · ${new Date().toLocaleTimeString()}`
}

async function loadJackpots() {
  currentView.value = 'jackpots'
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(filters.value.limit || '500')}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = data.rows || []
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

async function loadLedger() {
  currentView.value = 'ledger'
  const params = {
    commodity: ledgerFilters.value.commodity || '',
    event_type: ledgerFilters.value.eventType || 'Any',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/ledger?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = data.rows || []
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} trades · ${new Date().toLocaleTimeString()}`
}

function applyCurrentView() {
  if (currentView.value === 'ledger') return loadLedger()
  if (currentView.value === 'jackpots') return loadJackpots()
  return loadStations()
}

async function loadCommoditySettings() {
  const [settingsRes, commoditiesRes] = await Promise.all([
    fetch('/api/settings', { cache: 'no-store' }),
    fetch('/api/commodities', { cache: 'no-store' }),
  ])
  const settings = await settingsRes.json()
  const data = await commoditiesRes.json()
  watchedCommodities.value = settings.watched_commodities || ['Palladium', 'Gold', 'Silver']
  displayColumns.value = settings.watched_columns || watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  allCommodities.value = Array.from(new Set([...(data.commodities || []), ...watchedCommodities.value])).sort()
}

const filteredCommodities = computed(() => {
  const filter = (commoditySearch.value || '').toLowerCase()
  return allCommodities.value.filter(c => !filter || c.toLowerCase().includes(filter)).slice(0, 250)
})

function columnKey(col) { return `${col.commodity}::${col.side}` }
function isColumnSelected(commodity, side) {
  return displayColumns.value.some(c => c.commodity === commodity && c.side === side)
}
function setWatchedCommodity(commodity, checked) {
  const set = new Set(watchedCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  watchedCommodities.value = Array.from(set)
}
function setDisplayColumn(commodity, side, checked) {
  const key = `${commodity}::${side}`
  const map = new Map(displayColumns.value.map(c => [columnKey(c), c]))
  if (checked) map.set(key, { commodity, side })
  else map.delete(key)
  displayColumns.value = Array.from(map.values())
}

async function saveCommoditySettings() {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      watched_commodities: watchedCommodities.value,
      watched_columns: displayColumns.value,
    }),
  })
  settingsVisible.value = false
  await loadStations()
}

async function openCommoditySettings() {
  settingsVisible.value = !settingsVisible.value
  if (settingsVisible.value) await loadCommoditySettings()
}

async function pollStatus() {
  if (!autoRefresh.value) return
  const res = await fetch('/api/status', { cache: 'no-store' })
  const data = await res.json()
  if (lastVersion.value !== null && data.data_version !== lastVersion.value) {
    await applyCurrentView()
  }
  lastVersion.value = data.data_version
}

let pollTimer = null
onMounted(async () => {
  await loadCommoditySettings()
  await loadStations()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <header>
    <div>
      <h1>EDMC-MarketScout</h1>
      <p class="subtitle">Local-only scouting database. No uploads, no external scripts.</p>
    </div>
    <div class="status">
      <span>{{ statusText }}</span>
      <label><input type="checkbox" v-model="autoRefresh" /> Auto-refresh</label>
    </div>
  </header>

  <section class="filters">
    <label>System <input v-model="filters.system" type="text" /></label>
    <label>Station <input v-model="filters.station" type="text" /></label>
    <label>Economy <input v-model="filters.economy" type="text" /></label>
    <label>State <input v-model="filters.state" type="text" placeholder="Infrastructure Failure" /></label>
    <label>Source
      <select v-model="filters.source">
        <option>Any</option>
        <option>local_visit</option>
        <option>spansh</option>
        <option>imported</option>
      </select>
    </label>
    <label class="check"><input v-model="filters.includeFc" type="checkbox" /> Include fleet carriers</label>
    <label>Highlight price ≤ <input v-model.number="filters.priceThreshold" type="number" /></label>
    <label>Strong supply ≥ <input v-model.number="filters.supplyThreshold" type="number" /></label>
    <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
    <label class="ledgerOnly">Commodity <input v-model="ledgerFilters.commodity" type="text" placeholder="Gold" /></label>
    <label class="ledgerOnly">Trade Type
      <select v-model="ledgerFilters.eventType"><option>Any</option><option>buy</option><option>sell</option></select>
    </label>
    <label class="ledgerOnly check"><input v-model="ledgerFilters.showLifo" type="checkbox" /> Show LIFO</label>
    <button type="button" @click="applyCurrentView">Apply</button>
    <button type="button" @click="loadStations">Stations</button>
    <button type="button" @click="loadJackpots">Jackpot History</button>
    <button type="button" @click="loadLedger">Ledger</button>
    <button type="button" @click="openCommoditySettings">Commodities</button>
  </section>

  <section v-if="settingsVisible" class="settingsPanel">
    <div class="settingsHeader"><h2>Watched commodities</h2><button type="button" @click="settingsVisible = false">Close</button></div>
    <p class="subtitle">Watched commodities drive highlighting/details. Select Buy/Sell columns separately for the table.</p>
    <label>Filter commodities <input v-model="commoditySearch" type="text" placeholder="gold, palladium, osmium…" /></label>
    <div class="commoditySettings">
      <div v-for="commodity in filteredCommodities" :key="commodity" class="commodityRow">
        <label><input type="checkbox" :checked="watchedCommodities.includes(commodity)" @change="setWatchedCommodity(commodity, $event.target.checked)" /> {{ commodity }}</label>
        <label><input type="checkbox" :checked="isColumnSelected(commodity, 'buy')" @change="setDisplayColumn(commodity, 'buy', $event.target.checked)" /> Buy col</label>
        <label><input type="checkbox" :checked="isColumnSelected(commodity, 'sell')" @change="setDisplayColumn(commodity, 'sell', $event.target.checked)" /> Sell col</label>
      </div>
    </div>
    <button type="button" @click="saveCommoditySettings">Save commodity settings</button>
  </section>

  <main>
    <section class="tablePanel">
      <table v-if="currentView === 'stations'">
        <thead>
          <tr>
            <th>Flag</th><th>System / Station</th><th>State / Economy</th><th>Best Buy</th>
            <th v-for="col in displayColumns" :key="columnKey(col)">{{ col.commodity }} {{ col.side === 'buy' ? 'Buy' : 'Sell' }}</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="`${row.market_id || idx}-${row.system}-${row.station}`" :class="[rowFlag(row).cls, { selected: idx === selectedIndex }]" @click="setSelected(idx)">
            <td class="flag">{{ rowFlag(row).text }}</td>
            <td><div class="systemName">{{ fmt(row.system) }}</div><div class="stationName">{{ fmt(row.station) }} <span class="stationMeta">| Pad {{ fmt(row.pad) }}</span></div></td>
            <td><div class="cellMain">{{ fmt(row.state) }}</div><div class="cellSub">{{ fmt(row.economies) }}</div></td>
            <td>
              <div v-if="row.best_buy_commodity" class="price"><div class="cellMain">{{ row.best_buy_commodity }} @ {{ money(row.best_buy_price) }}</div><div class="cellSub">supply: {{ money(row.best_buy_supply) }} · score: {{ money(row.best_buy_score) }}</div></div>
              <span v-else>—</span>
            </td>
            <td v-for="col in displayColumns" :key="columnKey(col)">
              <div class="price"><div class="cellMain">{{ commodityCellParts(row, col.commodity, col.side).price }}</div><div class="cellSub">{{ commodityCellParts(row, col.commodity, col.side).qtyName }}: {{ commodityCellParts(row, col.commodity, col.side).qty }}</div></div>
            </td>
            <td><div>{{ localDateTime(row.market_updated) }}</div><div class="cellSub">Visit: {{ localDateTime(row.station_visit) }}</div></td>
          </tr>
        </tbody>
      </table>

      <table v-else-if="currentView === 'jackpots'">
        <thead><tr><th>Status</th><th>System / Station</th><th>Context</th><th>Palladium</th><th>Gold</th><th>Silver</th><th>Sample Time</th><th>Detected</th></tr></thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="`${row.jackpot_id}-${row.sample_datetime}-${idx}`" :class="[{ strong: row.is_jackpot, selected: idx === selectedIndex }]" @click="setSelected(idx)">
            <td>{{ row.is_jackpot ? 'Active sample' : 'Ended sample' }}</td>
            <td><div class="systemName">{{ fmt(row.system_name) }}</div><div class="stationName">{{ fmt(row.station_name) }} <span class="stationMeta">| Pad {{ fmt(row.largest_pad) }}</span></div></td>
            <td><div class="cellMain">{{ fmt(row.station_faction_state) }}</div><div class="cellSub">{{ fmt(row.station_economies_json) }}</div></td>
            <td><div class="price"><div class="cellMain">{{ money(row.palladium_buy) }}</div><div class="cellSub">supply: {{ money(row.palladium_supply) }}</div></div></td>
            <td><div class="price"><div class="cellMain">{{ money(row.gold_buy) }}</div><div class="cellSub">supply: {{ money(row.gold_supply) }}</div></div></td>
            <td><div class="price"><div class="cellMain">{{ money(row.silver_buy) }}</div><div class="cellSub">supply: {{ money(row.silver_supply) }}</div></div></td>
            <td>{{ localDateTime(row.sample_datetime) }}</td><td>{{ localDateTime(row.detected_datetime) }}</td>
          </tr>
        </tbody>
      </table>

      <table v-else-if="currentView === 'ledger'">
        <thead><tr><th>Time</th><th>Type</th><th>System / Station</th><th>Commodity</th><th>Qty</th><th>Unit</th><th>Total</th><th>Avg Paid</th><th>Profit</th><th>Cr/hr</th><th v-if="ledgerFilters.showLifo">LIFO avg</th><th v-if="ledgerFilters.showLifo">LIFO profit</th></tr></thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="row.trade_id || idx" :class="[{ selected: idx === selectedIndex, ledgerBuy: row.event_type === 'buy', ledgerSell: row.event_type === 'sell', cheap: row.event_type === 'sell' && num(row.journal_profit) > 0 }]" @click="setSelected(idx)">
            <td>{{ shortTime(row.event_datetime) }}</td><td><span class="tradeType" :class="row.event_type">{{ row.event_type === 'buy' ? 'BUY' : row.event_type === 'sell' ? 'SELL' : fmt(row.event_type) }}</span></td>
            <td><div class="cellMain">{{ fmt(row.system_name) }}</div><div class="cellSub">{{ fmt(row.station_name) }}</div></td>
            <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div v-if="row.event_type === 'buy' && row.supply_at_trade != null" class="cellSub">Supply: {{ money(row.supply_at_trade) }}</div><div v-else-if="row.event_type === 'sell' && row.demand_at_trade != null" class="cellSub">Demand: {{ money(row.demand_at_trade) }}</div></td>
            <td class="num">{{ money(row.quantity) }}</td><td class="num">{{ money(row.unit_price) }}</td><td class="num">{{ money(row.total_credits) }}</td>
            <td class="num">{{ money(row.journal_avg_price_paid) }}</td><td class="num"><span class="profit" :class="{ positive: num(row.journal_profit) > 0, negative: num(row.journal_profit) < 0 }">{{ money(row.journal_profit) }}</span></td><td class="num">{{ money(row.profit_per_hour ?? row.credits_per_hour) }}</td>
            <td v-if="ledgerFilters.showLifo" class="num">{{ money(row.ledger_avg_buy_price) }}</td><td v-if="ledgerFilters.showLifo" class="num">{{ money(row.ledger_profit) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <aside class="details">
      <template v-if="!selectedRow">
        <h2>{{ currentView === 'jackpots' ? 'Jackpot History' : currentView === 'ledger' ? 'Ledger' : 'Details' }}</h2>
        <p>Select a row.</p>
      </template>

      <template v-else-if="currentView === 'stations'">
        <h2>{{ fmt(selectedRow.system) }}</h2>
        <p class="subtitle">{{ fmt(selectedRow.station) }} | Pad {{ fmt(selectedRow.pad) }}</p>
        <dl class="detailGrid">
          <template v-for="[k, v] in [
            ['System', selectedRow.system], ['Station', selectedRow.station], ['Pad', selectedRow.pad], ['Type', selectedRow.type],
            ['State', selectedRow.state], ['Economies', selectedRow.economies], ['System Economy', selectedRow.system_economy],
            ['Security', selectedRow.security], ['Population', money(selectedRow.population)], ['Arrival LS', money(selectedRow.arrival_ls)],
            ['Fleet Carrier', selectedRow.fleet_carrier || 'No'], ['Planetary', selectedRow.planetary || 'No'],
            ['Source', selectedRow.source], ['Source Pulled', localDateTime(selectedRow.source_pulled)], ['Source Updated', localDateTime(selectedRow.source_updated)],
            ['Market Updated', localDateTime(selectedRow.market_updated)], ['Station Visit', localDateTime(selectedRow.station_visit)],
            ['Best Buy', selectedRow.best_buy_commodity ? `${selectedRow.best_buy_commodity} @ ${money(selectedRow.best_buy_price)} / supply ${money(selectedRow.best_buy_supply)} / score ${money(selectedRow.best_buy_score)}` : '—'],
          ]" :key="k">
            <dt>{{ k }}</dt><dd>{{ fmt(v) }}</dd>
          </template>
        </dl>
        <div v-for="commodity in Array.from(new Set([...watchedCommodities, ...displayColumns.map(c => c.commodity)]))" :key="commodity" class="metalBlock">
          <h3>{{ commodity }}</h3>
          <dl class="detailGrid">
            <dt>Buy</dt><dd>{{ money(selectedRow[`${commodity}_buy`]) }}</dd>
            <dt>Supply</dt><dd>{{ money(selectedRow[`${commodity}_supply`]) }}</dd>
            <dt>Sell</dt><dd>{{ money(selectedRow[`${commodity}_sell`]) }}</dd>
            <dt>Demand</dt><dd>{{ money(selectedRow[`${commodity}_demand`]) }}</dd>
          </dl>
        </div>
      </template>

      <template v-else>
        <h2>{{ currentView === 'ledger' ? `${fmt(selectedRow.event_type).toUpperCase()} ${fmt(selectedRow.commodity)}` : `Jackpot ${fmt(selectedRow.jackpot_id)}` }}</h2>
        <pre>{{ JSON.stringify(selectedRow, null, 2) }}</pre>
      </template>
    </aside>
  </main>
</template>
