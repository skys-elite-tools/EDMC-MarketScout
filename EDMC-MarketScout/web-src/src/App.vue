<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import StatusStrip from './components/StatusStrip.vue'
import TopBar from './components/TopBar.vue'
import ViewControls from './components/ViewControls.vue'
import CommoditySettings from './components/CommoditySettings.vue'
import StationsTable from './components/StationsTable.vue'
import StationDetails from './components/StationDetails.vue'
import JackpotHistory from './components/JackpotHistory.vue'
import LedgerView from './components/LedgerView.vue'
import RareCommoditiesView from './components/RareCommoditiesView.vue'
import CommoditiesView from './components/CommoditiesView.vue'
import AnalyzeCommoditiesView from './components/AnalyzeCommoditiesView.vue'
import CarrierTradeAlertView from './components/CarrierTradeAlertView.vue'
import CarrierTradeCalculatorView from './components/CarrierTradeCalculatorView.vue'
import ConfigurationView from './components/ConfigurationView.vue'
import FooterBar from './components/FooterBar.vue'
import { columnKey, dedupeStationRows, query } from './utils.js'

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
const lastVersion = ref(null)
let latestRowsRequestId = 0
const ACTIVE_VIEW_STORAGE_KEY = 'marketscout.activeView'
const VALID_VIEWS = new Set(['stations', 'jackpots', 'ledger', 'commodities', 'rare', 'analyze', 'carrier', 'carrierCalc', 'config'])

function loadStoredView() {
  try {
    const stored = window.localStorage.getItem(ACTIVE_VIEW_STORAGE_KEY)
    return VALID_VIEWS.has(stored) ? stored : 'stations'
  } catch (err) {
    return 'stations'
  }
}

