<script setup>
import { storeToRefs } from 'pinia'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
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
import ModalShell from './components/ModalShell.vue'
import { useStatusStore } from './stores/statusStore.js'
import { useSystemStore } from './stores/systemStore.js'
import { useTripPlannerStore } from './stores/tripPlannerStore.js'
import { dedupeStationRows, query } from './utils.js'
import { dataStore } from './services/dataStoreService.js'

const statusStore = useStatusStore()
const {
  statusText,
  latestJournalEvent,
  updateStatus,
  updateBusy,
} = storeToRefs(statusStore)

const systemStore = useSystemStore()
const { helpArticle, helpRequestId, supportOpen } = storeToRefs(systemStore)
const { openHelp } = systemStore
const tripPlannerStore = useTripPlannerStore()

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
let latestRowsRequestId = 0
const ACTIVE_VIEW_STORAGE_KEY = 'ui.activeView'
const LEGACY_ACTIVE_VIEW_STORAGE_KEY = 'marketscout.activeView'
const STATION_SCOUT_MODE_STORAGE_KEY = 'stations.scoutMode'
const STATION_SCOUT_THRESHOLDS_STORAGE_KEY = 'stations.scoutThresholds'
const STATION_ROW_LIMIT_STORAGE_KEY = 'stations.rowLimit'
const DEFAULT_STATION_ROW_LIMIT = 30
const TARGET_STATE_TOAST_TIMEOUT_MS = 60000
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
const draftWatchedCommodities = ref(['Palladium', 'Gold', 'Silver'])
const cachedStationScoutMode = dataStore.cached(STATION_SCOUT_MODE_STORAGE_KEY, 'buy', { legacyJson: false })
const stationScoutMode = ref(VALID_STATION_SCOUT_MODES.has(cachedStationScoutMode) ? cachedStationScoutMode : 'buy')
const stationRowLimit = ref(clampStationRowLimit(dataStore.cached(STATION_ROW_LIMIT_STORAGE_KEY, DEFAULT_STATION_ROW_LIMIT)))
const bestBuyIgnoreCommodities = ref([])
const draftBestBuyIgnoreCommodities = ref([])
const bestBuySupplyCap = ref(1000)
const draftBestBuySupplyCap = ref(1000)
const minimumPotentialProfit = ref(10000)
const draftMinimumPotentialProfit = ref(10000)
const allCommodities = ref([])
const commoditiesCatalogLoaded = ref(false)
const settingsVisible = ref(false)
const bestBuyIgnoreVisible = ref(false)
const commoditySearch = ref('')
const bestBuyIgnoreSearch = ref('')
const stationRowsLoading = ref(false)
const stationRowsRendering = ref(false)
const stationPage = ref({ totalCount: 0, hasMore: false, nextOffset: null, limit: DEFAULT_STATION_ROW_LIMIT, offset: 0 })
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
const targetStateToast = ref(null)
const targetStateDetailsOpen = ref(false)
const targetStateToastCountdownKey = ref(0)
const dismissedTargetStateAlertKey = ref('')
let targetStateToastTimer = null

const DEFAULT_STATION_FILTERS = {
  system: '',
  station: '',
  economy: '',
  stationFactionState: '',
  pendingStationFactionState: '',
  source: 'Any',
  includeFc: false,
  priceThreshold: 6000,
  supplyThreshold: 10000,
  sellPriceThreshold: 40000,
  demandThreshold: 10000,
}

