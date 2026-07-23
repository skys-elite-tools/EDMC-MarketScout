<script setup>
import { onMounted, ref, watch } from 'vue'
import CarrierTradeRareCalculator from '../components/CarrierTradeRareCalculator.vue'
import CarrierTradeRareStationCalculator from '../components/CarrierTradeRareStationCalculator.vue'
import CarrierTradeStationCalculator from '../components/CarrierTradeStationCalculator.vue'
import { dataStore } from '../services/dataStoreService.js'

const STORAGE_KEY = 'carrierTradeCalculator.draft'
const LEGACY_STORAGE_KEY = 'marketscout.carrierTradeCalculator.draft'

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

function applyDraft(draft) {
  if (draft && typeof draft === 'object') {
    if (draft.stationInputs && typeof draft.stationInputs === 'object') {
      stationInputs.value = { ...DEFAULT_STATION_INPUTS, ...draft.stationInputs }
    }
    if (draft.rareInputs && typeof draft.rareInputs === 'object') {
      rareInputs.value = { ...DEFAULT_RARE_INPUTS, ...draft.rareInputs }
    }
    if (draft.rareStationInputs && typeof draft.rareStationInputs === 'object') {
      rareStationInputs.value = { ...DEFAULT_RARE_STATION_INPUTS, ...draft.rareStationInputs }
    }
    if (draft.activeTab === 'station' || draft.activeTab === 'rare' || draft.activeTab === 'rare-station') {
      activeTab.value = draft.activeTab
    }
  }
}

function saveDraft() {
  dataStore.set(STORAGE_KEY, {
    activeTab: activeTab.value,
    stationInputs: stationInputs.value,
    rareInputs: rareInputs.value,
    rareStationInputs: rareStationInputs.value,
  })
}

applyDraft(dataStore.cached(STORAGE_KEY, {}, { legacyKey: LEGACY_STORAGE_KEY }))
onMounted(async () => {
  applyDraft(await dataStore.get(STORAGE_KEY, {}, { legacyKey: LEGACY_STORAGE_KEY }))
})
watch([activeTab, stationInputs, rareInputs, rareStationInputs], saveDraft, { deep: true })
</script>

<template>
  <div class="carrierTradeCalculator">
    <div class="calculatorTabs" role="tablist" aria-label="Carrier trade calculator sections">
      <button type="button" :class="{ active: activeTab === 'station' }" @click="activeTab = 'station'">Station to Station</button>
      <button type="button" :class="{ active: activeTab === 'rare' }" @click="activeTab = 'rare'">Rare Commodities</button>
      <button type="button" :class="{ active: activeTab === 'rare-station' }" title="This is mostly for Community Goals" @click="activeTab = 'rare-station'">Rare Commodities: Station to Station</button>
    </div>

    <CarrierTradeStationCalculator v-if="activeTab === 'station'" :inputs="stationInputs" />
    <CarrierTradeRareCalculator v-else-if="activeTab === 'rare'" :inputs="rareInputs" />
    <CarrierTradeRareStationCalculator v-else :inputs="rareStationInputs" />
  </div>
</template>
