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
        <option value="commodity_asc">Commodity asc</option>
        <option value="category_asc">Category asc</option>
        <option value="max_profit_desc">Max Profit desc</option>
      </select>
    </label>
    <button type="button" @click="emit('apply')">Apply</button>
  </div>
</template>