function clampStationRowLimit(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return DEFAULT_STATION_ROW_LIMIT
  return Math.max(30, Math.min(Math.round(number), 2000))
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

function normalizedList(value) {
  return Array.from(new Set((Array.isArray(value) ? value : []).map(item => String(item || '').trim()).filter(Boolean)))
}

function sameList(left, right) {
  const leftValues = normalizedList(left)
  const rightValues = normalizedList(right)
  if (leftValues.length !== rightValues.length) return false
  return leftValues.every((value, index) => value === rightValues[index])
}

const watchedCommoditySettingsDirty = computed(() => !sameList(draftWatchedCommodities.value, watchedCommodities.value))
const bestBuySettingsDirty = computed(() => (
  !sameList(draftBestBuyIgnoreCommodities.value, bestBuyIgnoreCommodities.value)
  || Number(draftBestBuySupplyCap.value) !== Number(bestBuySupplyCap.value)
  || Number(draftMinimumPotentialProfit.value) !== Number(minimumPotentialProfit.value)
))

function stationParams(offset = 0, limit = stationRowLimit.value) {
  return {
    system: filters.value.system,
    station: filters.value.station,
    economy: filters.value.economy,
    station_faction_state: filters.value.stationFactionState,
    pending_station_faction_state: filters.value.pendingStationFactionState,
    source: filters.value.source,
    include_fc: filters.value.includeFc ? '1' : '0',
    limit,
    offset,
  }
}

function afterBrowserPaint() {
  return new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
}

function stationStatusLabel() {
  const total = Number(stationPage.value.totalCount || rows.value.length)
  const shown = rows.value.length
  if (total && shown < total) return `Showing ${shown.toLocaleString()} of ${total.toLocaleString()} stations`
  return `${shown.toLocaleString()} stations`
}

function setSelected(idx) {
  selectedIndex.value = idx
}

function closeDetails() {
  selectedIndex.value = -1
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
  const append = options.append === true
  const offset = append ? Number(stationPage.value.nextOffset || rows.value.length || 0) : 0
  const requestLimit = append ? stationRowLimit.value : (options.preserveRows ? Math.max(stationRowLimit.value, rows.value.length || 0) : stationRowLimit.value)
  const requestId = beginRowsLoad('stations', { ...options, preserveRows: append || options.preserveRows })
  stationRowsLoading.value = true
  if (!append) {
    stationPage.value = { totalCount: 0, hasMore: false, nextOffset: null, limit: requestLimit, offset: 0 }
  }
  statusText.value = append ? `${stationStatusLabel()} · Loading more...` : 'Loading stations...'
  try {
    const res = await fetch(`/api/stations?${query(stationParams(offset, requestLimit))}`, { cache: 'no-store' })
    const data = await res.json()
    if (!isActiveRowsLoad('stations', requestId)) return
    const nextRows = data.rows || []
    rows.value = append ? dedupeStationRows([...rows.value, ...nextRows]) : dedupeStationRows(nextRows)
    displayColumns.value = data.display_columns || []
    watchedCommodities.value = data.watched_commodities || watchedCommodities.value
    stationPage.value = {
      totalCount: Number(data.total_count || rows.value.length),
      hasMore: Boolean(data.has_more),
      nextOffset: data.next_offset ?? null,
      limit: Number(data.limit || stationRowLimit.value),
      offset: Number(data.offset || offset),
    }
    await nextTick()
    await afterBrowserPaint()
    statusText.value = `${stationStatusLabel()} · ${new Date().toLocaleTimeString()}`
  } finally {
    if (isActiveRowsLoad('stations', requestId)) stationRowsLoading.value = false
  }
}

async function loadMoreStations() {
  if (!stationPage.value.hasMore || stationRowsLoading.value) return
  await loadStations({ append: true })
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

async function applyTripRouteStopSelection(stop) {
  const stopSystem = String(stop.system_name || '').trim()
  const stopStation = String(stop.station_hint_name || '').trim()
  const currentSystemFilter = String(filters.value.system || '').trim()
  const currentStationFilter = String(filters.value.station || '').trim()
  const sameSystem = currentSystemFilter.localeCompare(stopSystem, undefined, { sensitivity: 'accent' }) === 0
  const sameStation = !stopStation || currentStationFilter.localeCompare(stopStation, undefined, { sensitivity: 'accent' }) === 0
  if (sameSystem && sameStation) {
    filters.value.system = ''
    if (stopStation) filters.value.station = ''
  } else {
    filters.value.system = stopSystem
    if (stopStation) filters.value.station = stopStation
  }
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
  draftWatchedCommodities.value = [...watchedCommodities.value]
  displayColumns.value = watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  bestBuyIgnoreCommodities.value = settings.best_buy_ignore_commodities || []
  draftBestBuyIgnoreCommodities.value = [...bestBuyIgnoreCommodities.value]
  bestBuySupplyCap.value = Number(settings.best_buy_supply_cap || 1000)
  draftBestBuySupplyCap.value = bestBuySupplyCap.value
  minimumPotentialProfit.value = Number(settings.minimum_potential_profit || 10000)
  draftMinimumPotentialProfit.value = minimumPotentialProfit.value
  if (!commoditiesCatalogLoaded.value) {
    const commoditiesRes = await fetch('/api/commodities', { cache: 'no-store' })
    const data = await commoditiesRes.json()
    allCommodities.value = data.commodities || []
    commoditiesCatalogLoaded.value = true
  }
  allCommodities.value = Array.from(new Set([...allCommodities.value, ...watchedCommodities.value, ...bestBuyIgnoreCommodities.value, ...draftWatchedCommodities.value, ...draftBestBuyIgnoreCommodities.value])).sort()
}

const filteredCommodities = computed(() => {
  const filter = (commoditySearch.value || '').toLowerCase()
  const selected = new Set(draftWatchedCommodities.value)
  const selectedRows = allCommodities.value.filter(c => selected.has(c))
  const matchedRows = allCommodities.value.filter(c => !selected.has(c) && (!filter || c.toLowerCase().includes(filter)))
  return [...selectedRows, ...matchedRows.slice(0, COMMODITY_SELECTOR_LIMIT)]
})

const filteredBestBuyIgnoreCommodities = computed(() => {
  const filter = (bestBuyIgnoreSearch.value || '').toLowerCase()
  const selected = new Set(draftBestBuyIgnoreCommodities.value)
  const selectedRows = allCommodities.value.filter(c => selected.has(c))
  const matchedRows = allCommodities.value.filter(c => !selected.has(c) && (!filter || c.toLowerCase().includes(filter)))
  return [...selectedRows, ...matchedRows.slice(0, COMMODITY_SELECTOR_LIMIT)]
})

function setWatchedCommodity(commodity, checked) {
  const set = new Set(draftWatchedCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  draftWatchedCommodities.value = Array.from(set)
}

function setBestBuyIgnoreCommodity(commodity, checked) {
  const set = new Set(draftBestBuyIgnoreCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  draftBestBuyIgnoreCommodities.value = Array.from(set)
}

async function setStationScoutMode(mode) {
  if (!VALID_STATION_SCOUT_MODES.has(mode)) return
  if (stationScoutMode.value === mode) return
  stationRowsRendering.value = currentView.value === 'stations'
  stationScoutMode.value = mode
  try {
    await nextTick()
    await afterBrowserPaint()
  } finally {
    stationRowsRendering.value = false
  }
}

function setStationRowLimit(value) {
  const nextLimit = clampStationRowLimit(value)
  if (stationRowLimit.value === nextLimit) return
  stationRowLimit.value = nextLimit
  dataStore.set(STATION_ROW_LIMIT_STORAGE_KEY, nextLimit, { debounceMs: 0 })
  if (currentView.value === 'stations') loadStations()
}

async function saveCommoditySettings() {
  const nextWatched = normalizedList(draftWatchedCommodities.value)
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      watched_commodities: nextWatched,
    }),
  })
  watchedCommodities.value = nextWatched
  displayColumns.value = watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  settingsVisible.value = false
  await loadStations()
}

