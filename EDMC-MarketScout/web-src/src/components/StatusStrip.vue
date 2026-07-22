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
})
const emit = defineEmits(['update:autoRefresh', 'run-update'])

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
      <span>{{ statusText }}</span>
      <label>
        <input
          type="checkbox"
          :checked="autoRefresh"
          @change="emit('update:autoRefresh', $event.target.checked)"
        />
        Auto-refresh
      </label>
    </div>
  </section>
</template>
