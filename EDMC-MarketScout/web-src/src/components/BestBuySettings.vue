<script setup>
import { storeToRefs } from 'pinia'
import CommodityChecklist from './CommodityChecklist.vue'
import InfoButton from './InfoButton.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'
import { useSystemStore } from '../stores/systemStore.js'

const commoditySettingsStore = useCommoditySettingsStore()
const stationViewStore = useStationViewStore()
const systemStore = useSystemStore()
const {
  bestBuySettingsVisible,
  bestBuyIgnoreSearch,
  filteredBestBuyIgnoreCommodities,
  draftBestBuyIgnoreCommodities,
  draftBestBuySupplyCap,
  draftMinimumPotentialProfit,
  bestBuySettingsDirty,
} = storeToRefs(commoditySettingsStore)

async function save() {
  await commoditySettingsStore.saveBestBuySettings()
  await stationViewStore.loadStations()
}
</script>

<template>
  <section v-if="bestBuySettingsVisible" class="settingsPanel">
    <div class="settingsHeader">
      <h2>
        <span>Best Buy settings</span>
        <InfoButton title="How Best Buy works" @open="systemStore.openHelp('best-buy')" />
      </h2>
      <div class="settingsHeaderActions">
        <button type="button" class="settingsSaveButton" :disabled="!bestBuySettingsDirty" @click="save">Save Best Buy settings</button>
        <button type="button" @click="bestBuySettingsVisible = false">Close</button>
      </div>
    </div>
    <p class="subtitle">Tune how MarketScout chooses Best Buy opportunities. Ignored commodities are excluded, the supply cap limits how much large supply affects scoring, and the minimum potential profit controls candidate eligibility and Potential Profit visibility.</p>
    <div class="bestBuySettingsGrid">
      <label title="Best Buy score uses min(supply, this value), so very large supply does not dominate every result.">
        Best Buy supply cap
        <input
          v-model.number="draftBestBuySupplyCap"
          type="number"
          min="1"
          step="1"
        />
      </label>
      <label title="Best Buy candidates and Potential Profit links are shown only when profit per tonne is at least this value.">
        Minimum potential profit
        <input
          v-model.number="draftMinimumPotentialProfit"
          type="number"
          min="0"
          step="100"
        />
      </label>
    </div>
    <h3 class="settingsSubheading">Best Buy Ignore List</h3>
    <CommodityChecklist
      v-model:search="bestBuyIgnoreSearch"
      :commodities="filteredBestBuyIgnoreCommodities"
      :selected-commodities="draftBestBuyIgnoreCommodities"
      @toggle-selected="commoditySettingsStore.setDraftBestBuyIgnoreCommodity"
    />
  </section>
</template>