async function saveBestBuyIgnoreSettings() {
  const nextIgnore = normalizedList(draftBestBuyIgnoreCommodities.value)
  const nextSupplyCap = Math.max(1, Number(draftBestBuySupplyCap.value) || 1000)
  const nextMinimumProfit = Math.max(0, Number(draftMinimumPotentialProfit.value) || 0)
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      best_buy_ignore_commodities: nextIgnore,
      best_buy_supply_cap: nextSupplyCap,
      minimum_potential_profit: nextMinimumProfit,
    }),
  })
  bestBuyIgnoreCommodities.value = nextIgnore
  bestBuySupplyCap.value = nextSupplyCap
  minimumPotentialProfit.value = nextMinimumProfit
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
  return statusStore.pollStatus({
    onTargetStateAlert: updateTargetStateToast,
    onDataVersionChanged: async () => {
      await Promise.all([applyCurrentView({ preserveRows: true }), loadStationFilterOptions()])
    },
  })
}

function clearTargetStateToastTimer() {
  if (targetStateToastTimer) {
    clearTimeout(targetStateToastTimer)
    targetStateToastTimer = null
  }
}

function dismissTargetStateToast() {
  if (targetStateToast.value?.key) dismissedTargetStateAlertKey.value = targetStateToast.value.key
  targetStateToast.value = null
  targetStateDetailsOpen.value = false
  clearTargetStateToastTimer()
}

