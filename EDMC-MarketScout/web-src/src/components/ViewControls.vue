<script setup>
import { computed } from 'vue'
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
  systemSuggestions: { type: Array, default: () => [] },
  stationSuggestions: { type: Array, default: () => [] },
})
const emit = defineEmits(['apply', 'clear-station-filters', 'open-commodities', 'open-best-buy-ignore-list', 'save-economy-preset', 'open-help'])

const pageMetaByView = {
  stations: {
    title: 'Stations',
    description: 'Lists scouting data for stations visited while EDMC was running.',
  },
  jackpots: {
    title: 'Jackpots',
    description: 'Tracks high-value buy opportunities and how they change over time.',
  },
  ledger: {
    title: 'Ledger',
    description: 'Shows Journal buy and sell entries with profit and trade-rate context.',
  },
  rare: {
    title: 'Rare Commodities',
    description: 'Lists rare commodity sources, engineering unlock needs, and travel distances.',
  },
  commodities: {
    title: 'Commodities',
    description: 'Browses imported global commodity stats used by Best Buy calculations.',
  },
  analyze: {
    title: 'Analyze Commodities',
    description: 'Matches pasted commodity lists against regular and rare commodity data.',
  },
  carrier: {
    title: 'Carrier Trade Announcements',
    description: 'Creates Fleet Carrier trade announcement images and shareable text.',
  },
  carrierCalc: {
    title: 'Carrier Trade Calculator',
    description: 'Calculates carrier buy/sell prices and profit splits for station trades and rare commodities.',
  },
  config: {
    title: 'Configuration',
    description: 'Manages the local web address, shared port, and optional LAN access.',
  },
}
const pageMeta = computed(() => pageMetaByView[props.currentView] || { title: 'MarketScout', description: '' })
const hasControls = computed(() => !['analyze', 'carrier', 'carrierCalc', 'config'].includes(props.currentView))
</script>

<template>
  <section class="viewControls" :class="{ stationControls: currentView === 'stations' }">
    <div class="viewControlsHeader">
      <div class="controlGroupTitle">{{ pageMeta.title }}</div>
      <p v-if="currentView === 'stations'" class="viewControlsDescription">
        Lists scouting data for stations visited
        <button type="button" class="inlineHelpLink" @click="emit('open-help', 'edmc-running')">while EDMC was running</button>.
      </p>
      <p v-else class="viewControlsDescription">{{ pageMeta.description }}</p>
    </div>

    <div v-if="hasControls" class="viewControlsBody" :class="{ stationControlsBody: currentView === 'stations' }">
      <template v-if="currentView === 'stations'">
        <div class="stationFilterFields">
          <label>System
            <input v-model="filters.system" type="text" list="marketscoutSystemSuggestions" />
            <datalist id="marketscoutSystemSuggestions">
              <option v-for="system in systemSuggestions" :key="system" :value="system" />
            </datalist>
          </label>
          <label>Station
            <input v-model="filters.station" type="text" list="marketscoutStationSuggestions" />
            <datalist id="marketscoutStationSuggestions">
              <option v-for="station in stationSuggestions" :key="station" :value="station" />
            </datalist>
          </label>
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
          <div class="stationFilterPrimaryActions">
            <button type="button" class="applyFiltersButton" @click="emit('apply')">Apply Filters</button>
            <button type="button" class="clearFiltersButton" @click="emit('clear-station-filters')">Clear</button>
          </div>
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
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Refresh</button>
    </template>

    <template v-else-if="currentView === 'ledger'">
      <label>Commodity <input v-model="ledgerFilters.commodity" type="text" placeholder="Gold" /></label>
      <label>Trade Type
        <select v-model="ledgerFilters.eventType"><option>Any</option><option>buy</option><option>sell</option></select>
      </label>
      <label class="check"><input v-model="ledgerFilters.showLifo" type="checkbox" /> Show LIFO</label>
      <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>

    <template v-else-if="currentView === 'rare'">
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
      <label>Sort
        <select v-model="commodityFilters.sort">
          <option value="commodity_asc">Commodity asc</option>
          <option value="category_asc">Category asc</option>
          <option value="max_profit_desc">Max Profit desc</option>
        </select>
      </label>
      <button type="button" @click="emit('apply')">Apply</button>
    </template>
    </div>
  </section>
</template>
