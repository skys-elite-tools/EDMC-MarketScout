<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { fmt, money, num, query } from '../utils.js'

const STORAGE_KEY = 'marketscout.carrierTradeCalculator.draft'

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

const stationInputs = ref({ ...DEFAULT_STATION_INPUTS })
const rareInputs = ref({ ...DEFAULT_RARE_INPUTS })
const activeTab = ref('station')
const rareRows = ref([])
const rareStatus = ref('Loading rare commodities...')
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
      if (draft.activeTab === 'station' || draft.activeTab === 'rare') {
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
    }))
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

loadDraft()

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

async function loadRareCommodities() {
  rareStatus.value = 'Loading rare commodities...'
  try {
    const params = query({ sort: 'profit_desc', limit: 2000 })
    const res = await fetch(`/api/rare-commodities?${params}`, { cache: 'no-store' })
    const data = await res.json()
    rareRows.value = data.rows || []
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
watch([activeTab, stationInputs, rareInputs], saveDraft, { deep: true })

onMounted(loadRareCommodities)
</script>

<template>
  <div class="carrierTradeCalculator">
    <div class="calculatorTabs" role="tablist" aria-label="Carrier trade calculator sections">
      <button type="button" :class="{ active: activeTab === 'station' }" @click="activeTab = 'station'">Station to Station</button>
      <button type="button" :class="{ active: activeTab === 'rare' }" @click="activeTab = 'rare'">Rare Commodities</button>
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

    <section v-else class="calculatorPanel">
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
  </div>
</template>
