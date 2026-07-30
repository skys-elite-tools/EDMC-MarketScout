<script setup>
import { storeToRefs } from 'pinia'
import { watch } from 'vue'
import BestBuySettings from '../components/BestBuySettings.vue'
import StationDetails from '../components/StationDetails.vue'
import StationsFilterBar from '../components/StationsFilterBar.vue'
import StationsTable from '../components/StationsTable.vue'
import TripRouteBar from '../components/TripRouteBar.vue'
import ViewHeader from '../components/ViewHeader.vue'
import WatchedCommoditySettings from '../components/WatchedCommoditySettings.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'
import { useStationsStore } from '../stores/stationsStore.js'
import { useViewRefreshStore } from '../stores/viewRefreshStore.js'

const stationViewStore = useStationViewStore()
const stationsStore = useStationsStore()
const commoditySettingsStore = useCommoditySettingsStore()
const viewRefreshStore = useViewRefreshStore()
const {
  initialized,
} = storeToRefs(stationViewStore)
const {
  watchedCommodities,
  bestBuyIgnoreCommodities,
} = storeToRefs(commoditySettingsStore)
const { selectedRow } = storeToRefs(stationsStore)

watch(
  () => viewRefreshStore.refreshSerial,
  () => {
    stationViewStore.loadStations(viewRefreshStore.refreshOptions)
  },
)

watch(
  initialized,
  (ready) => {
    if (ready) stationViewStore.loadStations()
  },
  { immediate: true },
)

</script>

<template>
  <TripRouteBar />

  <section class="viewControls stationControls">
    <ViewHeader />
    <StationsFilterBar
    :watched-count="watchedCommodities.length"
    :best-buy-ignore-count="bestBuyIgnoreCommodities.length"
    />
  </section>

  <WatchedCommoditySettings />

  <BestBuySettings />

  <StationsTable />

  <StationDetails
    v-if="selectedRow"
    current-view="stations"
  />
</template>
