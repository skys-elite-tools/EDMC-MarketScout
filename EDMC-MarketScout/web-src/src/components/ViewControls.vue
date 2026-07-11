<script setup>
import EconomyPresetInput from './EconomyPresetInput.vue'
import EconomicStateInput from './EconomicStateInput.vue'
const props = defineProps({
  currentView: { type: String, required: true },
  filters: { type: Object, required: true },
  ledgerFilters: { type: Object, required: true },
  economyPresets: { type: Array, default: () => [] },
  economyPresetStatus: { type: String, default: '' },
})
const emit = defineEmits(['apply', 'open-commodities', 'save-economy-preset'])
</script>

<template>
  <section class="viewControls" :class="{ stationControls: currentView === 'stations' }">
    <template v-if="currentView === 'stations'">
      <div class="controlGroupTitle">Station filters</div>
      <div class="stationFilterFields">
        <label>System <input v-model="filters.system" type="text" /></label>
        <label>Station <input v-model="filters.station" type="text" /></label>
        <EconomyPresetInput
          v-model="filters.economy"
          :presets="economyPresets"
          :save-status="economyPresetStatus"
          @save="emit('save-economy-preset')"
        />
        <EconomicStateInput v-model="filters.state" />
        <label class="sourceFilter">Source
          <select v-model="filters.source">
            <option>Any</option>
            <option>local_visit</option>
            <option>spansh</option>
            <option>imported</option>
          </select>
        </label>
        <label>Highlight price ≤ <input v-model.number="filters.priceThreshold" type="number" /></label>
        <label>Strong supply ≥ <input v-model.number="filters.supplyThreshold" type="number" /></label>
        <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
        <label class="check includeFleetCarriers"><input v-model="filters.includeFc" type="checkbox" /> Include fleet carriers</label>
      </div>
      <div class="stationFilterActions">
        <button type="button" class="applyFiltersButton" @click="emit('apply')">Apply Filters</button>
        <button type="button" @click="emit('open-commodities')">Watched Commodities</button>
      </div>
    </template>

    <template v-else-if="currentView === 'jackpots'">
      <div class="controlGroupTitle">Jackpot controls</div>
      <div class="placeholderBox">Reserved for future jackpot filters, comparisons, exports, and timeline controls.</div>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Refresh</button>
    </template>

    <template v-else-if="currentView === 'ledger'">
      <div class="controlGroupTitle">Ledger controls</div>
      <div class="placeholderBox">Reserved for future ledger summaries, charts, trip grouping, and export controls.</div>
      <label>Commodity <input v-model="ledgerFilters.commodity" type="text" placeholder="Gold" /></label>
      <label>Trade Type
        <select v-model="ledgerFilters.eventType"><option>Any</option><option>buy</option><option>sell</option></select>
      </label>
      <label class="check"><input v-model="ledgerFilters.showLifo" type="checkbox" /> Show LIFO</label>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>
  </section>
</template>
