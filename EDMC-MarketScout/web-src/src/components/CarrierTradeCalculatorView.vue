<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fmt, money, num, query } from '../utils.js'

const STORAGE_KEY = 'marketscout.carrierTradeCalculator.draft'
const CUSTOM_SUPPLY_STORAGE_KEY = 'marketscout.rareCommodityCustomSupply'
const RARE_STATION_TRIP_PROFIT_TITLE = 'Aggregated Profit/Ship Trip = (carrier_capacity * profit) / (ceil(carrier_capacity / min(ship_cargo_capacity, origin_station_supply)) + ceil(carrier_capacity / ship_cargo_capacity)).'

const DEFAULT_STATION_INPUTS = {
  buyStationPrice: 6000,
  sellStationPrice: 26000,
  carrierProfitPercentage: 20,
  haulerSplit: 50,
  numTonnes: 20000,
}

const DEFAULT_RARE_INPUTS = {
  commodity: '',
  buyStationPrice: 0,
  carrierSalePrice: 0,
  carrierProfitPercentage: 20,
  numTonnes: 20000,
}

const DEFAULT_RARE_STATION_INPUTS = {
  marketId: '',
  originStockMode: 'recent',
  carrierCapacity: 20000,
  shipCargoCapacity: 1000,
  sort: 'profit_trip_desc',
}

const stationInputs = ref({ ...DEFAULT_STATION_INPUTS })
const rareInputs = ref({ ...DEFAULT_RARE_INPUTS })
const rareStationInputs = ref({ ...DEFAULT_RARE_STATION_INPUTS })
const activeTab = ref('station')
const rareRows = ref([])
const rareStatus = ref('Loading rare commodities...')
const rareStationOptions = ref([])
const rareStationRows = ref([])
const rareStationStatus = ref('Loading visited stations...')
const rareStationLoading = ref(false)
const rareStationTargetInputEl = ref(null)
const rareStationTargetQuery = ref('')
const rareStationTargetMenuOpen = ref(false)
const rareStationTargetShowAll = ref(false)
const rareStationTargetHighlightedIndex = ref(-1)
const customSupplies = ref({})
const customSupplyEditing = ref('')
const customSupplyDraft = ref('')
const rareCommoditiesLoaded = ref(false)
const rareStationOptionsLoaded = ref(false)
let skipNextRareApply = false

function loadDraft() {
  try {
    const draft = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}')
    if (draft && typeof draft === 'object') {
      if (draft.stationInputs && typeof draft.stationInputs === 'object') {
        stationInputs.value = { ...DEFAULT_STATION_INPUTS, ...draft.stationInputs }
      }
      if (draft.rareInputs && typeof draft.rareInputs === 'object') {
        rareInputs.value = { ...DEFAULT_RARE_INPUTS, ...draft.rareInputs }
        if (rareInputs.value.commodity) skipNextRareApply = true
      }
      if (draft.rareStationInputs && typeof draft.rareStationInputs === 'object') {
        rareStationInputs.value = { ...DEFAULT_RARE_STATION_INPUTS, ...draft.rareStationInputs }
      }
      if (draft.activeTab === 'station' || draft.activeTab === 'rare' || draft.activeTab === 'rare-station') {
        activeTab.value = draft.activeTab
      }
    }
  } catch (err) {
    // Ignore broken localStorage drafts.
  }
}

function saveDraft() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      activeTab: activeTab.value,
      stationInputs: stationInputs.value,
      rareInputs: rareInputs.value,
      rareStationInputs: rareStationInputs.value,
    }))
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

loadDraft()
loadCustomSupplies()

function loadCustomSupplies() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(CUSTOM_SUPPLY_STORAGE_KEY) || '{}')
    if (raw && typeof raw === 'object') {
      const next = {}
      for (const [commodity, value] of Object.entries(raw)) {
        const n = Number(value)
        if (commodity && Number.isFinite(n) && n >= 0) next[commodity] = Math.floor(n)
      }
      customSupplies.value = next
    }
  } catch (err) {
    customSupplies.value = {}
  }
}

