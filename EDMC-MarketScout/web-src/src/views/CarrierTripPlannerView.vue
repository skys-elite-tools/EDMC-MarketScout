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
    <CarrierTripImport :busy="carrierTripBusy" @import="importRoute" />

    <p v-if="carrierTripStatus" class="carrierTripStatus" role="status">{{ carrierTripStatus }}</p>

    <section class="carrierTripRoutesPanel" aria-labelledby="carrier-trip-routes-title">
      <div class="carrierTripPanelHeader">
        <div>
          <h2 id="carrier-trip-routes-title">Imported Carrier Trips</h2>
          <p>Only one carrier route is tracked as active. Imported routes remain available here for later use.</p>
        </div>
        <span class="routeCount">{{ carrierTripRoutes.length }}</span>
      </div>

      <div v-if="!carrierTripRoutes.length" class="placeholderBox">No Fleet Carrier routes imported yet.</div>
      <div v-else class="carrierTripRouteList">
        <div v-for="route in carrierTripRoutes" :key="route.carrier_trip_id" class="carrierTripRouteItem" :class="{ active: route.active }">
          <div class="carrierTripRouteIdentity">
            <strong>{{ route.route_name }}</strong>
            <span>{{ route.stop_count }} stops · {{ number(route.total_distance_ly, 1) }} LY · {{ number(route.total_tritium_t) }} t tritium</span>
          </div>
          <div class="carrierTripRouteActions">
            <span v-if="route.active" class="activeRouteBadge">Active</span>
            <button v-else type="button" :disabled="carrierTripBusy" @click="startRoute(route)">Track</button>
            <button type="button" class="dangerButton" :disabled="carrierTripBusy" title="Delete imported route" @click="deleteRoute(route)">Delete</button>
          </div>
        </div>
      </div>
    </section>

    <section v-if="liveCarrier" class="carrierLivePanel" aria-labelledby="carrier-live-title">
      <div class="carrierTripPanelHeader">
        <div>
          <h2 id="carrier-live-title">Live Journal Context</h2>
          <p>Values appear when EDMC receives a relevant Journal event.</p>
        </div>
        <span class="liveEventBadge">{{ liveCarrier.event }}</span>
      </div>
      <div class="carrierLiveGrid">
        <div><span>Commander</span><strong>{{ liveCarrier.commander_name || '—' }}</strong></div>
        <div><span>Commander ID</span><strong>{{ liveCarrier.commander_id || '—' }}</strong></div>
        <div><span>Carrier</span><strong>{{ liveCarrier.carrier_name || liveCarrier.carrier_callsign || '—' }}</strong></div>
        <div><span>Carrier ID</span><strong>{{ liveCarrier.carrier_id || '—' }}</strong></div>
        <div><span>Fuel level</span><strong>{{ liveCarrier.carrier_fuel_t == null ? '—' : `${number(liveCarrier.carrier_fuel_t)} t` }}</strong></div>
        <div><span>Body</span><strong>{{ liveCarrier.body || '—' }}</strong></div>
      </div>
    </section>

    <CarrierTripSummary :route="activeCarrierTrip" />

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

.carrierTripStatus {
  margin: 0;
  color: var(--accent);
  font-size: 12px;
}

.carrierTripRoutesPanel,
.carrierLivePanel,
.carrierTripStopsPanel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,.025);
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
.progressLabel,
.liveEventBadge {
  flex: none;
  color: var(--accent);
  border: 1px solid rgba(140,200,255,.35);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 800;
}

.liveEventBadge {
  color: #9ff0d4;
  border-color: rgba(159,240,212,.4);
}

.carrierTripRouteList {
  display: grid;
  gap: 6px;
}

.carrierTripRouteItem {
  display: flex;
  align-items: center;
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
  flex: none;
  gap: 6px;
}

.activeRouteBadge {
  color: #9ff0d4;
  font-size: 11px;
  font-weight: 800;
}

.dangerButton:hover {
  border-color: #ff9f9f;
  color: #ffb3b3;
}

.carrierLiveGrid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
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
  .carrierLiveGrid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
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
