<script setup>
import { storeToRefs } from 'pinia'
import AutocompleteDropdown from './AutocompleteDropdown.vue'
import EconomyPresetInput from './EconomyPresetInput.vue'
import StationOwnerStateInput from './StationOwnerStateInput.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'

defineProps({
  watchedCount: { type: Number, default: 0 },
  bestBuyIgnoreCount: { type: Number, default: 0 },
})

const stationViewStore = useStationViewStore()
const commoditySettingsStore = useCommoditySettingsStore()
const {
  filters,
  stationScoutMode,
  stationRowLimit,
  economyPresets,
  economyPresetStatus,
  stationFilterOptions,
} = storeToRefs(stationViewStore)
</script>

<template>
  <div class="viewControlsBody stationControlsBody">
    <div class="stationFilterFields">
      <label>System
        <AutocompleteDropdown
          v-model="filters.system"
          :options="stationFilterOptions.systems"
          placeholder="Any system"
          empty-text="No matching systems"
          button-title="Show visited systems"
        />
      </label>
      <label>Station
        <AutocompleteDropdown
          v-model="filters.station"
          :options="stationFilterOptions.stations"
          placeholder="Any station"
          empty-text="No matching stations"
          button-title="Show visited stations"
        />
      </label>
      <EconomyPresetInput
        v-model="filters.economy"
        :presets="economyPresets"
        :save-status="economyPresetStatus"
        @save="stationViewStore.saveEconomyPreset"
      />
      <StationOwnerStateInput v-model="filters.stationFactionState" />
      <StationOwnerStateInput
        v-model="filters.pendingStationFactionState"
        label="Pending Owner State"
        placeholder="Any pending state"
        button-title="Show all pending station owner states"
        empty-text="No matching pending states"
      />
      <label class="sourceFilter">Source
        <select v-model="filters.source">
          <option>Any</option>
          <option>local_visit</option>
          <option>spansh</option>
          <option>imported</option>
        </select>
      </label>
      <div class="stationScoutModeField">
        <span class="fieldLabel">Scout Mode</span>
        <div class="stationScoutModeButtons" aria-label="Stations scouting mode">
          <button type="button" :class="{ active: stationScoutMode === 'buy' }" @click="stationViewStore.setStationScoutMode('buy')">Buy Scout</button>
          <button type="button" :class="{ active: stationScoutMode === 'sell' }" @click="stationViewStore.setStationScoutMode('sell')">Sell Scout</button>
        </div>
      </div>
      <label v-if="stationScoutMode === 'sell'">Highlight price ≥ <input v-model.number="filters.sellPriceThreshold" type="number" /></label>
      <label v-else>Highlight price ≤ <input v-model.number="filters.priceThreshold" type="number" /></label>
      <label v-if="stationScoutMode === 'sell'">Strong demand ≥ <input v-model.number="filters.demandThreshold" type="number" /></label>
      <label v-else>Strong supply ≥ <input v-model.number="filters.supplyThreshold" type="number" /></label>
      <label>Rows per load <input :value="stationRowLimit" type="number" min="30" max="2000" step="10" @change="stationViewStore.setStationRowLimit(Number($event.target.value || 30))" /></label>
      <label class="check includeFleetCarriers"><input v-model="filters.includeFc" type="checkbox" /> Include fleet carriers</label>
    </div>
    <div class="stationFilterActions">
      <div class="stationFilterPrimaryActions">
        <button type="button" class="applyFiltersButton" @click="stationViewStore.loadStations()">Apply Filters</button>
        <button type="button" class="clearFiltersButton" @click="stationViewStore.clearStationFilters()">Clear</button>
      </div>
      <button type="button" class="countButton" @click="commoditySettingsStore.openWatchedCommoditySettings()">
        <span>Watched Commodities</span>
        <span class="buttonCount">{{ watchedCount }} selected</span>
      </button>
      <button type="button" class="countButton" @click="commoditySettingsStore.openBestBuySettings()">
        <span>Best Buy Settings</span>
        <span class="buttonCount">{{ bestBuyIgnoreCount }} selected</span>
      </button>
    </div>
  </div>
</template>
