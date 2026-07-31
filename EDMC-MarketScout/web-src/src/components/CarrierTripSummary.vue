<script setup>
import { computed } from 'vue'

const props = defineProps({
  route: { type: Object, default: null },
})

const destinations = computed(() => (
  Array.isArray(props.route?.destination_systems)
    ? props.route.destination_systems.map(item => item?.system_name).filter(Boolean)
    : []
))

function number(value, digits = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toLocaleString(undefined, { maximumFractionDigits: digits }) : '—'
}
</script>

<template>
  <section v-if="route" class="carrierTripSummary" aria-label="Carrier route summary">
    <div class="carrierTripSummaryHeading">
      <div>
        <h2>{{ route.route_name }}</h2>
        <p>
          {{ route.stop_count || 0 }} stops
          <span v-if="destinations.length"> · {{ destinations.join(' → ') }}</span>
        </p>
      </div>
      <span class="carrierTripSource">{{ route.source === 'spansh_carrier_json' ? 'Spansh JSON' : 'Spansh CSV' }}</span>
    </div>

    <div class="carrierTripMetrics">
      <div><span>Distance</span><strong>{{ number(route.total_distance_ly, 1) }} LY</strong></div>
      <div><span>Tritium required</span><strong>{{ number(route.total_tritium_t) }} t</strong></div>
      <div><span>Carrier mass</span><strong>{{ number(route.carrier_mass) }} t</strong></div>
      <div><span>Capacity used</span><strong>{{ number(route.capacity_used) }} t</strong></div>
      <div><span>Starting fuel</span><strong>{{ number(route.starting_fuel_t) }} t</strong></div>
      <div><span>Starting tritium</span><strong>{{ number(route.starting_tritium_t) }} t</strong></div>
    </div>
  </section>
</template>

<style scoped>
.carrierTripSummary {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(140,200,255,.04);
}

.carrierTripSummaryHeading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.carrierTripSummary h2 {
  margin: 0;
  color: var(--accent2);
  font-size: 18px;
}

.carrierTripSummary p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.carrierTripSource {
  flex: none;
  color: var(--accent);
  border: 1px solid rgba(140,200,255,.35);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 800;
}

.carrierTripMetrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}

.carrierTripMetrics div {
  min-width: 0;
  padding: 8px;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 4px;
  background: rgba(255,255,255,.025);
}

.carrierTripMetrics span,
.carrierTripMetrics strong {
  display: block;
}

.carrierTripMetrics span {
  color: var(--muted);
  font-size: 11px;
}

.carrierTripMetrics strong {
  margin-top: 4px;
  color: var(--text);
  font-size: 14px;
}

@media (max-width: 900px) {
  .carrierTripMetrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .carrierTripSummaryHeading {
    flex-direction: column;
  }

  .carrierTripMetrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
