<script setup>
defineProps({
  filters: { type: Object, required: true },
})
const emit = defineEmits(['apply'])
</script>

<template>
  <div class="viewControlsBody">
    <label>Sort
      <select v-model="filters.sort">
        <option value="profit_desc">Profit large to small</option>
        <option value="usual_supply_desc">Usual Supply, high to low</option>
      </select>
    </label>
    <label class="check"><input v-model="filters.engineeringOnly" type="checkbox" /> Show only engineering rare commodities</label>
    <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
    <button type="button" @click="emit('apply')">Apply</button>
  </div>
</template>
