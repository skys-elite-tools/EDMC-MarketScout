<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import StatusStrip from './components/StatusStrip.vue'
import TopBar from './components/TopBar.vue'
import ViewControls from './components/ViewControls.vue'
import CommoditySettings from './components/CommoditySettings.vue'
import TripRouteBar from './components/TripRouteBar.vue'
import StationsTable from './components/StationsTable.vue'
import StationDetails from './components/StationDetails.vue'
import JackpotHistory from './components/JackpotHistory.vue'
import LedgerView from './views/LedgerView.vue'
import RareCommoditiesView from './views/RareCommoditiesView.vue'
import CommoditiesView from './views/CommoditiesView.vue'
import AnalyzeCommoditiesView from './views/AnalyzeCommoditiesView.vue'
import CarrierTradeAnnouncementsView from './views/CarrierTradeAnnouncementsView.vue'
import CarrierTradeCalculatorView from './views/CarrierTradeCalculatorView.vue'
import ConfigurationView from './views/ConfigurationView.vue'
import FooterBar from './components/FooterBar.vue'
import { dedupeStationRows, query } from './utils.js'
import { dataStore } from './services/dataStoreService.js'

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
const lastVersion = ref(null)
let latestRowsRequestId = 0
const ACTIVE_VIEW_STORAGE_KEY = 'ui.activeView'
const LEGACY_ACTIVE_VIEW_STORAGE_KEY = 'marketscout.activeView'
const STATION_SCOUT_MODE_STORAGE_KEY = 'stations.scoutMode'
const STATION_SCOUT_THRESHOLDS_STORAGE_KEY = 'stations.scoutThresholds'
const VALID_VIEWS = new Set(['stations', 'jackpots', 'ledger', 'commodities', 'rare', 'analyze', 'carrier', 'carrierCalc', 'config'])
const VALID_STATION_SCOUT_MODES = new Set(['buy', 'sell'])

