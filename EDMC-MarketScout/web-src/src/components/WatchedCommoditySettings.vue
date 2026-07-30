<script setup>
import { storeToRefs } from 'pinia'
import CommodityChecklist from './CommodityChecklist.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'

const commoditySettingsStore = useCommoditySettingsStore()
const stationViewStore = useStationViewStore()
const {
  watchedSettingsVisible,
  watchedSearch,
  filteredWatchedCommodities,
  draftWatchedCommodities,
  watchedCommoditySettingsDirty,
} = storeToRefs(commoditySettingsStore)

async function save() {
  await commoditySettingsStore.saveWatchedCommoditySettings()
  await stationViewStore.loadStations()
}
</script>

<template>
  <section v-if="watchedSettingsVisible" class="settingsPanel">
    <div class="settingsHeader">
      <h2>Watched commodities</h2>
      <div class="settingsHeaderActions">
        <button type="button" class="settingsSaveButton" :disabled="!watchedCommoditySettingsDirty" @click="save">Save commodity settings</button>
        <button type="button" @click="watchedSettingsVisible = false">Close</button>
      </div>
    </div>
    <p class="subtitle">Watched commodities drive highlighting, details, and the Buy Scout / Sell Scout columns.</p>
    <CommodityChecklist
      v-model:search="watchedSearch"
      :commodities="filteredWatchedCommodities"
      :selected-commodities="draftWatchedCommodities"
      @toggle-selected="commoditySettingsStore.setDraftWatchedCommodity"
    />
  </section>
</template>