function saveCustomSupplies() {
  try {
    window.localStorage.setItem(CUSTOM_SUPPLY_STORAGE_KEY, JSON.stringify(customSupplies.value))
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

function asNumber(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function floorCr(value) {
  return Math.floor(asNumber(value))
}

function ceilCr(value) {
  return Math.ceil(asNumber(value))
}

function clamp(value, min, max) {
  const n = asNumber(value)
  return Math.min(max, Math.max(min, n))
}

function sortCommodity(a, b) {
  return String(a.commodity || '').localeCompare(String(b.commodity || ''))
}

const stationPriceDiff = computed(() => asNumber(stationInputs.value.sellStationPrice) - asNumber(stationInputs.value.buyStationPrice))
const stationCarrierProfit = computed(() => floorCr(stationPriceDiff.value * asNumber(stationInputs.value.carrierProfitPercentage) / 100))
const stationHaulerProfitPool = computed(() => stationPriceDiff.value - stationCarrierProfit.value)
const stationLoadingHaulerPercentage = computed(() => 100 - asNumber(stationInputs.value.haulerSplit))
const stationUnloadingHaulerPercentage = computed(() => asNumber(stationInputs.value.haulerSplit))
const stationLoadingHaulerProfit = computed(() => floorCr(stationHaulerProfitPool.value * stationLoadingHaulerPercentage.value / 100))
const stationUnloadingHaulerProfit = computed(() => floorCr(stationHaulerProfitPool.value - stationLoadingHaulerProfit.value))
const stationCarrierBuyPrice = computed(() => ceilCr(asNumber(stationInputs.value.buyStationPrice) + stationLoadingHaulerProfit.value))
const stationCarrierSellPrice = computed(() => floorCr(asNumber(stationInputs.value.sellStationPrice) - stationUnloadingHaulerProfit.value))
const stationTonnes = computed(() => Math.max(0, floorCr(stationInputs.value.numTonnes)))
const stationTotalCarrierProfit = computed(() => stationCarrierProfit.value * stationTonnes.value)
const stationTotalHaulersProfit = computed(() => (stationLoadingHaulerProfit.value + stationUnloadingHaulerProfit.value) * stationTonnes.value)
const stationHaulerPoolPercentage = computed(() => Math.max(0, 100 - asNumber(stationInputs.value.carrierProfitPercentage)))

const rareSuggestions = computed(() => {
  const term = String(rareInputs.value.commodity || '').trim().toLowerCase()
  const rows = [...rareRows.value].sort(sortCommodity)
  if (!term) return rows
  return rows.filter(row => String(row.commodity || '').toLowerCase().includes(term))
})

const selectedRare = computed(() => {
  const key = String(rareInputs.value.commodity || '').trim().toLowerCase()
  return rareRows.value.find(row => String(row.commodity || '').trim().toLowerCase() === key) || null
})

const rareMaxCarrierSalePrice = computed(() => {
  const avg = num(selectedRare.value?.galactic_average_price)
  return avg === null ? 0 : avg * 100
})
const rarePriceDiff = computed(() => asNumber(rareInputs.value.carrierSalePrice) - asNumber(rareInputs.value.buyStationPrice))
const rareCarrierProfit = computed(() => floorCr(rarePriceDiff.value * asNumber(rareInputs.value.carrierProfitPercentage) / 100))
const rareLoadingHaulerProfit = computed(() => floorCr(rarePriceDiff.value - rareCarrierProfit.value))
const rareCarrierBuyPrice = computed(() => ceilCr(asNumber(rareInputs.value.buyStationPrice) + rareLoadingHaulerProfit.value))
const rareTonnes = computed(() => Math.max(0, floorCr(rareInputs.value.numTonnes)))
const rareTotalCarrierProfit = computed(() => rareCarrierProfit.value * rareTonnes.value)
const rareTotalHaulersProfit = computed(() => rareLoadingHaulerProfit.value * rareTonnes.value)
const selectedRareStation = computed(() => {
  const id = String(rareStationInputs.value.marketId || '')
  return rareStationOptions.value.find(row => String(row.market_id) === id) || null
})

const filteredRareStationOptions = computed(() => {
  const filter = String(rareStationTargetQuery.value || '').trim().toLowerCase()
  const rows = rareStationOptions.value || []
  if (rareStationTargetShowAll.value || !filter) return rows.slice(0, 500)
  return rows.filter(station => rareStationOptionLabel(station).toLowerCase().includes(filter)).slice(0, 500)
})

function rareStationOptionLabel(station) {
  return station?.label || `${station?.station_name || 'Unknown station'} in ${station?.system_name || 'Unknown system'}`
}

function syncRareStationTargetQuery() {
  rareStationTargetQuery.value = selectedRareStation.value ? rareStationOptionLabel(selectedRareStation.value) : ''
}

function selectRareStationFromInput() {
  const value = String(rareStationTargetQuery.value || '').trim().toLowerCase()
  if (!value) {
    rareStationInputs.value.marketId = ''
    rareStationRows.value = []
    return
  }
  const match = rareStationOptions.value.find(station => rareStationOptionLabel(station).trim().toLowerCase() === value)
  if (match) {
    selectRareStationTarget(match)
  } else {
    rareStationInputs.value.marketId = ''
    rareStationRows.value = []
  }
}

function updateRareStationTarget(value) {
  rareStationTargetShowAll.value = false
  rareStationTargetHighlightedIndex.value = -1
  rareStationTargetQuery.value = value
  selectRareStationFromInput()
}

function openRareStationTargetMenu() {
  if (rareStationTargetShowAll.value) {
    rareStationTargetMenuOpen.value = true
    return
  }
  rareStationTargetShowAll.value = false
  rareStationTargetMenuOpen.value = true
}

async function openFullRareStationTargetMenu() {
  rareStationTargetShowAll.value = true
  rareStationTargetMenuOpen.value = true
  rareStationTargetHighlightedIndex.value = -1
  await nextTick()
  rareStationTargetInputEl.value?.focus()
}

function closeRareStationTargetMenuSoon() {
  window.setTimeout(() => {
    rareStationTargetMenuOpen.value = false
    rareStationTargetShowAll.value = false
    rareStationTargetHighlightedIndex.value = -1
  }, 120)
}

function chooseRareStationTarget(station) {
  selectRareStationTarget(station)
  rareStationTargetQuery.value = rareStationOptionLabel(station)
  rareStationTargetMenuOpen.value = false
  rareStationTargetShowAll.value = false
  rareStationTargetHighlightedIndex.value = -1
  rareStationTargetInputEl.value?.focus()
}

function selectRareStationTarget(station) {
  const nextMarketId = String(station.market_id)
  if (rareStationInputs.value.marketId === nextMarketId) {
    if (!rareStationRows.value.length) loadRareStationRows()
    return
  }
  rareStationInputs.value.marketId = nextMarketId
  loadRareStationRows()
}

function onRareStationTargetKeydown(event) {
  if (!rareStationTargetMenuOpen.value && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
    rareStationTargetMenuOpen.value = true
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    const count = filteredRareStationOptions.value.length
    if (count) rareStationTargetHighlightedIndex.value = (rareStationTargetHighlightedIndex.value + 1) % count
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    const count = filteredRareStationOptions.value.length
    if (count) rareStationTargetHighlightedIndex.value = rareStationTargetHighlightedIndex.value <= 0 ? count - 1 : rareStationTargetHighlightedIndex.value - 1
  } else if (event.key === 'Enter' && rareStationTargetHighlightedIndex.value >= 0) {
    event.preventDefault()
    chooseRareStationTarget(filteredRareStationOptions.value[rareStationTargetHighlightedIndex.value])
  } else if (event.key === 'Escape') {
    rareStationTargetMenuOpen.value = false
    rareStationTargetShowAll.value = false
    rareStationTargetHighlightedIndex.value = -1
  }
}

function onDocumentPointerDown(event) {
  if (!event.target.closest?.('.rareStationTargetField')) {
    rareStationTargetMenuOpen.value = false
    rareStationTargetShowAll.value = false
    rareStationTargetHighlightedIndex.value = -1
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))

function effectiveOriginStock(row) {
  let source = row.usual_supply
  if (rareStationInputs.value.originStockMode === 'recent') {
    source = row.default_origin_stock ?? row.recent_supply ?? row.usual_supply
  } else if (rareStationInputs.value.originStockMode === 'custom') {
    source = customSupplies.value[row.commodity] ?? row.usual_supply
  }
  return Math.max(0, floorCr(source))
}

function setRareStationStockMode(mode) {
  rareStationInputs.value.originStockMode = mode
}

function customSupplyFor(row) {
  const value = customSupplies.value[row.commodity]
  return Number.isFinite(Number(value)) ? Number(value) : null
}

const rareStationCalculatedRows = computed(() => {
  const capacity = Math.max(0, floorCr(rareStationInputs.value.carrierCapacity))
  const shipCapacity = Math.max(0, floorCr(rareStationInputs.value.shipCargoCapacity))
  const rows = rareStationRows.value.map(row => {
    const sellPrice = asNumber(row.sell_price)
    const originBuyPrice = asNumber(row.origin_buy_price)
    const profit = floorCr(sellPrice - originBuyPrice)
    const originStock = effectiveOriginStock(row)
    const loadCapacity = Math.min(shipCapacity, originStock)
    const loadsPerCarrier = capacity > 0 && loadCapacity > 0 ? Math.ceil(capacity / loadCapacity) : 0
    const unloadsPerCarrier = capacity > 0 && shipCapacity > 0 ? Math.ceil(capacity / shipCapacity) : 0
    const totalShipTrips = loadsPerCarrier + unloadsPerCarrier
    const profitPerCarrier = floorCr(profit * capacity)
    return {
      ...row,
      profit,
      origin_stock: originStock,
      loads_per_carrier: loadsPerCarrier,
      unloads_per_carrier: unloadsPerCarrier,
      profit_per_trip: totalShipTrips > 0 ? floorCr(profitPerCarrier / totalShipTrips) : 0,
      profit_per_carrier: profitPerCarrier,
    }
  })
  const sort = rareStationInputs.value.sort
  rows.sort((a, b) => {
    if (sort === 'profit_carrier_desc') {
      return b.profit_per_carrier - a.profit_per_carrier || String(a.commodity || '').localeCompare(String(b.commodity || ''))
    }
    return b.profit_per_trip - a.profit_per_trip || String(a.commodity || '').localeCompare(String(b.commodity || ''))
  })
  return rows
})

function setStationCarrierProfitPercentage(value) {
  stationInputs.value.carrierProfitPercentage = clamp(value, 0, 100)
}

function setStationHaulerSplit(value) {
  stationInputs.value.haulerSplit = clamp(value, 0, 100)
}

function setRareCarrierProfitPercentage(value) {
  rareInputs.value.carrierProfitPercentage = clamp(value, 0, 100)
}

function clampRareSalePrice() {
  const max = rareMaxCarrierSalePrice.value
  if (max <= 0) return
  rareInputs.value.carrierSalePrice = Math.min(asNumber(rareInputs.value.carrierSalePrice), max)
}

function applySelectedRare(row) {
  if (!row) return
  rareInputs.value.commodity = row.commodity || ''
  rareInputs.value.buyStationPrice = asNumber(row.buy_price)
  rareInputs.value.carrierSalePrice = asNumber(row.galactic_average_100x || row.galactic_average_price * 100)
}

function selectRareFromInput() {
  if (selectedRare.value) applySelectedRare(selectedRare.value)
}

function resetRareStationStockToUsual() {
  setRareStationStockMode('usual')
}

function startCustomSupplyEdit(row) {
  customSupplyEditing.value = row.commodity || ''
  const current = customSupplyFor(row)
  customSupplyDraft.value = current === null ? String(effectiveOriginStock(row)) : String(current)
}

function cancelCustomSupplyEdit() {
  customSupplyEditing.value = ''
  customSupplyDraft.value = ''
}

function saveCustomSupply(row) {
  const commodity = row.commodity || ''
  if (!commodity) return
  const raw = String(customSupplyDraft.value ?? '').trim()
  const next = { ...customSupplies.value }
  if (raw === '') {
    delete next[commodity]
  } else {
    const n = Number(raw)
    if (!Number.isFinite(n) || n < 0) return
    next[commodity] = Math.floor(n)
  }
  customSupplies.value = next
  saveCustomSupplies()
  cancelCustomSupplyEdit()
}

async function loadRareCommodities() {
  if (rareCommoditiesLoaded.value) return
  rareStatus.value = 'Loading rare commodities...'
  try {
    const params = query({ sort: 'profit_desc', limit: 2000 })
    const res = await fetch(`/api/rare-commodities?${params}`, { cache: 'no-store' })
    const data = await res.json()
    rareRows.value = data.rows || []
    rareCommoditiesLoaded.value = true
    rareStatus.value = `${rareRows.value.length} rare commodities`
    if (!rareInputs.value.commodity && rareRows.value.length) {
      const firstPriced = rareRows.value.find(row => num(row.galactic_average_price) !== null && num(row.buy_price) !== null) || rareRows.value[0]
      applySelectedRare(firstPriced)
    }
  } catch (err) {
    rareRows.value = []
    rareStatus.value = 'Could not load rare commodities'
  }
}

async function loadRareStationOptions() {
  if (rareStationOptionsLoaded.value) {
    await loadRareStationRows()
    return
  }
  rareStationStatus.value = 'Loading visited stations...'
  try {
    const res = await fetch('/api/rare-station-trade-options', { cache: 'no-store' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    rareStationOptions.value = data.rows || []
    rareStationOptionsLoaded.value = true
    if (rareStationInputs.value.marketId && !selectedRareStation.value) {
      rareStationInputs.value.marketId = ''
    }
    if (!rareStationInputs.value.marketId && rareStationOptions.value.length) {
      rareStationInputs.value.marketId = String(rareStationOptions.value[0].market_id)
    }
    syncRareStationTargetQuery()
    rareStationStatus.value = rareStationOptions.value.length
      ? `${rareStationOptions.value.length} visited stations`
      : 'No visited stations with market data yet'
    await loadRareStationRows()
  } catch (err) {
    rareStationOptions.value = []
    rareStationInputs.value.marketId = ''
    syncRareStationTargetQuery()
    rareStationStatus.value = 'Could not load visited stations'
  }
}

async function loadRareStationRows() {
  if (!rareStationInputs.value.marketId) {
    rareStationRows.value = []
    return
  }
  rareStationLoading.value = true
  try {
    const params = query({ market_id: rareStationInputs.value.marketId })
    const res = await fetch(`/api/rare-station-trade?${params}`, { cache: 'no-store' })
    const data = await res.json()
    rareStationRows.value = data.rows || []
  } catch (err) {
    rareStationRows.value = []
  } finally {
    rareStationLoading.value = false
  }
}

watch(selectedRare, row => {
  if (skipNextRareApply) {
    skipNextRareApply = false
    return
  }
  if (row) applySelectedRare(row)
})

watch(() => rareInputs.value.carrierSalePrice, clampRareSalePrice)
watch(rareMaxCarrierSalePrice, max => {
  if (max > 0 && rareInputs.value.carrierSalePrice > max) rareInputs.value.carrierSalePrice = max
})
watch([activeTab, stationInputs, rareInputs, rareStationInputs], saveDraft, { deep: true })

function loadActiveTabData() {
  if (activeTab.value === 'rare') {
    loadRareCommodities()
  } else if (activeTab.value === 'rare-station') {
    loadRareStationOptions()
  }
}

watch(activeTab, loadActiveTabData)

onMounted(loadActiveTabData)
</script>

<template>
  <div class="carrierTradeCalculator">
    <div class="calculatorTabs" role="tablist" aria-label="Carrier trade calculator sections">
      <button type="button" :class="{ active: activeTab === 'station' }" @click="activeTab = 'station'">Station to Station</button>
      <button type="button" :class="{ active: activeTab === 'rare' }" @click="activeTab = 'rare'">Rare Commodities</button>
      <button type="button" :class="{ active: activeTab === 'rare-station' }" title="This is mostly for Community Goals" @click="activeTab = 'rare-station'">Rare Commodities: Station to Station</button>
    </div>

    <section v-if="activeTab === 'station'" class="calculatorPanel">
      <div class="calculatorInputs">
        <fieldset>
          <legend>Station Prices</legend>
          <div class="calculatorGrid">
            <label>Buy Station Price <input v-model.number="stationInputs.buyStationPrice" type="number" min="0" step="1" /></label>
            <label>Sell Station Price <input v-model.number="stationInputs.sellStationPrice" type="number" min="0" step="1" /></label>
            <label>Quantity <input v-model.number="stationInputs.numTonnes" type="number" min="0" step="100" /></label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Profit Split</legend>
          <label class="calculatorSlider">
            Carrier profit: {{ stationInputs.carrierProfitPercentage }}%
            <input :value="stationInputs.carrierProfitPercentage" type="range" min="0" max="100" step="1" @input="setStationCarrierProfitPercentage($event.target.value)" />
          </label>
          <label class="calculatorSlider">
            Haulers: Loading {{ stationLoadingHaulerPercentage }}% / Unloading {{ stationUnloadingHaulerPercentage }}%
            <input :value="stationInputs.haulerSplit" type="range" min="0" max="100" step="1" @input="setStationHaulerSplit($event.target.value)" />
          </label>
          <div class="sliderScale"><span>Favor Loading</span><span>Favor Unloading</span></div>
          <p class="calculatorHint">Haulers share {{ stationHaulerPoolPercentage }}% of the station price difference after the carrier share is reserved.</p>
        </fieldset>
      </div>

      <div class="calculatorOutputs">
        <div class="metricCard"><span>Loading Haulers Profit</span><strong>{{ money(stationLoadingHaulerProfit) }}</strong><small>Cr/t</small></div>
        <div class="metricCard"><span>Unloading Haulers Profit</span><strong>{{ money(stationUnloadingHaulerProfit) }}</strong><small>Cr/t</small></div>
        <div class="metricCard carrierMetric"><span>Carrier Profit</span><strong>{{ money(stationCarrierProfit) }}</strong><small>Cr/t</small></div>
        <div class="metricCard"><span>Carrier Buy Price</span><strong>{{ money(stationCarrierBuyPrice) }}</strong><small>Cr/t</small></div>
        <div class="metricCard"><span>Carrier Sell Price</span><strong>{{ money(stationCarrierSellPrice) }}</strong><small>Cr/t</small></div>
        <div class="metricCard wide"><span>Total Carrier Profit at {{ money(stationTonnes) }} tonnes sold</span><strong>{{ money(stationTotalCarrierProfit) }}</strong><small>Cr</small></div>
        <div class="metricCard wide"><span>Total Haulers Profit at {{ money(stationTonnes) }} tonnes sold</span><strong>{{ money(stationTotalHaulersProfit) }}</strong><small>Cr</small></div>
      </div>
    </section>

    <section v-else-if="activeTab === 'rare'" class="calculatorPanel">
      <div class="calculatorInputs">
        <fieldset>
          <legend>Rare Commodity</legend>
          <div class="calculatorGrid">
            <label>Rare Commodity
              <input v-model="rareInputs.commodity" type="text" list="rareCommodityCalculatorOptions" @change="selectRareFromInput" />
              <datalist id="rareCommodityCalculatorOptions">
                <option v-for="row in rareSuggestions.slice(0, 500)" :key="row.commodity" :value="row.commodity" />
              </datalist>
            </label>
            <label>Buy Station Price <input v-model.number="rareInputs.buyStationPrice" type="number" min="0" step="1" /></label>
            <label>Quantity <input v-model.number="rareInputs.numTonnes" type="number" min="0" step="1" /></label>
          </div>
          <p class="calculatorHint">{{ rareStatus }} · {{ fmt(selectedRare?.station_name) }} in {{ fmt(selectedRare?.system_name) }}</p>
        </fieldset>

        <fieldset>
          <legend>Carrier Sale</legend>
          <div class="calculatorGrid">
            <label>Carrier Sale Price
              <input v-model.number="rareInputs.carrierSalePrice" type="number" min="0" :max="rareMaxCarrierSalePrice || undefined" step="1" @blur="clampRareSalePrice" />
            </label>
            <label>Maximum Sale Price <input :value="money(rareMaxCarrierSalePrice)" type="text" disabled /></label>
          </div>
          <label class="calculatorSlider">
            Carrier profit: {{ rareInputs.carrierProfitPercentage }}%
            <input :value="rareInputs.carrierProfitPercentage" type="range" min="0" max="100" step="1" @input="setRareCarrierProfitPercentage($event.target.value)" />
          </label>
        </fieldset>
      </div>

      <div class="calculatorOutputs">
        <div class="metricCard"><span>Loading Haulers Profit</span><strong>{{ money(rareLoadingHaulerProfit) }}</strong><small>Cr/unit</small></div>
        <div class="metricCard carrierMetric"><span>Carrier Profit</span><strong>{{ money(rareCarrierProfit) }}</strong><small>Cr/unit</small></div>
        <div class="metricCard"><span>Carrier Buy Price</span><strong>{{ money(rareCarrierBuyPrice) }}</strong><small>Cr/unit</small></div>
        <div class="metricCard"><span>Carrier Sale Price</span><strong>{{ money(rareInputs.carrierSalePrice) }}</strong><small>Cr/unit</small></div>
        <div class="metricCard wide"><span>Total Carrier Profit at {{ money(rareTonnes) }} units sold</span><strong>{{ money(rareTotalCarrierProfit) }}</strong><small>Cr</small></div>
        <div class="metricCard wide"><span>Total Haulers Profit at {{ money(rareTonnes) }} units sold</span><strong>{{ money(rareTotalHaulersProfit) }}</strong><small>Cr</small></div>
      </div>
    </section>

    <section v-else class="calculatorWidePanel">
      <fieldset class="calculatorInputs rareStationControls">
        <legend>Rare Commodity Station Trade</legend>
        <div class="calculatorGrid rareStationGrid">
          <label class="rareStationTargetField">Target Station
            <div class="rareStationTargetCombo">
              <input
                ref="rareStationTargetInputEl"
                :value="rareStationTargetQuery"
                type="text"
                placeholder="Select a visited station"
                autocomplete="off"
                @input="updateRareStationTarget($event.target.value)"
                @keyup="openRareStationTargetMenu"
                @focus="openRareStationTargetMenu"
                @keydown="onRareStationTargetKeydown"
                @blur="closeRareStationTargetMenuSoon"
              />
              <button
                type="button"
                class="economyComboToggle"
                title="Show target stations"
                aria-label="Show target stations"
                @mousedown.prevent
                @click="openFullRareStationTargetMenu"
              >▾</button>
              <div v-if="rareStationTargetMenuOpen" class="economyComboMenu rareStationTargetMenu" role="listbox">
                <button
                  v-for="(station, index) in filteredRareStationOptions"
                  :key="station.market_id"
                  type="button"
                  class="economyComboOption rareStationTargetOption"
                  :class="{ active: index === rareStationTargetHighlightedIndex }"
                  @mousedown.prevent="chooseRareStationTarget(station)"
                >
                  <span>{{ fmt(station.station_name) }}</span>
                  <small>{{ fmt(station.system_name) }}</small>
                </button>
                <div v-if="!filteredRareStationOptions.length" class="economyComboEmpty">No matching target stations</div>
              </div>
            </div>
          </label>
          <label>Carrier Capacity
            <input v-model.number="rareStationInputs.carrierCapacity" type="number" min="0" step="100" />
          </label>
          <label title="This is used for calculating the aggregated profit / trip">Ship Cargo Capacity
            <input v-model.number="rareStationInputs.shipCargoCapacity" type="number" min="0" step="10" />
          </label>
          <label>Sort
            <select v-model="rareStationInputs.sort">
              <option value="profit_trip_desc">Agg. Profit/Trip</option>
              <option value="profit_carrier_desc">Profit / Carrier</option>
            </select>
          </label>
          <div class="supplyModeField">
            <span>Supply</span>
            <div class="supplyModeButtons" role="group" aria-label="Origin stock source">
              <button type="button" :class="{ active: rareStationInputs.originStockMode === 'usual' }" @click="resetRareStationStockToUsual">Usual</button>
              <button type="button" :class="{ active: rareStationInputs.originStockMode === 'recent' }" @click="setRareStationStockMode('recent')">Most Recent</button>
              <button type="button" :class="{ active: rareStationInputs.originStockMode === 'custom' }" @click="setRareStationStockMode('custom')">Custom</button>
            </div>
          </div>
        </div>
        <p class="calculatorHint">
          Origin Stock uses {{ rareStationInputs.originStockMode === 'usual' ? 'usual supply' : rareStationInputs.originStockMode === 'custom' ? 'custom supply where set, falling back to usual supply' : 'the most recently seen supply at the commodity origin, falling back to usual supply' }}.
          {{ rareStationStatus }}<span v-if="selectedRareStation"> · {{ selectedRareStation.label }}</span>
        </p>
      </fieldset>

      <div class="tableWrap">
        <table class="rareStationTradeTable">
          <thead>
            <tr>
              <th>Commodity</th>
              <th class="num">Sell Price</th>
              <th class="num">Profit</th>
              <th class="num">Origin Buy Price</th>
              <th class="num">Origin Stock</th>
              <th class="num" :title="RARE_STATION_TRIP_PROFIT_TITLE">Agg. Profit/Trip</th>
              <th class="num">Profit / Carrier</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="rareStationLoading">
              <td colspan="7">Loading station prices...</td>
            </tr>
            <tr v-else-if="!rareStationCalculatedRows.length">
              <td colspan="7">No rare commodity matches found for this station yet.</td>
            </tr>
            <template v-else>
              <tr v-for="row in rareStationCalculatedRows" :key="row.commodity">
                <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div class="cellSub">{{ fmt(row.station_name) }} in {{ fmt(row.system_name) }}</div></td>
                <td class="num">{{ money(row.sell_price) }}</td>
                <td class="num"><span class="profit" :class="{ positive: row.profit > 0, negative: row.profit < 0 }">{{ money(row.profit) }}</span></td>
                <td class="num">{{ money(row.origin_buy_price) }}</td>
                <td class="num">
                  <div v-if="customSupplyEditing === row.commodity" class="customSupplyEditor">
                    <input v-model="customSupplyDraft" type="number" min="0" step="1" aria-label="Custom supply" />
                    <button type="button" @click="saveCustomSupply(row)">Save</button>
                    <button type="button" class="secondary" @click="cancelCustomSupplyEdit">Cancel</button>
                  </div>
                  <div v-else class="supplyCell">
                    <span :title="customSupplyFor(row) !== null ? `Custom supply: ${money(customSupplyFor(row))}` : ''">{{ money(row.origin_stock) }}</span>
                    <button type="button" class="secondary compactButton" @click="startCustomSupplyEdit(row)">Set Custom</button>
                  </div>
                </td>
                <td class="num" :title="`${RARE_STATION_TRIP_PROFIT_TITLE} Loads: ${row.loads_per_carrier}; unloads: ${row.unloads_per_carrier}.`">
                  <div>{{ money(row.profit_per_trip) }}</div>
                  <div class="cellSub tripCounts">Loads {{ money(row.loads_per_carrier) }} / Unloads {{ money(row.unloads_per_carrier) }}</div>
                </td>
                <td class="num">{{ money(row.profit_per_carrier) }}</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
