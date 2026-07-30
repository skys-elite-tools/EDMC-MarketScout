<script setup>
defineProps({
  filters: { type: Object, required: true },
})
const emit = defineEmits(['apply'])
</script>

<template>
  <div class="viewControlsBody">
    <label>Commodity <input v-model="filters.commodity" type="text" placeholder="Gold" /></label>
    <label>Trade Type
      <select v-model="filters.eventType"><option>Any</option><option>buy</option><option>sell</option></select>
    </label>
    <label class="check"><input v-model="filters.showLifo" type="checkbox" /> Show LIFO</label>
    <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
    <button type="button" @click="emit('apply')">Apply</button>
  </div>
</template>
