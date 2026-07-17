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
})
const emit = defineEmits([
  'close',
  'save',
  'update:search',
  'toggle-selected',
  'toggle-display-column',
])

const selectedSet = computed(() => new Set(props.selectedCommodities))

function columnKey(col) { return `${col.commodity}::${col.side}` }
function isColumnSelected(commodity, side) {
  return props.displayColumns.some(c => columnKey(c) === `${commodity}::${side}`)
}
</script>

<template>
  <section v-if="visible" class="settingsPanel">
    <div class="settingsHeader"><h2>{{ title }}</h2><button type="button" @click="emit('close')">Close</button></div>
    <p class="subtitle">{{ description }}</p>
    <label>Filter commodities <input :value="search" type="text" placeholder="gold, palladium, osmium..." @input="emit('update:search', $event.target.value)" /></label>
    <div class="commoditySettings">
      <div v-for="commodity in commodities" :key="commodity" class="commodityRow" :class="{ singleSelect: !showDisplayColumns }">
        <label><input type="checkbox" :checked="selectedSet.has(commodity)" @change="emit('toggle-selected', commodity, $event.target.checked)" /> {{ commodity }}</label>
        <label v-if="showDisplayColumns"><input type="checkbox" :checked="isColumnSelected(commodity, 'buy')" @change="emit('toggle-display-column', commodity, 'buy', $event.target.checked)" /> Buy col</label>
        <label v-if="showDisplayColumns"><input type="checkbox" :checked="isColumnSelected(commodity, 'sell')" @change="emit('toggle-display-column', commodity, 'sell', $event.target.checked)" /> Sell col</label>
      </div>
    </div>
    <button type="button" @click="emit('save')">{{ saveLabel }}</button>
  </section>
</template>
