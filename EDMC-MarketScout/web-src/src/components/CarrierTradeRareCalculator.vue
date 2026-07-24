<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { carrierTradeCosts, CARRIER_TRADE_COST_TOOLTIP } from '../carrierTradeCosts.js'
import { fmt, money, num, query } from '../utils.js'
import MetricCard from './MetricCard.vue'

const props = defineProps({
  inputs: { type: Object, required: true },
  costInputs: { type: Object, required: true },
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
const tradeCosts = computed(() => carrierTradeCosts(Boolean(props.costInputs.squadronCarrier)))
const carrierNetProfit = computed(() => totalCarrierProfit.value - tradeCosts.value.totalCost)
const totalHaulersProfit = computed(() => loadingHaulerProfit.value * tonnes.value)

function setCarrierProfitPercentage(value) {
  props.inputs.carrierProfitPercentage = clamp(value, 0, 100)
}

function setSquadronCarrier(value) {
  props.costInputs.squadronCarrier = Boolean(value)
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
      <MetricCard label="Loading Haulers Profit" :value="money(loadingHaulerProfit)" unit="Cr/unit" />
      <MetricCard label="Carrier Profit" :value="money(carrierProfit)" unit="Cr/unit" carrier />
      <MetricCard label="Carrier Buy Price" :value="money(carrierBuyPrice)" unit="Cr/unit" />
      <MetricCard label="Carrier Sale Price" :value="money(inputs.carrierSalePrice)" unit="Cr/unit" />
      <MetricCard label="Carrier Net Profit, after trit and hull maint." :value="money(carrierNetProfit)" unit="Cr" carrier />
      <MetricCard label="Costs" :value="money(tradeCosts.totalCost)" unit="Cr" :title="CARRIER_TRADE_COST_TOOLTIP" inline-details>
        <template #headerRight>
          <label class="squadronToggle">
            <input :checked="costInputs.squadronCarrier" type="checkbox" @change="setSquadronCarrier($event.target.checked)" />
            Squadron Carrier
          </label>
        </template>
        <div class="costLines">
          <div><span>Tritium ({{ money(tradeCosts.tritiumTonnes) }}t)</span><strong>{{ money(tradeCosts.tritiumCost) }} Cr</strong></div>
          <div><span>Hull</span><strong>{{ money(tradeCosts.hullCost) }} Cr</strong></div>
        </div>
      </MetricCard>
      <MetricCard label="Total Haulers Profit" :value="money(totalHaulersProfit)" unit="Cr" wide />
    </div>
  </section>
</template>

<style scoped>
.calculatorPanel {
  display: grid;
  grid-template-columns: minmax(24rem, .95fr) minmax(22rem, 1.05fr);
  gap: 14px;
  align-items: start;
}

.calculatorInputs {
  display: grid;
  gap: 12px;
}

.calculatorInputs fieldset {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 12px;
  margin: 0;
  background: rgba(255,255,255,.025);
}

.calculatorInputs legend {
  color: var(--accent2);
  font-weight: 900;
  padding: 0 4px;
}

.calculatorGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-items: end;
}

.calculatorGrid label,
.calculatorSlider {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
}

.calculatorGrid input {
  width: 100%;
}

.calculatorSlider {
  margin-top: 10px;
}

.calculatorSlider input[type="range"] {
  width: 100%;
}

.calculatorHint {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.calculatorOutputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.costLines {
  display: grid;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
  min-width: 9.25rem;
}

.costLines div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.costLines strong {
  color: var(--text);
  font-size: 12px;
  line-height: 1.2;
}

.squadronToggle {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.squadronToggle input {
  margin: 0;
}

@media (max-width: 1100px) {
  .calculatorPanel,
  .calculatorGrid,
  .calculatorOutputs {
    grid-template-columns: 1fr;
  }
}
</style>
