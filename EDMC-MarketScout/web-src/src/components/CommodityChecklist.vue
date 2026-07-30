<script setup>
import { computed } from 'vue'

const props = defineProps({
  commodities: { type: Array, default: () => [] },
  selectedCommodities: { type: Array, default: () => [] },
  search: { type: String, default: '' },
})
const emit = defineEmits(['update:search', 'toggle-selected'])

const selectedSet = computed(() => new Set(props.selectedCommodities))
const sortedCommodities = computed(() => {
  return [...props.commodities].sort((a, b) => {
    const aSelected = selectedSet.value.has(a) ? 0 : 1
    const bSelected = selectedSet.value.has(b) ? 0 : 1
    if (aSelected !== bSelected) return aSelected - bSelected
    return String(a || '').localeCompare(String(b || ''))
  })
})
</script>

<template>
  <label>
    Filter commodities
    <input
      :value="search"
      type="text"
      placeholder="gold, palladium, osmium..."
      @input="emit('update:search', $event.target.value)"
    />
  </label>
  <div class="commoditySettings">
    <div v-for="commodity in sortedCommodities" :key="commodity" class="commodityRow singleSelect">
      <label>
        <input
          type="checkbox"
          :checked="selectedSet.has(commodity)"
          @change="emit('toggle-selected', commodity, $event.target.checked)"
        />
        {{ commodity }}
      </label>
    </div>
  </div>
</template>