function expireTargetStateToast() {
  if (targetStateToast.value?.key) dismissedTargetStateAlertKey.value = targetStateToast.value.key
  targetStateToast.value = null
  targetStateDetailsOpen.value = false
  targetStateToastTimer = null
}

function resetTargetStateToastTimer() {
  if (!targetStateToast.value?.key) return
  clearTargetStateToastTimer()
  targetStateToastCountdownKey.value += 1
  targetStateToastTimer = setTimeout(expireTargetStateToast, TARGET_STATE_TOAST_TIMEOUT_MS)
}

function openTargetStateDetails() {
  targetStateDetailsOpen.value = true
  resetTargetStateToastTimer()
}

function formatTargetStateTimestamp(value) {
  if (!value) return ''
  const time = Date.parse(value)
  if (!Number.isFinite(time)) return String(value)
  return new Date(time).toLocaleString()
}

function formatInfluence(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return ''
  return `${(number * 100).toFixed(1)}%`
}

function targetStateStationSummary(station) {
  const parts = [station.station_type, station.largest_pad ? `${station.largest_pad}-Pad` : ''].filter(Boolean)
  return parts.join(' · ')
}

function updateTargetStateToast(alert) {
  if (!alert?.key) {
    targetStateToast.value = null
    targetStateDetailsOpen.value = false
    clearTargetStateToastTimer()
    return
  }
  if (targetStateToast.value?.key === alert.key || dismissedTargetStateAlertKey.value === alert.key) {
    return
  }
  targetStateToast.value = alert
  targetStateDetailsOpen.value = false
  resetTargetStateToastTimer()
}



async function discardEdmcDelayedStationMessages() {
  await statusStore.discardEdmcDelayedStationMessages({ refresh: pollStatus })
}

