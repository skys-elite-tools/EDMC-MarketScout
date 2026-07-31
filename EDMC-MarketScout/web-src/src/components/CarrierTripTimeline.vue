<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  stops: { type: Array, default: () => [] },
  progressStopIndex: { type: Number, default: 0 },
  currentSystem: { type: String, default: '' },
})

const emit = defineEmits(['toggle-skip'])
const normalizedCurrentSystem = computed(() => props.currentSystem.trim().toLocaleLowerCase())
const showPrevious = ref(false)

const routeKey = computed(() => props.stops[0]?.carrier_trip_id || null)

watch(routeKey, () => {
  showPrevious.value = false
})

function number(value, digits = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toLocaleString(undefined, { maximumFractionDigits: digits }) : '—'
}

function systemIsCurrent(stop) {
  return normalizedCurrentSystem.value && stop.system_name?.trim().toLocaleLowerCase() === normalizedCurrentSystem.value
}

function visitedAt(stop) {
  return stop.visited_datetime || stop.last_system_visit_datetime || ''
}

function stopWasVisited(stop) {
  return Boolean(visitedAt(stop))
}

const currentStopIndex = computed(() => {
  const progressStop = props.stops.find(
    stop => stop.stop_index === props.progressStopIndex && systemIsCurrent(stop),
  )
  const currentStop = progressStop || props.stops.find(stop => systemIsCurrent(stop))
  return currentStop?.stop_index ?? props.progressStopIndex
})

const collapsedVisitedStops = computed(() => (
  props.stops.filter(
    stop => stop.stop_index < currentStopIndex.value - 1 && stopWasVisited(stop),
  )
))

const visibleStops = computed(() => {
  if (showPrevious.value || !collapsedVisitedStops.value.length) return props.stops
  const collapsedIds = new Set(collapsedVisitedStops.value.map(stop => stop.stop_index))
  return props.stops.filter(stop => !collapsedIds.has(stop.stop_index))
})

function formatDateTime(value) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <section class="carrierTripTimeline" aria-label="Fleet Carrier route stops">
    <div v-if="!stops.length" class="placeholderBox">Import a Spansh Fleet Carrier route to display its stops.</div>
    <div v-else class="carrierTripTableWrap">
      <table class="carrierTripTable">
        <thead>
          <tr>
            <th>#</th>
            <th class="systemColumn">System</th>
            <th class="bodyColumn">Body</th>
            <th class="num">LY</th>
            <th class="num">Tritium</th>
            <th class="num">Tank</th>
            <th class="notesColumn">Notes</th>
            <th class="visitedColumn">Visited</th>
            <th class="actionCol">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="collapsedVisitedStops.length" class="previousStopsRow">
            <td colspan="9">
              <button type="button" class="showPreviousButton" @click="showPrevious = !showPrevious">
                {{ showPrevious ? 'Hide Previous' : 'Show Previous' }}
                <span>({{ collapsedVisitedStops.length }} visited)</span>
              </button>
            </td>
          </tr>
          <tr
            v-for="stop in visibleStops"
            :key="`${stop.carrier_trip_id}-${stop.stop_index}`"
            :class="{
              current: systemIsCurrent(stop),
              progress: stop.stop_index === progressStopIndex,
              skipped: stop.stop_skipped,
            }"
          >
            <td class="stopIndex">{{ stop.stop_index + 1 }}</td>
            <td class="systemColumn">
              <strong>{{ stop.system_name }}</strong>
              <span v-if="systemIsCurrent(stop)" class="currentBadge">Current</span>
              <span v-if="stop.is_desired_destination" class="destinationBadge">Destination</span>
            </td>
            <td class="bodyColumn">{{ stop.body_name || '—' }}</td>
            <td class="num">{{ number(stop.leg_distance_ly, 1) }}</td>
            <td class="num">{{ number(stop.tritium_used_t) }} t</td>
            <td class="num">{{ number(stop.tritium_in_tank_t) }} t</td>
            <td class="notesColumn">
              <span v-if="stop.must_restock" class="routeFlag restockFlag">Restock<span v-if="stop.restock_amount_t"> {{ number(stop.restock_amount_t) }} t</span></span>
              <span v-if="stop.has_icy_ring" class="routeFlag">Icy ring</span>
              <span v-if="stop.is_system_pristine" class="routeFlag">Pristine</span>
              <span v-if="stop.stop_skipped" class="routeFlag skippedFlag">Skipped</span>
              <span v-if="!stop.must_restock && !stop.has_icy_ring && !stop.is_system_pristine && !stop.stop_skipped">—</span>
            </td>
            <td class="visitedColumn">
              <time
                v-if="visitedAt(stop)"
                :datetime="visitedAt(stop)"
                :title="visitedAt(stop)"
              >{{ formatDateTime(visitedAt(stop)) }}</time>
              <span v-else>—</span>
            </td>
            <td class="actionCol">
              <button type="button" class="smallActionButton" @click="emit('toggle-skip', stop)">
                {{ stop.stop_skipped ? 'Restore' : 'Skip' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.carrierTripTimeline {
  min-width: 0;
}

.carrierTripTableWrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
}

.carrierTripTable {
  min-width: 960px;
  table-layout: fixed;
}

.carrierTripTable .systemColumn {
  width: 18%;
}

.carrierTripTable .bodyColumn {
  width: 12%;
}

.carrierTripTable .notesColumn {
  width: 12%;
}

.carrierTripTable .visitedColumn {
  width: 10rem;
}

.carrierTripTable th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #242c38;
}

.carrierTripTable td {
  vertical-align: middle;
}

.carrierTripTable tr.current td {
  background: rgba(159,240,212,.11);
}

.carrierTripTable tr.progress td {
  border-top: 2px solid var(--accent);
}

.carrierTripTable tr.skipped {
  opacity: .62;
}

.carrierTripTable tr.previousStopsRow td {
  padding: 5px;
  background: rgba(140,200,255,.04);
}

.showPreviousButton {
  width: 100%;
  border-style: dashed;
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
}

.showPreviousButton span {
  color: var(--muted);
  font-weight: 600;
}

.stopIndex {
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}

.carrierTripTable strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--accent2);
}

.currentBadge,
.destinationBadge,
.routeFlag {
  display: inline-block;
  margin: 3px 4px 0 0;
  padding: 1px 5px;
  border: 1px solid rgba(140,200,255,.35);
  border-radius: 999px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 800;
  white-space: nowrap;
}

.currentBadge {
  color: #9ff0d4;
  border-color: rgba(159,240,212,.45);
}

.destinationBadge {
  color: #ffe27a;
  border-color: rgba(255,226,122,.45);
}

.restockFlag {
  color: #ffb36b;
  border-color: rgba(255,179,107,.45);
}

.skippedFlag {
  color: var(--muted);
}

.actionCol {
  width: 5.5rem;
  text-align: center;
}

.visitedColumn {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.visitedColumn time {
  color: var(--text);
  font-size: 11px;
}

.smallActionButton {
  padding: 4px 7px;
  font-size: 11px;
}
</style>