function persistCurrentView() {
  try {
    window.localStorage.setItem(ACTIVE_VIEW_STORAGE_KEY, currentView.value)
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

const currentView = ref(loadStoredView())
const displayColumns = ref([])
const watchedCommodities = ref(['Palladium', 'Gold', 'Silver'])
const bestBuyIgnoreCommodities = ref([])
const allCommodities = ref([])
const commoditiesCatalogLoaded = ref(false)
const settingsVisible = ref(false)
const bestBuyIgnoreVisible = ref(false)
const helpArticle = ref('')
const helpRequestId = ref(0)
const commoditySearch = ref('')
const bestBuyIgnoreSearch = ref('')
const statusText = ref('Loading…')
const latestJournalEvent = ref(null)
const autoRefresh = ref(true)
const economyPresets = ref([])
const economyPresetStatus = ref('')
const stationFilterOptions = ref({ systems: [], stations: [] })

const DEFAULT_STATION_FILTERS = {
  system: '',
  station: '',
  economy: '',
  state: '',
  source: 'Any',
  includeFc: false,
  priceThreshold: 6000,
  supplyThreshold: 10000,
  limit: 1000,
}

const filters = ref({ ...DEFAULT_STATION_FILTERS })

const ledgerFilters = ref({
  commodity: '',
  eventType: 'Any',
  showLifo: false,
})

const rareFilters = ref({
  sort: 'profit_desc',
  engineeringOnly: false,
})

const commodityFilters = ref({
  sort: 'commodity_asc',
})
const COMMODITY_SELECTOR_LIMIT = 500

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

function setSelected(idx) {
  selectedIndex.value = idx
}

function closeDetails() {
  selectedIndex.value = -1
}

function openHelp(article = '') {
  helpArticle.value = article
  helpRequestId.value += 1
}

function beginRowsLoad(viewName) {
  currentView.value = viewName
  selectedIndex.value = -1
  rows.value = []
  latestRowsRequestId += 1
  return latestRowsRequestId
}

function isActiveRowsLoad(viewName, requestId) {
  return currentView.value === viewName && requestId === latestRowsRequestId
}

async function clearStationFilters() {
  filters.value = { ...DEFAULT_STATION_FILTERS }
  await loadStations()
}

async function loadStations() {
  const requestId = beginRowsLoad('stations')
  const res = await fetch(`/api/stations?${query(stationParams())}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('stations', requestId)) return
  rows.value = dedupeStationRows(data.rows || [])
  displayColumns.value = data.display_columns || []
  watchedCommodities.value = data.watched_commodities || watchedCommodities.value
  statusText.value = `${rows.value.length} rows · ${new Date().toLocaleTimeString()}`
}

async function loadJackpots() {
  const requestId = beginRowsLoad('jackpots')
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(filters.value.limit || '500')}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('jackpots', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

async function loadLedger() {
  const requestId = beginRowsLoad('ledger')
  const params = {
    commodity: ledgerFilters.value.commodity || '',
    event_type: ledgerFilters.value.eventType || 'Any',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/ledger?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('ledger', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} trades · ${new Date().toLocaleTimeString()}`
}

async function loadRareCommodities() {
  const requestId = beginRowsLoad('rare')
  const params = {
    sort: rareFilters.value.sort || 'profit_desc',
    engineering_only: rareFilters.value.engineeringOnly ? '1' : '0',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/rare-commodities?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('rare', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} rare commodities · ${new Date().toLocaleTimeString()}`
}

async function loadCommodityStats() {
  const requestId = beginRowsLoad('commodities')
  const params = {
    sort: commodityFilters.value.sort || 'commodity_asc',
  }
  const res = await fetch(`/api/commodity-stats?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('commodities', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} commodities · ${new Date().toLocaleTimeString()}`
}

async function loadAnalyzeCommodities() {
  beginRowsLoad('analyze')
  statusText.value = `Analyze commodities · ${new Date().toLocaleTimeString()}`
}

async function loadCarrierTradeAlert() {
  beginRowsLoad('carrier')
  statusText.value = `Carrier trade announcements · ${new Date().toLocaleTimeString()}`
}

async function loadCarrierTradeCalculator() {
  beginRowsLoad('carrierCalc')
  statusText.value = `Carrier trade calculator · ${new Date().toLocaleTimeString()}`
}

async function loadConfiguration() {
  beginRowsLoad('config')
  statusText.value = `Configuration · ${new Date().toLocaleTimeString()}`
}

function applyCurrentView() {
  if (currentView.value === 'config') return loadConfiguration()
  if (currentView.value === 'carrierCalc') return loadCarrierTradeCalculator()
  if (currentView.value === 'carrier') return loadCarrierTradeAlert()
  if (currentView.value === 'analyze') return loadAnalyzeCommodities()
  if (currentView.value === 'commodities') return loadCommodityStats()
  if (currentView.value === 'rare') return loadRareCommodities()
  if (currentView.value === 'ledger') return loadLedger()
  if (currentView.value === 'jackpots') return loadJackpots()
  return loadStations()
}

watch(currentView, () => {
  persistCurrentView()
  applyCurrentView()
})

watch(
  () => [rareFilters.value.sort, rareFilters.value.engineeringOnly],
  () => {
    if (currentView.value === 'rare') loadRareCommodities()
  }
)

watch(
  () => commodityFilters.value.sort,
  () => {
    if (currentView.value === 'commodities') loadCommodityStats()
  }
)


async function loadEconomyPresets() {
  const res = await fetch('/api/economy-presets', { cache: 'no-store' })
  const data = await res.json()
  economyPresets.value = data.presets || []
}

async function loadStationFilterOptions() {
  const res = await fetch('/api/station-filter-options', { cache: 'no-store' })
  const data = await res.json()
  stationFilterOptions.value = {
    systems: data.systems || [],
    stations: data.stations || [],
  }
}

async function saveEconomyPreset() {
  const value = (filters.value.economy || '').trim()
  if (!value) {
    economyPresetStatus.value = 'Nothing to save'
    setTimeout(() => { economyPresetStatus.value = '' }, 2200)
    return
  }
  const res = await fetch('/api/economy-presets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset: value }),
  })
  const data = await res.json()
  economyPresets.value = data.presets || economyPresets.value
  economyPresetStatus.value = data.created ? 'Saved preset' : 'Preset already saved'
  setTimeout(() => { economyPresetStatus.value = '' }, 2200)
}

async function loadCommoditySettings() {
  const settingsRes = await fetch('/api/settings', { cache: 'no-store' })
  const settings = await settingsRes.json()
  watchedCommodities.value = settings.watched_commodities || ['Palladium', 'Gold', 'Silver']
  displayColumns.value = settings.watched_columns || watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  bestBuyIgnoreCommodities.value = settings.best_buy_ignore_commodities || []
  if (!commoditiesCatalogLoaded.value) {
    const commoditiesRes = await fetch('/api/commodities', { cache: 'no-store' })
    const data = await commoditiesRes.json()
    allCommodities.value = data.commodities || []
    commoditiesCatalogLoaded.value = true
  }
  allCommodities.value = Array.from(new Set([...allCommodities.value, ...watchedCommodities.value, ...bestBuyIgnoreCommodities.value])).sort()
}

const filteredCommodities = computed(() => {
  const filter = (commoditySearch.value || '').toLowerCase()
  const selected = new Set(watchedCommodities.value)
  const selectedRows = allCommodities.value.filter(c => selected.has(c))
  const matchedRows = allCommodities.value.filter(c => !selected.has(c) && (!filter || c.toLowerCase().includes(filter)))
  return [...selectedRows, ...matchedRows.slice(0, COMMODITY_SELECTOR_LIMIT)]
})

const filteredBestBuyIgnoreCommodities = computed(() => {
  const filter = (bestBuyIgnoreSearch.value || '').toLowerCase()
  const selected = new Set(bestBuyIgnoreCommodities.value)
  const selectedRows = allCommodities.value.filter(c => selected.has(c))
  const matchedRows = allCommodities.value.filter(c => !selected.has(c) && (!filter || c.toLowerCase().includes(filter)))
  return [...selectedRows, ...matchedRows.slice(0, COMMODITY_SELECTOR_LIMIT)]
})

function setWatchedCommodity(commodity, checked) {
  const set = new Set(watchedCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  watchedCommodities.value = Array.from(set)
}

function setBestBuyIgnoreCommodity(commodity, checked) {
  const set = new Set(bestBuyIgnoreCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  bestBuyIgnoreCommodities.value = Array.from(set)
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

async function saveBestBuyIgnoreSettings() {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      best_buy_ignore_commodities: bestBuyIgnoreCommodities.value,
    }),
  })
  bestBuyIgnoreVisible.value = false
  await loadStations()
}

async function openCommoditySettings() {
  settingsVisible.value = !settingsVisible.value
  if (settingsVisible.value) bestBuyIgnoreVisible.value = false
  if (settingsVisible.value) await loadCommoditySettings()
}

async function openBestBuyIgnoreSettings() {
  bestBuyIgnoreVisible.value = !bestBuyIgnoreVisible.value
  if (bestBuyIgnoreVisible.value) settingsVisible.value = false
  if (bestBuyIgnoreVisible.value) await loadCommoditySettings()
}

async function pollStatus() {
  const res = await fetch('/api/status', { cache: 'no-store' })
  const data = await res.json()
  latestJournalEvent.value = data.latest_journal_event || null
  if (!autoRefresh.value) {
    lastVersion.value = data.data_version
    return
  }
  if (lastVersion.value !== null && data.data_version !== lastVersion.value) {
    await Promise.all([applyCurrentView(), loadStationFilterOptions()])
  }
  lastVersion.value = data.data_version
}

let pollTimer = null
onMounted(async () => {
  await Promise.all([loadCommoditySettings(), loadEconomyPresets(), loadStationFilterOptions()])
  await pollStatus()
  await applyCurrentView()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="appShell">
    <StatusStrip
      v-model:auto-refresh="autoRefresh"
      :status-text="statusText"
      :latest-journal-event="latestJournalEvent"
    />

    <TopBar
      v-model:current-view="currentView"
      @refresh="applyCurrentView"
    />

    <ViewControls
      :current-view="currentView"
      :filters="filters"
      :ledger-filters="ledgerFilters"
      :rare-filters="rareFilters"
      :commodity-filters="commodityFilters"
      :watched-count="watchedCommodities.length"
      :best-buy-ignore-count="bestBuyIgnoreCommodities.length"
      :economy-presets="economyPresets"
      :economy-preset-status="economyPresetStatus"
      :system-suggestions="stationFilterOptions.systems"
      :station-suggestions="stationFilterOptions.stations"
      @apply="applyCurrentView"
      @open-commodities="openCommoditySettings"
      @open-best-buy-ignore-list="openBestBuyIgnoreSettings"
      @save-economy-preset="saveEconomyPreset"
      @open-help="openHelp"
      @clear-station-filters="clearStationFilters"
    />

    <CommoditySettings
      :visible="settingsVisible"
      title="Watched commodities"
      description="Watched commodities drive highlighting/details. Select Buy/Sell columns separately for the table."
      save-label="Save commodity settings"
      :commodities="filteredCommodities"
      :selected-commodities="watchedCommodities"
      :display-columns="displayColumns"
      :search="commoditySearch"
      :show-display-columns="true"
      @close="settingsVisible = false"
      @save="saveCommoditySettings"
      @update:search="commoditySearch = $event"
      @toggle-selected="setWatchedCommodity"
      @toggle-display-column="setDisplayColumn"
    />

    <CommoditySettings
      :visible="bestBuyIgnoreVisible"
      title="Best Buy ignore list"
      description="Ignored commodities are excluded when MarketScout chooses a station's Best Buy. This is useful for commodities that rarely sell near the galactic maximum, so they do not crowd out more practical opportunities."
      save-label="Save ignore list"
      :commodities="filteredBestBuyIgnoreCommodities"
      :selected-commodities="bestBuyIgnoreCommodities"
      :display-columns="[]"
      :search="bestBuyIgnoreSearch"
      :show-display-columns="false"
      @close="bestBuyIgnoreVisible = false"
      @save="saveBestBuyIgnoreSettings"
      @update:search="bestBuyIgnoreSearch = $event"
      @toggle-selected="setBestBuyIgnoreCommodity"
    />

    <main :class="{ detailsOpen: selectedRow }">
      <section class="tablePanel">
        <StationsTable
          v-if="currentView === 'stations'"
          :rows="rows"
          :selected-index="selectedIndex"
          :display-columns="displayColumns"
          :watched-commodities="watchedCommodities"
          :price-threshold="filters.priceThreshold"
          :supply-threshold="filters.supplyThreshold"
          :current-system="latestJournalEvent?.system || ''"
          @select="setSelected"
        />
        <JackpotHistory
          v-else-if="currentView === 'jackpots'"
          :rows="rows"
          :selected-index="selectedIndex"
          @select="setSelected"
        />
        <LedgerView
          v-else-if="currentView === 'ledger'"
          :rows="rows"
          :selected-index="selectedIndex"
          :show-lifo="ledgerFilters.showLifo"
          @select="setSelected"
        />
        <RareCommoditiesView
          v-else-if="currentView === 'rare'"
          :rows="rows"
          :selected-index="selectedIndex"
        />
        <CommoditiesView
          v-else-if="currentView === 'commodities'"
          :rows="rows"
        />
        <AnalyzeCommoditiesView
          v-else-if="currentView === 'analyze'"
        />
        <CarrierTradeAlertView
          v-else-if="currentView === 'carrier'"
        />
        <CarrierTradeCalculatorView
          v-else-if="currentView === 'carrierCalc'"
        />
        <ConfigurationView
          v-else-if="currentView === 'config'"
        />
      </section>

      <StationDetails
        v-if="selectedRow && currentView !== 'rare'"
        :row="selectedRow"
        :current-view="currentView"
        :watched-commodities="watchedCommodities"
        :display-columns="displayColumns"
        @close="closeDetails"
      />
    </main>

    <FooterBar
      :help-article="helpArticle"
      :help-request-id="helpRequestId"
    />
  </div>
</template>
