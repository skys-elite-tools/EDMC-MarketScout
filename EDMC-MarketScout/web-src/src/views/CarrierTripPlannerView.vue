<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import CarrierTripImport from '../components/CarrierTripImport.vue'
import CarrierTripSummary from '../components/CarrierTripSummary.vue'
import CarrierTripTimeline from '../components/CarrierTripTimeline.vue'
import ViewHeader from '../components/ViewHeader.vue'
import { useCarrierTripPlannerStore } from '../stores/carrierTripPlannerStore.js'
import { useStatusStore } from '../stores/statusStore.js'

const carrierTripStore = useCarrierTripPlannerStore()
const statusStore = useStatusStore()
const {
  carrierTripRoutes,
  activeCarrierTrip,
  selectedCarrierTripId,
  carrierTripBusy,
  carrierTripStatus,
} = storeToRefs(carrierTripStore)
const { latestJournalEvent } = storeToRefs(statusStore)

const currentSystem = computed(() => latestJournalEvent.value?.system || '')
const liveCarrier = computed(() => {
  const event = latestJournalEvent.value
  if (!event) return null
  const context = event.carrier_context || null
  const hasCarrierData = context?.carrier_id || context?.carrier_name || context?.carrier_callsign || context?.carrier_fuel_t != null
  const carrierEvent = ['CarrierStats', 'CarrierJumpRequest', 'CarrierJump', 'CarrierBuy', 'CarrierSell'].includes(event.event)
  if (!hasCarrierData && !carrierEvent) return null
  return { ...event, ...(context || {}) }
})

const carrierLabel = computed(() => {
  const carrier = liveCarrier.value
  if (!carrier) return '—'
  const name = carrier.carrier_name || 'Carrier'
  return carrier.carrier_callsign ? `${name} [${carrier.carrier_callsign}]` : name
})

const fuelLabel = computed(() => {
  const fuel = liveCarrier.value?.carrier_fuel_t
  return fuel == null ? '—' : `${number(fuel)} t`
})

const routeImportedTime = route => {
  const timestamp = Date.parse(route?.imported_datetime || '')
  return Number.isFinite(timestamp) ? timestamp : 0
}

const activeRoutes = computed(() => (
  carrierTripRoutes.value.filter(route => route.active)
))

const oldestActiveImportTime = computed(() => {
  if (!activeRoutes.value.length) return null
  return Math.min(...activeRoutes.value.map(routeImportedTime))
})

const visibleCarrierRoutes = computed(() => {
  const oldestActive = oldestActiveImportTime.value
  return carrierTripRoutes.value
    .filter(route => route.active || (oldestActive != null && routeImportedTime(route) > oldestActive))
    .sort((left, right) => {
      if (Boolean(left.active) !== Boolean(right.active)) return left.active ? -1 : 1
      return routeImportedTime(right) - routeImportedTime(left)
    })
})

const archivedCarrierRoutes = computed(() => {
  const visibleIds = new Set(visibleCarrierRoutes.value.map(route => route.carrier_trip_id))
  return carrierTripRoutes.value
    .filter(route => !visibleIds.has(route.carrier_trip_id))
    .sort((left, right) => routeImportedTime(right) - routeImportedTime(left))
})

function number(value, digits = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toLocaleString(undefined, { maximumFractionDigits: digits }) : '—'
}

async function importRoute(file) {
  await carrierTripStore.importCarrierTrip(file)
}

async function startRoute(route) {
  await carrierTripStore.startCarrierTrip(route.carrier_trip_id)
}

async function stopRoute(route) {
  await carrierTripStore.stopCarrierTrip(route.carrier_trip_id)
}

function viewRoute(route) {
  carrierTripStore.selectCarrierTrip(route.carrier_trip_id)
}

async function toggleSkip(stop) {
  await carrierTripStore.setStopSkipped({
    carrier_trip_id: stop.carrier_trip_id,
    stop_index: stop.stop_index,
    skipped: !stop.stop_skipped,
  })
}

