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

<style scoped>
.metricCard {
  display: grid;
  gap: 4px;
  align-content: start;
  min-height: 5.2rem;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  background: rgba(255,255,255,.025);
}

.metricCard span {
  color: var(--muted);
  font-size: 12px;
}

.metricCard strong {
  color: var(--text);
  font-size: 22px;
  line-height: 1.1;
}

.metricCard small {
  color: var(--accent);
  font-size: 12px;
}

.metricCard.wide {
  grid-column: span 2;
}

.metricCard.carrierMetric {
  border-color: rgba(159, 240, 212, .35);
  background: rgba(159, 240, 212, .055);
}

.metricCard.carrierMetric strong {
  color: #9ff0d4;
}

@media (max-width: 1100px) {
  .metricCard.wide {
    grid-column: auto;
  }
}
</style>