function loadStoredView() {
  const stored = dataStore.cached(ACTIVE_VIEW_STORAGE_KEY, 'stations', {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  return VALID_VIEWS.has(stored) ? stored : 'stations'
}

function persistCurrentView() {
  dataStore.set(ACTIVE_VIEW_STORAGE_KEY, currentView.value)
}

const currentView = ref(loadStoredView())
const displayColumns = ref([])
const watchedCommodities = ref(['Palladium', 'Gold', 'Silver'])
const cachedStationScoutMode = dataStore.cached(STATION_SCOUT_MODE_STORAGE_KEY, 'buy', { legacyJson: false })
const stationScoutMode = ref(VALID_STATION_SCOUT_MODES.has(cachedStationScoutMode) ? cachedStationScoutMode : 'buy')
const bestBuyIgnoreCommodities = ref([])
const bestBuySupplyCap = ref(1000)
const minimumPotentialProfit = ref(10000)
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
const edmcStatus = ref(null)
const autoRefresh = ref(true)
const updateStatus = ref(null)
const updateBusy = ref(false)
const updateModal = ref({
  visible: false,
  title: '',
  message: '',
  backupPath: '',
  pluginDir: '',
})
const economyPresets = ref([])
const economyPresetStatus = ref('')
const stationFilterOptions = ref({ systems: [], stations: [] })
const tripRoutes = ref([])
const activeTripRoute = ref(null)
const tripRouteBusy = ref(false)
const tripRouteStatus = ref('')

const DEFAULT_STATION_FILTERS = {
  system: '',
  station: '',
  economy: '',
  state: '',
  source: 'Any',
  includeFc: false,
  priceThreshold: 6000,
  supplyThreshold: 10000,
  sellPriceThreshold: 40000,
  demandThreshold: 10000,
  limit: 1000,
}

function stationThresholdsFrom(value) {
  const source = value && typeof value === 'object' ? value : {}
  return {
    priceThreshold: Number.isFinite(Number(source.priceThreshold)) ? Number(source.priceThreshold) : DEFAULT_STATION_FILTERS.priceThreshold,
    supplyThreshold: Number.isFinite(Number(source.supplyThreshold)) ? Number(source.supplyThreshold) : DEFAULT_STATION_FILTERS.supplyThreshold,
    sellPriceThreshold: Number.isFinite(Number(source.sellPriceThreshold)) ? Number(source.sellPriceThreshold) : DEFAULT_STATION_FILTERS.sellPriceThreshold,
    demandThreshold: Number.isFinite(Number(source.demandThreshold)) ? Number(source.demandThreshold) : DEFAULT_STATION_FILTERS.demandThreshold,
  }
}

function currentStationThresholds() {
  return stationThresholdsFrom(filters.value)
}

const cachedStationThresholds = stationThresholdsFrom(dataStore.cached(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, {}))
const filters = ref({ ...DEFAULT_STATION_FILTERS, ...cachedStationThresholds })

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

const stationModeDisplayColumns = computed(() => {
  const side = stationScoutMode.value === 'sell' ? 'sell' : 'buy'
  return watchedCommodities.value.map(commodity => ({ commodity, side }))
})

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

function beginRowsLoad(viewName, options = {}) {
  const preserveRows = options.preserveRows === true
  currentView.value = viewName
  if (!preserveRows) {
    selectedIndex.value = -1
    rows.value = []
  } else if (statusText.value && !statusText.value.endsWith(' · Refreshing...')) {
    statusText.value = `${statusText.value} · Refreshing...`
  }
  latestRowsRequestId += 1
  return latestRowsRequestId
}

function isActiveRowsLoad(viewName, requestId) {
  return currentView.value === viewName && requestId === latestRowsRequestId
}

async function clearStationFilters() {
  filters.value = {
    ...DEFAULT_STATION_FILTERS,
    ...currentStationThresholds(),
  }
  await loadStations()
}

async function loadStations(options = {}) {
  const requestId = beginRowsLoad('stations', options)
  const res = await fetch(`/api/stations?${query(stationParams())}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('stations', requestId)) return
  rows.value = dedupeStationRows(data.rows || [])
  displayColumns.value = data.display_columns || []
  watchedCommodities.value = data.watched_commodities || watchedCommodities.value
  statusText.value = `${rows.value.length} rows · ${new Date().toLocaleTimeString()}`
}

async function loadJackpots(options = {}) {
  const requestId = beginRowsLoad('jackpots', options)
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(filters.value.limit || '500')}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('jackpots', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

async function loadLedger(options = {}) {
  const requestId = beginRowsLoad('ledger', options)
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

async function loadRareCommodities(options = {}) {
  const requestId = beginRowsLoad('rare', options)
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

async function loadCommodityStats(options = {}) {
  const requestId = beginRowsLoad('commodities', options)
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

function applyCurrentView(options = {}) {
  if (currentView.value === 'config') return loadConfiguration()
  if (currentView.value === 'carrierCalc') return loadCarrierTradeCalculator()
  if (currentView.value === 'carrier') return loadCarrierTradeAlert()
  if (currentView.value === 'analyze') return loadAnalyzeCommodities()
  if (currentView.value === 'commodities') return loadCommodityStats(options)
  if (currentView.value === 'rare') return loadRareCommodities(options)
  if (currentView.value === 'ledger') return loadLedger(options)
  if (currentView.value === 'jackpots') return loadJackpots(options)
  return loadStations(options)
}

watch(currentView, () => {
  persistCurrentView()
  applyCurrentView()
})

watch(stationScoutMode, (value) => {
  const mode = VALID_STATION_SCOUT_MODES.has(value) ? value : 'buy'
  if (mode !== value) {
    stationScoutMode.value = mode
    return
  }
  dataStore.set(STATION_SCOUT_MODE_STORAGE_KEY, mode)
})

watch(
  () => [
    filters.value.priceThreshold,
    filters.value.supplyThreshold,
    filters.value.sellPriceThreshold,
    filters.value.demandThreshold,
  ],
  () => {
    dataStore.set(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, currentStationThresholds())
  }
)

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

async function loadTripRoutes() {
  const res = await fetch('/api/trip-routes', { cache: 'no-store' })
  const data = await res.json()
  tripRoutes.value = data.routes || []
  activeTripRoute.value = data.active_route || null
}

async function importTripRoute(file) {
  tripRouteBusy.value = true
  tripRouteStatus.value = 'Importing route...'
  try {
    const res = await fetch('/api/trip-routes/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(file),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not import route')
    await loadTripRoutes()
    tripRouteStatus.value = `Imported ${data.imported_stops || 0} route stops.`
    setTimeout(() => { tripRouteStatus.value = '' }, 3200)
  } catch (err) {
    tripRouteStatus.value = err?.message || String(err)
  } finally {
    tripRouteBusy.value = false
  }
}

async function startTripRoute(routeId) {
  tripRouteBusy.value = true
  try {
    const res = await fetch('/api/trip-routes/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ route_id: routeId }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not start route')
    tripRoutes.value = data.routes || []
    activeTripRoute.value = data.active_route || null
  } catch (err) {
    tripRouteStatus.value = err?.message || String(err)
  } finally {
    tripRouteBusy.value = false
  }
}

async function deleteTripRoute(routeId) {
  tripRouteBusy.value = true
  try {
    const res = await fetch('/api/trip-routes/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ route_id: routeId }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not delete route')
    tripRoutes.value = data.routes || []
    activeTripRoute.value = data.active_route || null
  } catch (err) {
    tripRouteStatus.value = err?.message || String(err)
  } finally {
    tripRouteBusy.value = false
  }
}

async function selectTripRouteStop(stop) {
  const stopSystem = String(stop.system_name || '').trim()
  const currentSystemFilter = String(filters.value.system || '').trim()
  filters.value.system = currentSystemFilter.localeCompare(stopSystem, undefined, { sensitivity: 'accent' }) === 0 ? '' : stopSystem
  await loadStations()
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
  displayColumns.value = watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  bestBuyIgnoreCommodities.value = settings.best_buy_ignore_commodities || []
  bestBuySupplyCap.value = Number(settings.best_buy_supply_cap || 1000)
  minimumPotentialProfit.value = Number(settings.minimum_potential_profit || 10000)
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

function setStationScoutMode(mode) {
  if (!VALID_STATION_SCOUT_MODES.has(mode)) return
  stationScoutMode.value = mode
}

async function saveCommoditySettings() {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      watched_commodities: watchedCommodities.value,
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
      best_buy_supply_cap: bestBuySupplyCap.value,
      minimum_potential_profit: minimumPotentialProfit.value,
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
  edmcStatus.value = data.edmc || null
  updateStatus.value = data.update || null
  if (!autoRefresh.value) {
    lastVersion.value = data.data_version
    return
  }
  if (lastVersion.value !== null && data.data_version !== lastVersion.value) {
    await Promise.all([applyCurrentView({ preserveRows: true }), loadStationFilterOptions()])
  }
  lastVersion.value = data.data_version
}

async function handleUpdateAction() {
  const update = updateStatus.value || {}
  if (!update.can_update) {
    const url = update.html_url || update.download_url
    if (url) window.open(url, '_blank', 'noopener')
    return
  }

  updateBusy.value = true
  try {
    const res = await fetch('/api/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const data = await res.json()
    updateStatus.value = data.update || updateStatus.value
    updateModal.value = {
      visible: true,
      title: data.ok ? 'Update Complete' : 'Update Could Not Be Completed',
      message: data.ok
        ? (data.message || 'Update Complete. Please restart EDMC to start using the latest version of MarketScout.')
        : `${data.message || 'The update could not be completed.'} Copy all files from the backup directory to the plugin directory if you need to restore the previous working version.`,
      backupPath: data.backup_path || '',
      pluginDir: data.plugin_dir || '',
    }
  } catch (err) {
    updateModal.value = {
      visible: true,
      title: 'Update Could Not Be Completed',
      message: `The update could not be completed. ${err?.message || err}`,
      backupPath: '',
      pluginDir: '',
    }
  } finally {
    updateBusy.value = false
  }
}

let pollTimer = null
onMounted(async () => {
  const storedView = await dataStore.get(ACTIVE_VIEW_STORAGE_KEY, currentView.value, {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  if (VALID_VIEWS.has(storedView)) currentView.value = storedView
  const storedStationScoutMode = await dataStore.get(STATION_SCOUT_MODE_STORAGE_KEY, stationScoutMode.value, { legacyJson: false })
  if (VALID_STATION_SCOUT_MODES.has(storedStationScoutMode)) stationScoutMode.value = storedStationScoutMode
  const storedStationThresholds = await dataStore.get(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, currentStationThresholds())
  filters.value = {
    ...filters.value,
    ...stationThresholdsFrom(storedStationThresholds),
  }
  await Promise.all([loadCommoditySettings(), loadEconomyPresets(), loadStationFilterOptions(), loadTripRoutes()])
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
      :edmc-status="edmcStatus"
      :update-status="updateStatus"
      :update-busy="updateBusy"
      @run-update="handleUpdateAction"
    />

    <TopBar
      v-model:current-view="currentView"
      @refresh="applyCurrentView"
    />

    <TripRouteBar
      v-if="currentView === 'stations'"
      :routes="tripRoutes"
      :active-route="activeTripRoute"
      :busy="tripRouteBusy"
      :status="tripRouteStatus"
      :current-system="latestJournalEvent?.system || ''"
      :current-position="latestJournalEvent"
      @import-route="importTripRoute"
      @start-route="startTripRoute"
      @delete-route="deleteTripRoute"
      @select-stop="selectTripRouteStop"
      @open-help="openHelp"
    />

    <ViewControls
      :current-view="currentView"
      :filters="filters"
      :ledger-filters="ledgerFilters"
      :rare-filters="rareFilters"
      :commodity-filters="commodityFilters"
      :watched-count="watchedCommodities.length"
      :best-buy-ignore-count="bestBuyIgnoreCommodities.length"
      :station-scout-mode="stationScoutMode"
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
      @set-station-scout-mode="setStationScoutMode"
    />

    <CommoditySettings
      :visible="settingsVisible"
      title="Watched commodities"
      description="Watched commodities drive highlighting, details, and the Buy Scout / Sell Scout columns."
      save-label="Save commodity settings"
      :commodities="filteredCommodities"
      :selected-commodities="watchedCommodities"
      :search="commoditySearch"
      @close="settingsVisible = false"
      @save="saveCommoditySettings"
      @update:search="commoditySearch = $event"
      @toggle-selected="setWatchedCommodity"
    />

    <CommoditySettings
      :visible="bestBuyIgnoreVisible"
      title="Best Buy settings"
      description="Tune how MarketScout chooses Best Buy opportunities. Ignored commodities are excluded, the supply cap limits how much large supply affects scoring, and the minimum potential profit controls candidate eligibility and Potential Profit visibility."
      save-label="Save Best Buy settings"
      :commodities="filteredBestBuyIgnoreCommodities"
      :selected-commodities="bestBuyIgnoreCommodities"
      :search="bestBuyIgnoreSearch"
      :show-best-buy-settings="true"
      help-article="best-buy"
      help-title="How Best Buy works"
      v-model:best-buy-supply-cap="bestBuySupplyCap"
      v-model:minimum-potential-profit="minimumPotentialProfit"
      @close="bestBuyIgnoreVisible = false"
      @save="saveBestBuyIgnoreSettings"
      @update:search="bestBuyIgnoreSearch = $event"
      @toggle-selected="setBestBuyIgnoreCommodity"
      @open-help="openHelp"
    />

    <main :class="{ detailsOpen: selectedRow }">
      <section class="tablePanel">
        <template v-if="currentView === 'stations'">
          <StationsTable
            :rows="rows"
            :selected-index="selectedIndex"
            :display-columns="stationModeDisplayColumns"
            :watched-commodities="watchedCommodities"
            :scout-mode="stationScoutMode"
            :price-threshold="filters.priceThreshold"
            :supply-threshold="filters.supplyThreshold"
            :sell-price-threshold="filters.sellPriceThreshold"
            :demand-threshold="filters.demandThreshold"
            :minimum-potential-profit="minimumPotentialProfit"
            :current-system="latestJournalEvent?.system || ''"
            @select="setSelected"
            @open-help="openHelp"
          />
        </template>
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
        <CarrierTradeAnnouncementsView
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
        :display-columns="currentView === 'stations' ? stationModeDisplayColumns : displayColumns"
        @close="closeDetails"
      />
    </main>

    <FooterBar
      :help-article="helpArticle"
      :help-request-id="helpRequestId"
    />

    <div v-if="updateModal.visible" class="modalBackdrop" @click.self="updateModal.visible = false">
      <section class="aboutModal updateModal" role="dialog" aria-modal="true" aria-labelledby="update-modal-title">
        <div class="modalHeader">
          <h2 id="update-modal-title">{{ updateModal.title }}</h2>
          <button type="button" class="iconButton" aria-label="Close" @click="updateModal.visible = false">×</button>
        </div>
        <p>{{ updateModal.message }}</p>
        <p v-if="updateModal.backupPath" class="modalPath"><strong>Backup:</strong> {{ updateModal.backupPath }}</p>
        <p v-if="updateModal.pluginDir" class="modalPath"><strong>Plugin:</strong> {{ updateModal.pluginDir }}</p>
        <div class="modalActions">
          <button type="button" @click="updateModal.visible = false">Close</button>
        </div>
      </section>
    </div>
  </div>
</template>