async function deleteRoute(route) {
  if (!window.confirm(`Delete the imported route “${route.route_name}”?`)) return
  await carrierTripStore.deleteCarrierTrip(route.carrier_trip_id)
}

onMounted(async () => {
  try {
    await carrierTripStore.loadCarrierTrips()
  } catch (err) {
    carrierTripStatus.value = err?.message || String(err)
  }
})
</script>

<template>
  <section class="viewControls">
    <ViewHeader />
  </section>

  <div class="carrierTripPlannerView">
    <div class="carrierTripTopGrid">
      <section class="carrierTripsPanel" aria-labelledby="carrier-trip-import-title">
        <CarrierTripImport :busy="carrierTripBusy" @import="importRoute" />

        <div v-if="!carrierTripRoutes.length" class="placeholderBox">No Fleet Carrier routes imported yet.</div>
        <div v-else class="carrierTripRouteList">
          <div
            v-for="route in visibleCarrierRoutes"
            :key="route.carrier_trip_id"
            class="carrierTripRouteItem"
            :class="{ active: route.active, selected: route.carrier_trip_id === selectedCarrierTripId }"
          >
            <div class="carrierTripRouteIdentity">
              <strong>{{ route.route_name }}</strong>
              <span>{{ route.stop_count }} stops · {{ number(route.total_distance_ly, 1) }} LY · {{ number(route.total_tritium_t) }} t tritium</span>
            </div>
            <div class="carrierTripRouteActions">
              <span v-if="route.active" class="activeRouteBadge">Active</span>
              <button v-if="route.active && route.carrier_trip_id !== selectedCarrierTripId" type="button" :disabled="carrierTripBusy" @click="viewRoute(route)">View</button>
              <span v-if="route.active && route.carrier_trip_id === selectedCarrierTripId" class="viewingRouteBadge">Viewing</span>
              <button v-if="route.active" type="button" :disabled="carrierTripBusy" @click="stopRoute(route)">Pause</button>
              <button v-else type="button" :disabled="carrierTripBusy" @click="startRoute(route)">Track</button>
              <button type="button" class="dangerButton" :disabled="carrierTripBusy" title="Delete imported route" @click="deleteRoute(route)">Delete</button>
            </div>
          </div>
        </div>

        <details v-if="archivedCarrierRoutes.length" class="archivedCarrierTrips">
          <summary>Older imported routes ({{ archivedCarrierRoutes.length }})</summary>
          <div class="carrierTripRouteList">
            <div v-for="route in archivedCarrierRoutes" :key="route.carrier_trip_id" class="carrierTripRouteItem">
              <div class="carrierTripRouteIdentity">
                <strong>{{ route.route_name }}</strong>
                <span>{{ route.stop_count }} stops · {{ number(route.total_distance_ly, 1) }} LY · {{ number(route.total_tritium_t) }} t tritium</span>
              </div>
              <div class="carrierTripRouteActions">
                <button type="button" :disabled="carrierTripBusy" @click="startRoute(route)">Track</button>
                <button type="button" class="dangerButton" :disabled="carrierTripBusy" title="Delete imported route" @click="deleteRoute(route)">Delete</button>
              </div>
            </div>
          </div>
        </details>
      </section>

      <section class="carrierLivePanel" aria-labelledby="carrier-live-title">
        <div class="carrierTripPanelHeader">
          <div>
            <h2 id="carrier-live-title">Live Journal</h2>
            <p>Values appear when EDMC receives a relevant Journal event.</p>
          </div>
        </div>
        <div class="carrierLiveGrid">
          <div><span>Commander</span><strong>{{ liveCarrier?.commander_name || '—' }}</strong></div>
          <div><span>Carrier</span><strong>{{ carrierLabel }}</strong></div>
          <div><span>Fuel level</span><strong>{{ fuelLabel }}</strong></div>
          <div><span>Body</span><strong>{{ liveCarrier?.body || '—' }}</strong></div>
        </div>
      </section>

      <CarrierTripSummary :route="activeCarrierTrip" />
    </div>

    <p v-if="carrierTripStatus" class="carrierTripStatus" role="status">{{ carrierTripStatus }}</p>

    <section v-if="activeCarrierTrip" class="carrierTripStopsPanel" aria-labelledby="carrier-trip-stops-title">
      <div class="carrierTripPanelHeader">
        <div>
          <h2 id="carrier-trip-stops-title">Route Stops</h2>
          <p>Distance and tritium values are imported from Spansh. The current system is read from the Journal.</p>
        </div>
        <span class="progressLabel">Progress {{ Math.min((activeCarrierTrip.progress_stop_index || 0) + 1, activeCarrierTrip.stop_count) }} / {{ activeCarrierTrip.stop_count }}</span>
      </div>
      <CarrierTripTimeline
        :stops="activeCarrierTrip.stops"
        :progress-stop-index="activeCarrierTrip.progress_stop_index || 0"
        :current-system="currentSystem"
        @toggle-skip="toggleSkip"
      />
    </section>
  </div>
