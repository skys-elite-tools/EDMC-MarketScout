<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  title: { type: String, default: '' },
  wide: { type: Boolean, default: false },
  carrier: { type: Boolean, default: false },
  inlineDetails: { type: Boolean, default: false },
})
</script>

<template>
  <div class="metricCard" :class="{ wide, carrierMetric: carrier, inlineDetails }" :title="title || undefined">
    <span class="metricLabel">
      <span>{{ label }}</span>
      <span v-if="$slots.headerRight" class="metricHeaderRight">
        <slot name="headerRight"></slot>
      </span>
    </span>
    <strong>{{ value }}</strong>
    <small v-if="unit">{{ unit }}</small>
    <div v-if="$slots.default" class="metricDetails">
      <slot></slot>
    </div>
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

.metricLabel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  color: var(--muted);
  font-size: 12px;
}

.metricLabel > span:first-child {
  min-width: 0;
}

.metricHeaderRight {
  flex: 0 0 auto;
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

.metricDetails {
  min-width: 0;
}

.metricCard.inlineDetails {
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "label label"
    "value details"
    "unit details";
  column-gap: 12px;
  row-gap: 2px;
  align-items: start;
  min-height: 0;
}

.metricCard.inlineDetails > .metricLabel {
  grid-area: label;
}

.metricCard.inlineDetails > strong {
  grid-area: value;
}

.metricCard.inlineDetails > small {
  grid-area: unit;
}

.metricCard.inlineDetails > .metricDetails {
  grid-area: details;
  align-self: start;
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