let pollTimer = null
onMounted(async () => {
  tripPlannerStore.setTripRouteStopSelectionHandler(applyTripRouteStopSelection)
  const storedView = await dataStore.get(ACTIVE_VIEW_STORAGE_KEY, currentView.value, {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  if (VALID_VIEWS.has(storedView)) currentView.value = storedView
  const storedStationScoutMode = await dataStore.get(STATION_SCOUT_MODE_STORAGE_KEY, stationScoutMode.value, { legacyJson: false })
  if (VALID_STATION_SCOUT_MODES.has(storedStationScoutMode)) stationScoutMode.value = storedStationScoutMode
  stationRowLimit.value = clampStationRowLimit(await dataStore.get(STATION_ROW_LIMIT_STORAGE_KEY, stationRowLimit.value))
  const storedStationThresholds = await dataStore.get(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, currentStationThresholds())
  filters.value = {
    ...filters.value,
    ...stationThresholdsFrom(storedStationThresholds),
  }
  await Promise.all([loadCommoditySettings(), loadEconomyPresets(), loadStationFilterOptions(), tripPlannerStore.loadTripRoutes()])
  await pollStatus()
  await applyCurrentView()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  tripPlannerStore.setTripRouteStopSelectionHandler(null)
  clearTargetStateToastTimer()
})
</script>

<template>
  <div class="appShell">
    <StatusStrip
      :busy-text="stationRowsLoading ? 'Loading stations...' : (stationRowsRendering ? 'Updating table...' : '')"
      @run-update="handleUpdateAction"
      @discard-edmc-delayed="discardEdmcDelayedStationMessages"
      @open-support="systemStore.openSupport()"
    />

    <section
      v-if="targetStateToast"
      class="targetStateToast"
      :class="{ targetStateToastPending: targetStateToast.tone === 'pending', targetStateToastOpen: targetStateDetailsOpen }"
      :title="targetStateToast.faction_names?.length ? targetStateToast.faction_names.join(', ') : targetStateToast.message"
      role="button"
      tabindex="0"
      @click="openTargetStateDetails"
      @keydown.enter.prevent="openTargetStateDetails"
      @keydown.space.prevent="openTargetStateDetails"
      @mouseenter="resetTargetStateToastTimer"
    >
      <div class="targetStateToastSummary">
        <strong>{{ targetStateToast.state }}</strong>
        <span>{{ targetStateToast.message }}</span>
        <small>{{ targetStateDetailsOpen ? 'Details open' : 'Click for details' }}</small>
        <button
          type="button"
          class="targetStateToastClose"
          aria-label="Dismiss target state alert"
          title="Dismiss"
          @click.stop="dismissTargetStateToast"
        >×</button>
      </div>
      <div v-if="targetStateDetailsOpen" class="targetStateToastDetails" @click.stop>
        <div class="targetStateToastDetailBlock">
          <h3>Detected Factions</h3>
          <ul>
            <li v-for="detection in targetStateToast.detections || []" :key="`${detection.state_kind}-${detection.faction_name}-${detection.updated_at}`">
              <strong>{{ detection.faction_name }}</strong>
              <span>{{ detection.state_kind === 'pending' ? 'Pending' : 'Active' }}</span>
              <span v-if="formatInfluence(detection.influence)">{{ formatInfluence(detection.influence) }}</span>
              <span v-if="formatTargetStateTimestamp(detection.updated_at)">{{ formatTargetStateTimestamp(detection.updated_at) }}</span>
            </li>
          </ul>
        </div>
        <div class="targetStateToastDetailBlock">
          <h3>Known Stations</h3>
          <ul v-if="targetStateToast.stations?.length">
            <li v-for="station in targetStateToast.stations" :key="`${station.station_faction_name}-${station.station_name}`">
              <strong>{{ station.station_name }}</strong>
              <span>{{ station.station_faction_name }}</span>
              <span v-if="targetStateStationSummary(station)">{{ targetStateStationSummary(station) }}</span>
              <span v-if="formatTargetStateTimestamp(station.last_station_visit_datetime)">Visited {{ formatTargetStateTimestamp(station.last_station_visit_datetime) }}</span>
            </li>
          </ul>
          <p v-else>No known stations owned by the detected faction in this system.</p>
          <p v-if="targetStateToast.station_ownership_note" class="targetStateToastNote">Station ownership is based on previously recorded MarketScout data and may have changed.</p>
        </div>
      </div>
      <span :key="targetStateToastCountdownKey" class="targetStateToastCountdown" aria-hidden="true"></span>
    </section>

    <TopBar
      v-model:current-view="currentView"
      @refresh="applyCurrentView"
    />

    <TripRouteBar
      v-if="currentView === 'stations'"
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
      :station-row-limit="stationRowLimit"
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
      @set-station-row-limit="setStationRowLimit"
    />

    <CommoditySettings
      :visible="settingsVisible"
      title="Watched commodities"
      description="Watched commodities drive highlighting, details, and the Buy Scout / Sell Scout columns."
      save-label="Save commodity settings"
      :save-disabled="!watchedCommoditySettingsDirty"
      :commodities="filteredCommodities"
      :selected-commodities="draftWatchedCommodities"
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
      :save-disabled="!bestBuySettingsDirty"
      :commodities="filteredBestBuyIgnoreCommodities"
      :selected-commodities="draftBestBuyIgnoreCommodities"
      :search="bestBuyIgnoreSearch"
      :show-best-buy-settings="true"
      help-article="best-buy"
      help-title="How Best Buy works"
      v-model:best-buy-supply-cap="draftBestBuySupplyCap"
      v-model:minimum-potential-profit="draftMinimumPotentialProfit"
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
          <div class="stationLoadMoreBar">
            <button
              type="button"
              class="loadMoreButton"
              :disabled="stationRowsLoading || !stationPage.hasMore"
              @click="loadMoreStations"
            >
              {{ stationPage.hasMore ? `Load More (${rows.length.toLocaleString()} of ${Number(stationPage.totalCount || 0).toLocaleString()})` : `Showing ${rows.length.toLocaleString()} station${rows.length === 1 ? '' : 's'}` }}
            </button>
          </div>
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

    <ModalShell v-if="supportOpen" title="Support MarketScout" title-id="supportTitle" panel-class="aboutModal" @close="systemStore.closeSupport()">
      <p>MarketScout is free and open source. If you find it useful and would like to support development, you can do so here:</p>
      <p>
        <a href="https://oriondreams.gumroad.com/l/MarketScout/" target="_blank" rel="noreferrer">Support MarketScout on Gumroad</a>
      </p>
      <p>Thank you for helping keep MarketScout moving forward. o7 commanders.</p>
    </ModalShell>

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
