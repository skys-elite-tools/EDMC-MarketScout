<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  commodities: { type: Array, default: () => [] },
  watchedCommodities: { type: Array, default: () => [] },
  displayColumns: { type: Array, default: () => [] },
  search: { type: String, default: '' },
})
const emit = defineEmits([
  'close',
  'save',
  'update:search',
  'toggle-watched',
  'toggle-display-column',
])

function columnKey(col) { return `${col.commodity}::${col.side}` }
function isColumnSelected(commodity, side) {
  return props.displayColumns.some(c => columnKey(c) === `${commodity}::${side}`)
}
</script>

<template>
  <section v-if="visible" class="settingsPanel">
    <div class="settingsHeader"><h2>Watched commodities</h2><button type="button" @click="emit('close')">Close</button></div>
    <p class="subtitle">Watched commodities drive highlighting/details. Select Buy/Sell columns separately for the table.</p>
    <label>Filter commodities <input :value="search" type="text" placeholder="gold, palladium, osmium…" @input="emit('update:search', $event.target.value)" /></label>
    <div class="commoditySettings">
      <div v-for="commodity in commodities" :key="commodity" class="commodityRow">
        <label><input type="checkbox" :checked="watchedCommodities.includes(commodity)" @change="emit('toggle-watched', commodity, $event.target.checked)" /> {{ commodity }}</label>
        <label><input type="checkbox" :checked="isColumnSelected(commodity, 'buy')" @change="emit('toggle-display-column', commodity, 'buy', $event.target.checked)" /> Buy col</label>
        <label><input type="checkbox" :checked="isColumnSelected(commodity, 'sell')" @change="emit('toggle-display-column', commodity, 'sell', $event.target.checked)" /> Sell col</label>
      </div>
    </div>
    <button type="button" @click="emit('save')">Save commodity settings</button>
  </section>
</template>
