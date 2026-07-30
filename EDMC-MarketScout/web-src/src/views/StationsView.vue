<script setup>
import { storeToRefs } from 'pinia'
import { watch } from 'vue'
import BestBuySettings from '../components/BestBuySettings.vue'
import StationDetails from '../components/StationDetails.vue'
import StationsTable from '../components/StationsTable.vue'
import TripRouteBar from '../components/TripRouteBar.vue'
import ViewControls from '../components/ViewControls.vue'
import WatchedCommoditySettings from '../components/WatchedCommoditySettings.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'
import { useStationsStore } from '../stores/stationsStore.js'
import { useSystemStore } from '../stores/systemStore.js'

const stationViewStore = useStationViewStore()
const stationsStore = useStationsStore()
const commoditySettingsStore = useCommoditySettingsStore()
const systemStore = useSystemStore()
const {
  filters,
  stationScoutMode,
  stationRowLimit,
  economyPresets,
  economyPresetStatus,
  stationFilterOptions,
} = storeToRefs(stationViewStore)
const {
  watchedCommodities,
  bestBuyIgnoreCommodities,
} = storeToRefs(commoditySettingsStore)
const { selectedRow } = storeToRefs(stationsStore)

watch(stationScoutMode, value => {
  stationViewStore.persistStationScoutMode(value)
})

watch(
  () => [
    filters.value.priceThreshold,
    filters.value.supplyThreshold,
    filters.value.sellPriceThreshold,
    filters.value.demandThreshold,
  ],
  () => {
    stationViewStore.persistStationThresholds()
  },
)
</script>

<template>
  <TripRouteBar />

  <ViewControls
    current-view="stations"
    :filters="filters"
    :ledger-filters="{}"
    :rare-filters="{}"
    :commodity-filters="{}"
    :watched-count="watchedCommodities.length"
    :best-buy-ignore-count="bestBuyIgnoreCommodities.length"
    :station-scout-mode="stationScoutMode"
    :station-row-limit="stationRowLimit"
    :economy-presets="economyPresets"
    :economy-preset-status="economyPresetStatus"
    :system-suggestions="stationFilterOptions.systems"
    :station-suggestions="stationFilterOptions.stations"
    @apply="stationViewStore.loadStations"
    @open-commodities="commoditySettingsStore.openWatchedCommoditySettings"
    @open-best-buy-ignore-list="commoditySettingsStore.openBestBuySettings"
    @save-economy-preset="stationViewStore.saveEconomyPreset"
    @open-help="systemStore.openHelp"
    @clear-station-filters="stationViewStore.clearStationFilters"
    @set-station-scout-mode="stationViewStore.setStationScoutMode"
    @set-station-row-limit="stationViewStore.setStationRowLimit"
  />

  <WatchedCommoditySettings :after-save="stationViewStore.loadStations" />

  <BestBuySettings :after-save="stationViewStore.loadStations" />

  <StationsTable
    :scout-mode="stationScoutMode"
    :price-threshold="filters.priceThreshold"
    :supply-threshold="filters.supplyThreshold"
    :sell-price-threshold="filters.sellPriceThreshold"
    :demand-threshold="filters.demandThreshold"
    :load-options="{ rowLimit: stationRowLimit, params: stationViewStore.stationParams }"
  />

  <StationDetails
    v-if="selectedRow"
    current-view="stations"
  />
</template>
