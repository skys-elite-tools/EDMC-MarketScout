<script setup>
import { computed } from 'vue'
import { money } from '../utils.js'
import MetricCard from './MetricCard.vue'

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
      <MetricCard label="Loading Haulers Profit" :value="money(loadingHaulerProfit)" unit="Cr/t" />
      <MetricCard label="Unloading Haulers Profit" :value="money(unloadingHaulerProfit)" unit="Cr/t" />
      <MetricCard label="Carrier Profit" :value="money(carrierProfit)" unit="Cr/t" carrier />
      <MetricCard label="Carrier Buy Price" :value="money(carrierBuyPrice)" unit="Cr/t" />
      <MetricCard label="Carrier Sell Price" :value="money(carrierSellPrice)" unit="Cr/t" />
      <MetricCard :label="`Total Carrier Profit at ${money(tonnes)} tonnes sold`" :value="money(totalCarrierProfit)" unit="Cr" wide />
      <MetricCard :label="`Total Haulers Profit at ${money(tonnes)} tonnes sold`" :value="money(totalHaulersProfit)" unit="Cr" wide />
    </div>
  </section>
</template>
