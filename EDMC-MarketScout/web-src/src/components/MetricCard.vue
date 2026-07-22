<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  wide: { type: Boolean, default: false },
  carrier: { type: Boolean, default: false },
})
</script>

<template>
  <div class="metricCard" :class="{ wide, carrierMetric: carrier }">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
    <small v-if="unit">{{ unit }}</small>
  </div>
</template>
