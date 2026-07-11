<script setup>
import { computed } from 'vue'
import { shortTime } from '../utils.js'

const props = defineProps({
  statusText: { type: String, default: '' },
  latestJournalEvent: { type: Object, default: null },
  autoRefresh: { type: Boolean, default: true },
})
const emit = defineEmits(['update:autoRefresh'])

const journalLabel = computed(() => {
  const event = props.latestJournalEvent || null
  if (!event || !event.event) return 'No Journal event received yet'
  const parts = [`${shortTime(event.timestamp)} · ${event.event}`]
  if (event.system) parts.push(event.system)
  if (event.station) parts.push(event.station)
  return parts.filter(Boolean).join(' · ')
})
</script>

<template>
  <section class="statusStrip" aria-label="MarketScout status">
    <div class="journalStatus" :title="journalLabel">
      <span class="statusLabel">Journal</span>
      <span class="statusValue">{{ journalLabel }}</span>
    </div>
    <div class="viewStatus">
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
