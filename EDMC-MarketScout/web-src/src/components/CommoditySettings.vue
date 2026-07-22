<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: 'Watched commodities' },
  description: { type: String, default: 'Watched commodities drive highlighting/details. Select Buy/Sell columns separately for the table.' },
  saveLabel: { type: String, default: 'Save commodity settings' },
  commodities: { type: Array, default: () => [] },
  selectedCommodities: { type: Array, default: () => [] },
  displayColumns: { type: Array, default: () => [] },
  search: { type: String, default: '' },
  showDisplayColumns: { type: Boolean, default: true },
  showBestBuySettings: { type: Boolean, default: false },
  bestBuySupplyCap: { type: Number, default: 1000 },
  minimumPotentialProfit: { type: Number, default: 10000 },
})
const emit = defineEmits([
  'close',
  'save',
  'update:search',
  'update:bestBuySupplyCap',
  'update:minimumPotentialProfit',
  'toggle-selected',
  'toggle-display-column',
])

const selectedSet = computed(() => new Set(props.selectedCommodities))
const sortedCommodities = computed(() => {
  return [...props.commodities].sort((a, b) => {
    const aSelected = selectedSet.value.has(a) ? 0 : 1
    const bSelected = selectedSet.value.has(b) ? 0 : 1
    if (aSelected !== bSelected) return aSelected - bSelected
    return String(a || '').localeCompare(String(b || ''))
  })
})

function columnKey(col) { return `${col.commodity}::${col.side}` }
function isColumnSelected(commodity, side) {
  return props.displayColumns.some(c => columnKey(c) === `${commodity}::${side}`)
}
</script>

<template>
  <section v-if="visible" class="settingsPanel">
    <div class="settingsHeader"><h2>{{ title }}</h2><button type="button" @click="emit('close')">Close</button></div>
    <p class="subtitle">{{ description }}</p>
    <div v-if="showBestBuySettings" class="bestBuySettingsGrid">
      <label title="Best Buy score uses min(supply, this value), so very large supply does not dominate every result.">
        Best Buy supply cap
        <input
          :value="bestBuySupplyCap"
          type="number"
          min="1"
          step="1"
          @input="emit('update:bestBuySupplyCap', Number($event.target.value || 1000))"
        />
      </label>
      <label title="Best Buy candidates and Potential Profit links are shown only when profit per tonne is at least this value.">
        Minimum potential profit
        <input
          :value="minimumPotentialProfit"
          type="number"
          min="0"
          step="100"
          @input="emit('update:minimumPotentialProfit', Number($event.target.value || 0))"
        />
      </label>
    </div>
    <h3 v-if="showBestBuySettings" class="settingsSubheading">Best Buy Ignore List</h3>
    <label>Filter commodities <input :value="search" type="text" placeholder="gold, palladium, osmium..." @input="emit('update:search', $event.target.value)" /></label>
    <div class="commoditySettings">
      <div v-for="commodity in sortedCommodities" :key="commodity" class="commodityRow" :class="{ singleSelect: !showDisplayColumns }">
        <label><input type="checkbox" :checked="selectedSet.has(commodity)" @change="emit('toggle-selected', commodity, $event.target.checked)" /> {{ commodity }}</label>
        <label v-if="showDisplayColumns"><input type="checkbox" :checked="isColumnSelected(commodity, 'buy')" @change="emit('toggle-display-column', commodity, 'buy', $event.target.checked)" /> Buy col</label>
        <label v-if="showDisplayColumns"><input type="checkbox" :checked="isColumnSelected(commodity, 'sell')" @change="emit('toggle-display-column', commodity, 'sell', $event.target.checked)" /> Sell col</label>
      </div>
    </div>
    <button type="button" @click="emit('save')">{{ saveLabel }}</button>
  </section>
</template>
