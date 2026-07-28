<script setup>
import { computed } from 'vue'
import { shortTime } from '../utils.js'

const props = defineProps({
  statusText: { type: String, default: '' },
  latestJournalEvent: { type: Object, default: null },
  edmcStatus: { type: Object, default: null },
  autoRefresh: { type: Boolean, default: true },
  updateStatus: { type: Object, default: null },
  updateBusy: { type: Boolean, default: false },
  edmcDiscardBusy: { type: Boolean, default: false },
})
const emit = defineEmits(['update:autoRefresh', 'run-update', 'discard-edmc-delayed', 'open-support'])

const journalLabel = computed(() => {
  const event = props.latestJournalEvent || null
  if (!event || !event.event) return 'No Journal event received yet'
  const parts = [`${shortTime(event.timestamp)} · ${event.event}`]
  if (event.system) parts.push(event.system)
  if (event.station) parts.push(event.station)
  return parts.filter(Boolean).join(' · ')
})

const updateLabel = computed(() => {
  if (props.updateBusy) return 'Updating MarketScout...'
  return props.updateStatus?.can_update
    ? 'Update Available: Click Here to Update'
    : 'Update Available: Click Here to Download'
})

const delayedMessages = computed(() => (
  Array.isArray(props.edmcStatus?.delayed_station_messages)
    ? props.edmcStatus.delayed_station_messages
    : []
))

function delayedMessagePlace(message) {
  if (!message) return 'Station data'
  if (message.station_name && message.system_name) return `${message.station_name} / ${message.system_name}`
  return message.station_name || message.system_name || 'Station data'
}

const delayedMessagesTitle = computed(() => {
  if (!delayedMessages.value.length) return 'Delayed EDDN station messages waiting to be sent.'
  return delayedMessages.value
    .map((message) => `${delayedMessagePlace(message)} · ~${Number(message.seconds_remaining || 0)}s`)
    .join('\n')
})

const firstDelayedMessageLabel = computed(() => {
  const message = delayedMessages.value[0]
  if (!message) return ''
  return `${delayedMessagePlace(message)} · ~${Number(message.seconds_remaining || 0)}s`
})
</script>

<template>
  <section class="statusStrip" aria-label="MarketScout status">
    <div class="journalStatus" :title="journalLabel">
      <span class="statusLabel">Journal</span>
      <span class="statusValue">{{ journalLabel }}</span>
    </div>
    <div v-if="updateStatus?.available" class="updateStatusSlot">
      <button
        class="updateAvailableButton"
        type="button"
        :disabled="updateBusy"
        @click="emit('run-update')"
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
          @change="emit('update:autoRefresh', $event.target.checked)"
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
