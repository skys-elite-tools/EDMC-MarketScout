<script setup>
import { storeToRefs } from 'pinia'
import { useNotificationStore } from '../stores/notificationStore.js'

const notificationStore = useNotificationStore()
const {
  targetStateToast,
  targetStateDetailsOpen,
  targetStateToastCountdownKey,
} = storeToRefs(notificationStore)

function formatTargetStateTimestamp(value) {
  if (!value) return ''
  const time = Date.parse(value)
  if (!Number.isFinite(time)) return String(value)
  return new Date(time).toLocaleString()
}

function formatInfluence(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return ''
  return `${(number * 100).toFixed(1)}%`
}

function targetStateStationSummary(station) {
  const parts = [station.station_type, station.largest_pad ? `${station.largest_pad}-Pad` : ''].filter(Boolean)
  return parts.join(' · ')
}
</script>

<template>
  <section
    v-if="targetStateToast"
    class="targetStateToast"
    :class="{ targetStateToastPending: targetStateToast.tone === 'pending', targetStateToastOpen: targetStateDetailsOpen }"
    :title="targetStateToast.faction_names?.length ? targetStateToast.faction_names.join(', ') : targetStateToast.message"
    role="button"
    tabindex="0"
    @click="notificationStore.openTargetStateDetails"
    @keydown.enter.prevent="notificationStore.openTargetStateDetails"
    @keydown.space.prevent="notificationStore.openTargetStateDetails"
    @mouseenter="notificationStore.resetTargetStateToastTimer"
  >
    <div class="targetStateToastSummary">
      <strong>{{ targetStateToast.state }}</strong>
      <span>{{ targetStateToast.message }}</span>
      <small>{{ targetStateDetailsOpen ? 'Details open' : 'Click for details' }}</small>
      <button
        type="button"
        class="targetStateToastClose"
        aria-label="Dismiss target state alert"
        title="Dismiss"
        @click.stop="notificationStore.dismissTargetStateToast"
      >x</button>
    </div>
    <div v-if="targetStateDetailsOpen" class="targetStateToastDetails" @click.stop>
      <div class="targetStateToastDetailBlock">
        <h3>Detected Factions</h3>
        <ul>
          <li v-for="detection in targetStateToast.detections || []" :key="`${detection.state_kind}-${detection.faction_name}-${detection.updated_at}`">
            <strong>{{ detection.faction_name }}</strong>
            <span>{{ detection.state_kind === 'pending' ? 'Pending' : 'Active' }}</span>
            <span v-if="formatInfluence(detection.influence)">{{ formatInfluence(detection.influence) }}</span>
            <span v-if="formatTargetStateTimestamp(detection.updated_at)">{{ formatTargetStateTimestamp(detection.updated_at) }}</span>
          </li>
        </ul>
      </div>
      <div class="targetStateToastDetailBlock">
        <h3>Known Stations</h3>
        <ul v-if="targetStateToast.stations?.length">
          <li v-for="station in targetStateToast.stations" :key="`${station.station_faction_name}-${station.station_name}`">
            <strong>{{ station.station_name }}</strong>
            <span>{{ station.station_faction_name }}</span>
            <span v-if="targetStateStationSummary(station)">{{ targetStateStationSummary(station) }}</span>
            <span v-if="formatTargetStateTimestamp(station.last_station_visit_datetime)">Visited {{ formatTargetStateTimestamp(station.last_station_visit_datetime) }}</span>
          </li>
        </ul>
        <p v-else>No known stations owned by the detected faction in this system.</p>
        <p v-if="targetStateToast.station_ownership_note" class="targetStateToastNote">Station ownership is based on previously recorded MarketScout data and may have changed.</p>
      </div>
    </div>
    <span :key="targetStateToastCountdownKey" class="targetStateToastCountdown" aria-hidden="true"></span>
  </section>
</template>
