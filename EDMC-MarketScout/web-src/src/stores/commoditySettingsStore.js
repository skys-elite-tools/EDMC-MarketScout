import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const DEFAULT_WATCHED_COMMODITIES = ['Palladium', 'Gold', 'Silver']
const COMMODITY_SELECTOR_LIMIT = 500

function normalizedList(value) {
  return Array.from(new Set((Array.isArray(value) ? value : []).map(item => String(item || '').trim()).filter(Boolean)))
}

function sameList(left, right) {
  const leftValues = normalizedList(left)
  const rightValues = normalizedList(right)
  if (leftValues.length !== rightValues.length) return false
  return leftValues.every((value, index) => value === rightValues[index])
}

export const useCommoditySettingsStore = defineStore('commoditySettings', () => {
  const watchedCommodities = ref([...DEFAULT_WATCHED_COMMODITIES])
  const draftWatchedCommodities = ref([...DEFAULT_WATCHED_COMMODITIES])
  const watchedSettingsVisible = ref(false)
  const watchedSearch = ref('')

  const bestBuyIgnoreCommodities = ref([])
  const draftBestBuyIgnoreCommodities = ref([])
  const bestBuySupplyCap = ref(1000)
  const draftBestBuySupplyCap = ref(1000)
  const minimumPotentialProfit = ref(10000)
  const draftMinimumPotentialProfit = ref(10000)
  const bestBuySettingsVisible = ref(false)
  const bestBuyIgnoreSearch = ref('')

  const allCommodities = ref([])
  const commoditiesCatalogLoaded = ref(false)

  const watchedCommoditySettingsDirty = computed(() => !sameList(draftWatchedCommodities.value, watchedCommodities.value))
  const bestBuySettingsDirty = computed(() => (
    !sameList(draftBestBuyIgnoreCommodities.value, bestBuyIgnoreCommodities.value)
    || Number(draftBestBuySupplyCap.value) !== Number(bestBuySupplyCap.value)
    || Number(draftMinimumPotentialProfit.value) !== Number(minimumPotentialProfit.value)
  ))

  const filteredWatchedCommodities = computed(() => filteredCommodities(watchedSearch.value, draftWatchedCommodities.value))
  const filteredBestBuyIgnoreCommodities = computed(() => filteredCommodities(bestBuyIgnoreSearch.value, draftBestBuyIgnoreCommodities.value))

  function filteredCommodities(search, selectedValues) {
    const filter = String(search || '').toLowerCase()
    const selected = new Set(selectedValues)
    const selectedRows = allCommodities.value.filter(commodity => selected.has(commodity))
    const matchedRows = allCommodities.value.filter(commodity => !selected.has(commodity) && (!filter || String(commodity || '').toLowerCase().includes(filter)))
    return [...selectedRows, ...matchedRows.slice(0, COMMODITY_SELECTOR_LIMIT)]
  }

  function mergeKnownCommodities() {
    allCommodities.value = Array.from(new Set([
      ...allCommodities.value,
      ...watchedCommodities.value,
      ...bestBuyIgnoreCommodities.value,
      ...draftWatchedCommodities.value,
      ...draftBestBuyIgnoreCommodities.value,
    ])).sort()
  }

  async function loadCommoditiesCatalog() {
    if (commoditiesCatalogLoaded.value) return
    const res = await fetch('/api/commodities', { cache: 'no-store' })
    const data = await res.json()
    allCommodities.value = data.commodities || []
    commoditiesCatalogLoaded.value = true
  }

  async function loadCommoditySettings() {
    const settingsRes = await fetch('/api/settings', { cache: 'no-store' })
    const settings = await settingsRes.json()
    watchedCommodities.value = settings.watched_commodities || [...DEFAULT_WATCHED_COMMODITIES]
    draftWatchedCommodities.value = [...watchedCommodities.value]
    bestBuyIgnoreCommodities.value = settings.best_buy_ignore_commodities || []
    draftBestBuyIgnoreCommodities.value = [...bestBuyIgnoreCommodities.value]
    bestBuySupplyCap.value = Number(settings.best_buy_supply_cap || 1000)
    draftBestBuySupplyCap.value = bestBuySupplyCap.value
    minimumPotentialProfit.value = Number(settings.minimum_potential_profit || 10000)
    draftMinimumPotentialProfit.value = minimumPotentialProfit.value
    await loadCommoditiesCatalog()
    mergeKnownCommodities()
  }

  function applyWatchedCommoditiesFromStations(value) {
    if (!Array.isArray(value)) return
    watchedCommodities.value = value
    if (!watchedSettingsVisible.value) draftWatchedCommodities.value = [...value]
    mergeKnownCommodities()
  }

  function setDraftWatchedCommodity(commodity, checked) {
    const set = new Set(draftWatchedCommodities.value)
    if (checked) set.add(commodity)
    else set.delete(commodity)
    draftWatchedCommodities.value = Array.from(set)
    mergeKnownCommodities()
  }

  function setDraftBestBuyIgnoreCommodity(commodity, checked) {
    const set = new Set(draftBestBuyIgnoreCommodities.value)
    if (checked) set.add(commodity)
    else set.delete(commodity)
    draftBestBuyIgnoreCommodities.value = Array.from(set)
    mergeKnownCommodities()
  }

  async function openWatchedCommoditySettings() {
    watchedSettingsVisible.value = !watchedSettingsVisible.value
    if (watchedSettingsVisible.value) {
      bestBuySettingsVisible.value = false
      await loadCommoditySettings()
    }
  }

  async function openBestBuySettings() {
    bestBuySettingsVisible.value = !bestBuySettingsVisible.value
    if (bestBuySettingsVisible.value) {
      watchedSettingsVisible.value = false
      await loadCommoditySettings()
    }
  }

  async function saveWatchedCommoditySettings() {
    const nextWatched = normalizedList(draftWatchedCommodities.value)
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watched_commodities: nextWatched }),
    })
    watchedCommodities.value = nextWatched
    watchedSettingsVisible.value = false
    mergeKnownCommodities()
  }

  async function saveBestBuySettings() {
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
    bestBuySettingsVisible.value = false
    mergeKnownCommodities()
  }

  return {
    watchedCommodities,
    draftWatchedCommodities,
    watchedSettingsVisible,
    watchedSearch,
    bestBuyIgnoreCommodities,
    draftBestBuyIgnoreCommodities,
    bestBuySupplyCap,
    draftBestBuySupplyCap,
    minimumPotentialProfit,
    draftMinimumPotentialProfit,
    bestBuySettingsVisible,
    bestBuyIgnoreSearch,
    filteredWatchedCommodities,
    filteredBestBuyIgnoreCommodities,
    watchedCommoditySettingsDirty,
    bestBuySettingsDirty,
    loadCommoditySettings,
    applyWatchedCommoditiesFromStations,
    setDraftWatchedCommodity,
    setDraftBestBuyIgnoreCommodity,
    openWatchedCommoditySettings,
    openBestBuySettings,
    saveWatchedCommoditySettings,
    saveBestBuySettings,
  }
})
