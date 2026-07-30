<script setup>
defineProps({
  filters: { type: Object, required: true },
})
const emit = defineEmits(['apply'])
</script>

<template>
  <div class="viewControlsBody">
    <label>Limit <input v-model.number="filters.limit" type="number" min="1" max="2000" /></label>
    <button type="button" @click="emit('apply')">Refresh</button>
  </div>
</template>
