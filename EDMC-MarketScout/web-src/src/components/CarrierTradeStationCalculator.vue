<script setup>
import { computed } from 'vue'
import { money } from '../utils.js'

const props = defineProps({
  inputs: { type: Object, required: true },
})

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

const priceDiff = computed(() => asNumber(props.inputs.sellStationPrice) - asNumber(props.inputs.buyStationPrice))
const carrierProfit = computed(() => floorCr(priceDiff.value * asNumber(props.inputs.carrierProfitPercentage) / 100))
const haulerProfitPool = computed(() => priceDiff.value - carrierProfit.value)
const loadingHaulerPercentage = computed(() => 100 - asNumber(props.inputs.haulerSplit))
const unloadingHaulerPercentage = computed(() => asNumber(props.inputs.haulerSplit))
const loadingHaulerProfit = computed(() => floorCr(haulerProfitPool.value * loadingHaulerPercentage.value / 100))
const unloadingHaulerProfit = computed(() => floorCr(haulerProfitPool.value - loadingHaulerProfit.value))
const carrierBuyPrice = computed(() => ceilCr(asNumber(props.inputs.buyStationPrice) + loadingHaulerProfit.value))
const carrierSellPrice = computed(() => floorCr(asNumber(props.inputs.sellStationPrice) - unloadingHaulerProfit.value))
const tonnes = computed(() => Math.max(0, floorCr(props.inputs.numTonnes)))
const totalCarrierProfit = computed(() => carrierProfit.value * tonnes.value)
const totalHaulersProfit = computed(() => (loadingHaulerProfit.value + unloadingHaulerProfit.value) * tonnes.value)
const haulerPoolPercentage = computed(() => Math.max(0, 100 - asNumber(props.inputs.carrierProfitPercentage)))

function setCarrierProfitPercentage(value) {
  props.inputs.carrierProfitPercentage = clamp(value, 0, 100)
}

function setHaulerSplit(value) {
  props.inputs.haulerSplit = clamp(value, 0, 100)
}
</script>

<template>
  <section class="calculatorPanel">
    <div class="calculatorInputs">
      <fieldset>
        <legend>Station Prices</legend>
        <div class="calculatorGrid">
          <label>Buy Station Price <input v-model.number="inputs.buyStationPrice" type="number" min="0" step="1" /></label>
          <label>Sell Station Price <input v-model.number="inputs.sellStationPrice" type="number" min="0" step="1" /></label>
          <label>Quantity <input v-model.number="inputs.numTonnes" type="number" min="0" step="100" /></label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Profit Split</legend>
        <label class="calculatorSlider">
          Carrier profit: {{ inputs.carrierProfitPercentage }}%
          <input :value="inputs.carrierProfitPercentage" type="range" min="0" max="100" step="1" @input="setCarrierProfitPercentage($event.target.value)" />
        </label>
        <label class="calculatorSlider">
          Haulers: Loading {{ loadingHaulerPercentage }}% / Unloading {{ unloadingHaulerPercentage }}%
          <input :value="inputs.haulerSplit" type="range" min="0" max="100" step="1" @input="setHaulerSplit($event.target.value)" />
        </label>
        <div class="sliderScale"><span>Favor Loading</span><span>Favor Unloading</span></div>
        <p class="calculatorHint">Haulers share {{ haulerPoolPercentage }}% of the station price difference after the carrier share is reserved.</p>
      </fieldset>
    </div>

    <div class="calculatorOutputs">
      <div class="metricCard"><span>Loading Haulers Profit</span><strong>{{ money(loadingHaulerProfit) }}</strong><small>Cr/t</small></div>
      <div class="metricCard"><span>Unloading Haulers Profit</span><strong>{{ money(unloadingHaulerProfit) }}</strong><small>Cr/t</small></div>
      <div class="metricCard carrierMetric"><span>Carrier Profit</span><strong>{{ money(carrierProfit) }}</strong><small>Cr/t</small></div>
      <div class="metricCard"><span>Carrier Buy Price</span><strong>{{ money(carrierBuyPrice) }}</strong><small>Cr/t</small></div>
      <div class="metricCard"><span>Carrier Sell Price</span><strong>{{ money(carrierSellPrice) }}</strong><small>Cr/t</small></div>
      <div class="metricCard wide"><span>Total Carrier Profit at {{ money(tonnes) }} tonnes sold</span><strong>{{ money(totalCarrierProfit) }}</strong><small>Cr</small></div>
      <div class="metricCard wide"><span>Total Haulers Profit at {{ money(tonnes) }} tonnes sold</span><strong>{{ money(totalHaulersProfit) }}</strong><small>Cr</small></div>
    </div>
  </section>
</template>