</template>

<style scoped>
.carrierTripPlannerView {
  display: grid;
  gap: 12px;
  padding: 12px 16px 18px;
}

.carrierTripTopGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: stretch;
  gap: 12px;
}

.carrierTripStatus {
  margin: 0;
  color: var(--accent);
  font-size: 12px;
}

.carrierTripsPanel,
.carrierLivePanel,
.carrierTripStopsPanel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,.025);
}

.carrierTripsPanel,
.carrierLivePanel {
  min-width: 0;
}

.carrierTripPanelHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.carrierTripPanelHeader h2 {
  margin: 0;
  color: var(--accent2);
  font-size: 15px;
}

.carrierTripPanelHeader p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.routeCount,
.progressLabel {
  flex: none;
  color: var(--accent);
  border: 1px solid rgba(140,200,255,.35);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 800;
}

.carrierTripRouteList {
  display: grid;
  gap: 6px;
}

.carrierTripRouteItem {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 8px;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 4px;
}

.carrierTripRouteItem.active {
  border-color: rgba(159,240,212,.5);
  background: rgba(159,240,212,.07);
}

.carrierTripRouteItem.selected {
  box-shadow: inset 0 0 0 1px rgba(140,200,255,.35);
}

.carrierTripRouteIdentity {
  min-width: 0;
}

.carrierTripRouteIdentity strong,
.carrierTripRouteIdentity span {
  display: block;
}

.carrierTripRouteIdentity strong {
  color: var(--accent2);
}

.carrierTripRouteIdentity span {
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
}

.carrierTripRouteActions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  flex: none;
  justify-content: flex-end;
  gap: 6px;
}

.activeRouteBadge {
  color: #9ff0d4;
  font-size: 11px;
  font-weight: 800;
}

.viewingRouteBadge {
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
}

.archivedCarrierTrips {
  margin-top: 2px;
  border-top: 1px solid rgba(255,255,255,.08);
  padding-top: 8px;
}

.archivedCarrierTrips summary {
  color: var(--muted);
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.archivedCarrierTrips[open] summary {
  margin-bottom: 8px;
}

.dangerButton:hover {
  border-color: #ff9f9f;
  color: #ffb3b3;
}

.carrierLiveGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.carrierLiveGrid div {
  min-width: 0;
  padding: 7px;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 4px;
}

.carrierLiveGrid span,
.carrierLiveGrid strong {
  display: block;
}

.carrierLiveGrid span {
  color: var(--muted);
  font-size: 11px;
}

.carrierLiveGrid strong {
  overflow: hidden;
  margin-top: 3px;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-size: 13px;
}

@media (max-width: 1000px) {
  .carrierTripTopGrid {
    grid-template-columns: 1fr;
  }

  .carrierLiveGrid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .carrierTripRouteItem,
  .carrierTripPanelHeader {
    align-items: stretch;
    flex-direction: column;
  }

  .carrierTripRouteActions {
    justify-content: flex-end;
  }

  .carrierLiveGrid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
