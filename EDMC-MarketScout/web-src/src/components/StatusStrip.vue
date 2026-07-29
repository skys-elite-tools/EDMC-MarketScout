<script setup>
import { storeToRefs } from 'pinia'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useStatusStore } from '../stores/statusStore.js'
import { useSystemStore } from '../stores/systemStore.js'
import { shortTime } from '../utils.js'

const props = defineProps({
  busyText: { type: String, default: '' },
})
const emit = defineEmits(['run-update', 'discard-edmc-delayed', 'open-support'])
const statusStore = useStatusStore()
const {
  autoRefresh,
  statusText,
  latestJournalEvent,
  edmcStatus,
  updateStatus,
  updateBusy,
  edmcDiscardBusy,
} = storeToRefs(statusStore)

const systemStore = useSystemStore()

const displayedBusyText = ref('')
let busyTextTimer = null

function clearBusyTextTimer() {
  if (!busyTextTimer) return
  clearTimeout(busyTextTimer)
  busyTextTimer = null
}

watch(
  () => props.busyText,
  (busyText) => {
    clearBusyTextTimer()
    if (!busyText) {
      displayedBusyText.value = ''
      return
    }
    if (displayedBusyText.value) {
      displayedBusyText.value = busyText
      return
    }
    busyTextTimer = setTimeout(() => {
      if (props.busyText) displayedBusyText.value = props.busyText
      busyTextTimer = null
    }, 1000)
  },
  { immediate: true },
)

onBeforeUnmount(clearBusyTextTimer)

const journalLabel = computed(() => {
  const event = latestJournalEvent.value || null
  if (!event || !event.event) return 'No Journal event received yet'
  const parts = [`${shortTime(event.timestamp)} · ${event.event}`]
  if (event.system) parts.push(event.system)
  if (event.station) parts.push(event.station)
  return parts.filter(Boolean).join(' · ')
})

const updateLabel = computed(() => {
  if (updateBusy.value) return 'Updating MarketScout...'
  return updateStatus.value?.can_update
    ? 'Update Available: Click Here to Update'
    : 'Update Available: Click Here to Download'
})

const delayedMessages = computed(() => (
  Array.isArray(edmcStatus.value?.delayed_station_messages)
    ? edmcStatus.value.delayed_station_messages
    : []
))

function delayedMessagePlace(message) {
  if (!message) return 'Station data'
  if (message.station_name && message.system_name) return `${message.station_name} / ${message.system_name}`
  return message.station_name || message.system_name || 'Station data'
}

function delayedMessageSchema(message) {
  return message?.schema_name || 'station'
}

function delayedMessageShortLabel(message) {
  return delayedMessageSchema(message)
}

const delayedMessagesTitle = computed(() => {
  if (!delayedMessages.value.length) return 'Delayed EDDN station messages waiting to be sent.'
  return delayedMessages.value
    .map((message) => `${delayedMessageSchema(message)} · ${delayedMessagePlace(message)} · ~${Number(message.seconds_remaining || 0)}s`)
    .join('\n')
})

const firstDelayedMessageLabel = computed(() => {
  const message = delayedMessages.value[0]
  if (!message) return ''
  return `${delayedMessageShortLabel(message)} · ~${Number(message.seconds_remaining || 0)}s`
})
</script>

<template>
  <section class="statusStrip" aria-label="MarketScout status">
    <div class="journalStatus" :title="journalLabel">
      <span class="statusLabel">Journal</span>
      <span class="statusValue">{{ journalLabel }}</span>
      <span v-if="displayedBusyText" class="topBusyStatus" :title="displayedBusyText">
        <span class="stationTableBusyIndicator"></span>
        <span>{{ displayedBusyText }}</span>
      </span>
    </div>
    <div v-if="updateStatus?.available" class="updateStatusSlot">
      <button
        class="updateAvailableButton"
        type="button"
        :disabled="updateBusy"
        @click="systemStore.handleUpdateAction()"
      >
        {{ updateLabel }}
      </button>
    </div>
    <div class="viewStatus">
      <span
        v-if="edmcStatus"
        class="edmcSettingStatus"
        :title="edmcStatus.detail || 'EDMC EDDN station-data setting'"
      >
        {{ edmcStatus.label || 'EDDN Station: Unknown' }}
      </span>
      <span
        v-if="firstDelayedMessageLabel"
        class="edmcDelayQueueStatus"
        :title="delayedMessagesTitle"
      >
        {{ firstDelayedMessageLabel }}
      </span>
      <button
        v-if="edmcStatus?.can_discard_delayed_station_messages && Number(edmcStatus?.delayed_station_messages_pending || 0) > 0"
        type="button"
        class="edmcDiscardButton"
        :disabled="edmcDiscardBusy"
        :title="delayedMessagesTitle"
        @click="emit('discard-edmc-delayed')"
      >
        {{ edmcDiscardBusy ? 'Clearing...' : `Clear delayed (${edmcStatus.delayed_station_messages_pending})` }}
      </button>
      <span>{{ statusText }}</span>
      <label>
        <input
          type="checkbox"
          :checked="autoRefresh"
          @change="statusStore.autoRefresh = $event.target.checked"
        />
        Auto-refresh
      </label>
      <button
        type="button"
        class="statusSupportLink"
        title="Support MarketScout development"
        @click="emit('open-support')"
      >
        Support
      </button>
    </div>
  </section>
</template>
