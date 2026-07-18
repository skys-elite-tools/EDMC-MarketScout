<script setup>
import EconomyPresetInput from './EconomyPresetInput.vue'
import EconomicStateInput from './EconomicStateInput.vue'
const props = defineProps({
  currentView: { type: String, required: true },
  filters: { type: Object, required: true },
  ledgerFilters: { type: Object, required: true },
  rareFilters: { type: Object, required: true },
  commodityFilters: { type: Object, required: true },
  watchedCount: { type: Number, default: 0 },
  bestBuyIgnoreCount: { type: Number, default: 0 },
  economyPresets: { type: Array, default: () => [] },
  economyPresetStatus: { type: String, default: '' },
})
const emit = defineEmits(['apply', 'open-commodities', 'open-best-buy-ignore-list', 'save-economy-preset'])
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
        <button type="button" class="countButton" @click="emit('open-commodities')">
          <span>Watched Commodities</span>
          <span class="buttonCount">{{ watchedCount }} selected</span>
        </button>
        <button type="button" class="countButton" @click="emit('open-best-buy-ignore-list')">
          <span>Best Buy Ignore List</span>
          <span class="buttonCount">{{ bestBuyIgnoreCount }} selected</span>
        </button>
      </div>
    </template>

    <template v-else-if="currentView === 'jackpots'">
      <div class="controlGroupTitle">Jackpot controls</div>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Refresh</button>
    </template>

    <template v-else-if="currentView === 'ledger'">
      <div class="controlGroupTitle">Ledger controls</div>
      <label>Commodity <input v-model="ledgerFilters.commodity" type="text" placeholder="Gold" /></label>
      <label>Trade Type
        <select v-model="ledgerFilters.eventType"><option>Any</option><option>buy</option><option>sell</option></select>
      </label>
      <label class="check"><input v-model="ledgerFilters.showLifo" type="checkbox" /> Show LIFO</label>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>

    <template v-else-if="currentView === 'rare'">
      <div class="controlGroupTitle">Rare commodity controls</div>
      <label>Sort
        <select v-model="rareFilters.sort">
          <option value="profit_desc">Profit large to small</option>
          <option value="usual_supply_desc">Usual Supply, high to low</option>
        </select>
      </label>
      <label class="check"><input v-model="rareFilters.engineeringOnly" type="checkbox" /> Show only engineering rare commodities</label>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>

    <template v-else-if="currentView === 'commodities'">
      <div class="controlGroupTitle">Commodity controls</div>
      <label>Sort
        <select v-model="commodityFilters.sort">
          <option value="commodity_asc">Commodity asc</option>
          <option value="category_asc">Category asc</option>
          <option value="max_profit_desc">Max Profit desc</option>
        </select>
      </label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>

    <template v-else-if="currentView === 'analyze'">
      <div class="controlGroupTitle">Analyze commodities</div>
    </template>

    <template v-else-if="currentView === 'carrier'">
      <div class="controlGroupTitle">Carrier trade announcements</div>
    </template>

    <template v-else-if="currentView === 'config'">
      <div class="controlGroupTitle">Configuration</div>
    </template>
  </section>
</template>
