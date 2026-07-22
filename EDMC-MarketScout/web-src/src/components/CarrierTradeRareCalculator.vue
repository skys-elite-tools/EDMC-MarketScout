<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { fmt, money, num, query } from '../utils.js'

const props = defineProps({
  inputs: { type: Object, required: true },
})

const rareRows = ref([])
const rareStatus = ref('Loading rare commodities...')
let skipNextRareApply = false

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

const rareSuggestions = computed(() => {
  const term = String(props.inputs.commodity || '').trim().toLowerCase()
  const rows = [...rareRows.value].sort(sortCommodity)
  if (!term) return rows
  return rows.filter(row => String(row.commodity || '').toLowerCase().includes(term))
})

const selectedRare = computed(() => {
  const key = String(props.inputs.commodity || '').trim().toLowerCase()
  return rareRows.value.find(row => String(row.commodity || '').trim().toLowerCase() === key) || null
})

const maxCarrierSalePrice = computed(() => {
  const avg = num(selectedRare.value?.galactic_average_price)
  return avg === null ? 0 : avg * 100
})
const priceDiff = computed(() => asNumber(props.inputs.carrierSalePrice) - asNumber(props.inputs.buyStationPrice))
const carrierProfit = computed(() => floorCr(priceDiff.value * asNumber(props.inputs.carrierProfitPercentage) / 100))
const loadingHaulerProfit = computed(() => floorCr(priceDiff.value - carrierProfit.value))
const carrierBuyPrice = computed(() => ceilCr(asNumber(props.inputs.buyStationPrice) + loadingHaulerProfit.value))
const tonnes = computed(() => Math.max(0, floorCr(props.inputs.numTonnes)))
const totalCarrierProfit = computed(() => carrierProfit.value * tonnes.value)
const totalHaulersProfit = computed(() => loadingHaulerProfit.value * tonnes.value)

function setCarrierProfitPercentage(value) {
  props.inputs.carrierProfitPercentage = clamp(value, 0, 100)
}

function clampSalePrice() {
  const max = maxCarrierSalePrice.value
  if (max <= 0) return
  props.inputs.carrierSalePrice = Math.min(asNumber(props.inputs.carrierSalePrice), max)
}

function applySelectedRare(row) {
  if (!row) return
  props.inputs.commodity = row.commodity || ''
  props.inputs.buyStationPrice = asNumber(row.buy_price)
  props.inputs.carrierSalePrice = asNumber(row.galactic_average_100x || row.galactic_average_price * 100)
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
    if (!props.inputs.commodity && rareRows.value.length) {
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

watch(() => props.inputs.carrierSalePrice, clampSalePrice)
watch(maxCarrierSalePrice, max => {
  if (max > 0 && props.inputs.carrierSalePrice > max) props.inputs.carrierSalePrice = max
})

if (props.inputs.commodity) skipNextRareApply = true
onMounted(loadRareCommodities)
</script>

<template>
  <section class="calculatorPanel">
    <div class="calculatorInputs">
      <fieldset>
        <legend>Rare Commodity</legend>
        <div class="calculatorGrid">
          <label>Rare Commodity
            <input v-model="inputs.commodity" type="text" list="rareCommodityCalculatorOptions" @change="selectRareFromInput" />
            <datalist id="rareCommodityCalculatorOptions">
              <option v-for="row in rareSuggestions.slice(0, 500)" :key="row.commodity" :value="row.commodity" />
            </datalist>
          </label>
          <label>Buy Station Price <input v-model.number="inputs.buyStationPrice" type="number" min="0" step="1" /></label>
          <label>Quantity <input v-model.number="inputs.numTonnes" type="number" min="0" step="1" /></label>
        </div>
        <p class="calculatorHint">{{ rareStatus }} · {{ fmt(selectedRare?.station_name) }} in {{ fmt(selectedRare?.system_name) }}</p>
      </fieldset>

      <fieldset>
        <legend>Carrier Sale</legend>
        <div class="calculatorGrid">
          <label>Carrier Sale Price
            <input v-model.number="inputs.carrierSalePrice" type="number" min="0" :max="maxCarrierSalePrice || undefined" step="1" @blur="clampSalePrice" />
          </label>
          <label>Maximum Sale Price <input :value="money(maxCarrierSalePrice)" type="text" disabled /></label>
        </div>
        <label class="calculatorSlider">
          Carrier profit: {{ inputs.carrierProfitPercentage }}%
          <input :value="inputs.carrierProfitPercentage" type="range" min="0" max="100" step="1" @input="setCarrierProfitPercentage($event.target.value)" />
        </label>
      </fieldset>
    </div>

    <div class="calculatorOutputs">
      <div class="metricCard"><span>Loading Haulers Profit</span><strong>{{ money(loadingHaulerProfit) }}</strong><small>Cr/unit</small></div>
      <div class="metricCard carrierMetric"><span>Carrier Profit</span><strong>{{ money(carrierProfit) }}</strong><small>Cr/unit</small></div>
      <div class="metricCard"><span>Carrier Buy Price</span><strong>{{ money(carrierBuyPrice) }}</strong><small>Cr/unit</small></div>
      <div class="metricCard"><span>Carrier Sale Price</span><strong>{{ money(inputs.carrierSalePrice) }}</strong><small>Cr/unit</small></div>
      <div class="metricCard wide"><span>Total Carrier Profit at {{ money(tonnes) }} units sold</span><strong>{{ money(totalCarrierProfit) }}</strong><small>Cr</small></div>
      <div class="metricCard wide"><span>Total Haulers Profit at {{ money(tonnes) }} units sold</span><strong>{{ money(totalHaulersProfit) }}</strong><small>Cr</small></div>
    </div>
  </section>
</template>
