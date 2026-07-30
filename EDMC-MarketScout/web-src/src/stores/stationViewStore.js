import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { dataStore } from '../services/dataStoreService.js'
import { useStationsStore } from './stationsStore.js'

const STATION_SCOUT_MODE_STORAGE_KEY = 'stations.scoutMode'
const STATION_SCOUT_THRESHOLDS_STORAGE_KEY = 'stations.scoutThresholds'
const STATION_ROW_LIMIT_STORAGE_KEY = 'stations.rowLimit'
const DEFAULT_STATION_ROW_LIMIT = 30
const VALID_STATION_SCOUT_MODES = new Set(['buy', 'sell'])

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

export const useStationViewStore = defineStore('stationView', () => {
  const cachedStationScoutMode = dataStore.cached(STATION_SCOUT_MODE_STORAGE_KEY, 'buy', { legacyJson: false })
  const cachedStationThresholds = stationThresholdsFrom(dataStore.cached(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, {}))
  const filters = ref({ ...DEFAULT_STATION_FILTERS, ...cachedStationThresholds })
  const stationScoutMode = ref(VALID_STATION_SCOUT_MODES.has(cachedStationScoutMode) ? cachedStationScoutMode : 'buy')
  const stationRowLimit = ref(clampStationRowLimit(dataStore.cached(STATION_ROW_LIMIT_STORAGE_KEY, DEFAULT_STATION_ROW_LIMIT)))
  const economyPresets = ref([])
  const economyPresetStatus = ref('')
  const stationFilterOptions = ref({ systems: [], stations: [] })
  const initialized = ref(false)

  watch(stationScoutMode, value => {
    persistStationScoutMode(value)
  })

  watch(
    () => [
      filters.value.priceThreshold,
      filters.value.supplyThreshold,
      filters.value.sellPriceThreshold,
      filters.value.demandThreshold,
    ],
    () => {
      persistStationThresholds()
    },
  )

  function currentStationThresholds() {
    return stationThresholdsFrom(filters.value)
  }

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

  async function initialize() {
    const storedStationScoutMode = await dataStore.get(STATION_SCOUT_MODE_STORAGE_KEY, stationScoutMode.value, { legacyJson: false })
    if (VALID_STATION_SCOUT_MODES.has(storedStationScoutMode)) stationScoutMode.value = storedStationScoutMode
    stationRowLimit.value = clampStationRowLimit(await dataStore.get(STATION_ROW_LIMIT_STORAGE_KEY, stationRowLimit.value))
    const storedStationThresholds = await dataStore.get(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, currentStationThresholds())
    filters.value = {
      ...filters.value,
      ...stationThresholdsFrom(storedStationThresholds),
    }
    await Promise.all([loadEconomyPresets(), loadStationFilterOptions()])
    initialized.value = true
  }

  async function loadStations(options = {}) {
    const stationsStore = useStationsStore()
    await stationsStore.loadStations({
      ...options,
      rowLimit: stationRowLimit.value,
      params: stationParams,
    })
  }

  async function clearStationFilters() {
    filters.value = {
      ...DEFAULT_STATION_FILTERS,
      ...currentStationThresholds(),
    }
    await loadStations()
  }

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

  async function setStationScoutMode(mode) {
    if (!VALID_STATION_SCOUT_MODES.has(mode)) return
    if (stationScoutMode.value === mode) return
    const stationsStore = useStationsStore()
    await stationsStore.renderStationRows(() => { stationScoutMode.value = mode })
  }

  function setStationRowLimit(value) {
    const nextLimit = clampStationRowLimit(value)
    if (stationRowLimit.value === nextLimit) return
    stationRowLimit.value = nextLimit
    dataStore.set(STATION_ROW_LIMIT_STORAGE_KEY, nextLimit, { debounceMs: 0 })
    loadStations()
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

  function persistStationScoutMode(value) {
    const mode = VALID_STATION_SCOUT_MODES.has(value) ? value : 'buy'
    if (mode !== value) {
      stationScoutMode.value = mode
      return
    }
    dataStore.set(STATION_SCOUT_MODE_STORAGE_KEY, mode)
  }

  function persistStationThresholds() {
    dataStore.set(STATION_SCOUT_THRESHOLDS_STORAGE_KEY, currentStationThresholds())
  }

  return {
    filters,
    stationScoutMode,
    stationRowLimit,
    economyPresets,
    economyPresetStatus,
    stationFilterOptions,
    initialized,
    initialize,
    loadStations,
    clearStationFilters,
    loadStationFilterOptions,
    saveEconomyPreset,
    setStationScoutMode,
    setStationRowLimit,
    applyTripRouteStopSelection,
    stationParams,
  }
})
