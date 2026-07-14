<script setup>
import { computed, ref } from 'vue'
import { compactDateTime, fmt, localDateTime, money } from '../utils.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
})
const emit = defineEmits(['select'])

const expanded = ref({})

const groups = computed(() => {
  const byId = new Map()
  for (const [index, row] of props.rows.entries()) {
    const key = row.jackpot_id ?? `row-${index}`
    if (!byId.has(key)) byId.set(key, [])
    byId.get(key).push({ ...row, originalIndex: index })
  }
  return Array.from(byId.entries()).map(([id, samples]) => {
    const sorted = [...samples].sort((a, b) => String(b.sample_datetime || '').localeCompare(String(a.sample_datetime || '')))
    const latest = sorted[0] || {}
    const first = sorted[sorted.length - 1] || latest
    const ended = sorted.find(sample => !Number(sample.is_jackpot))
    return { id, samples: sorted, latest, first, ended }
  })
})

function isExpanded(group) {
  return Boolean(expanded.value[group.id])
}

function toggleGroup(group) {
  expanded.value = { ...expanded.value, [group.id]: !isExpanded(group) }
}

function groupStatus(group) {
  return Number(group.latest.is_jackpot) ? 'Active' : 'Ended'
}

function sampleCountLabel(group) {
  const count = group.samples.length
  return `${count} sample${count === 1 ? '' : 's'}`
}

function selectSample(sample) {
  emit('select', sample.originalIndex)
}

function isGroupSelected(group) {
  return group.samples.some(sample => sample.originalIndex === props.selectedIndex)
}
</script>

<template>
  <table>
    <thead><tr><th>Status</th><th>System / Station</th><th>Context</th><th>Palladium</th><th>Gold</th><th>Silver</th><th>Samples</th><th>Last Sample</th></tr></thead>
    <tbody>
      <template v-for="group in groups" :key="group.id">
        <tr :class="[{ strong: group.latest.is_jackpot, selected: isGroupSelected(group) }]" @click="selectSample(group.latest)">
          <td><button type="button" class="inlineToggle" :title="isExpanded(group) ? 'Hide sample history' : 'Show sample history'" @click.stop="toggleGroup(group)">{{ isExpanded(group) ? '▾' : '▸' }}</button> {{ groupStatus(group) }}</td>
          <td><div class="systemName">{{ fmt(group.latest.system_name) }}</div><div class="stationName">{{ fmt(group.latest.station_name) }} <span class="stationMeta">| Pad {{ fmt(group.latest.largest_pad) }}</span></div></td>
          <td><div class="cellMain">{{ fmt(group.latest.station_faction_state) }}</div><div class="cellSub">{{ fmt(group.latest.station_economies_json) }}</div></td>
          <td><div class="price"><div class="cellMain">{{ money(group.latest.palladium_buy) }}</div><div class="cellSub">supply: {{ money(group.latest.palladium_supply) }}</div></div></td>
          <td><div class="price"><div class="cellMain">{{ money(group.latest.gold_buy) }}</div><div class="cellSub">supply: {{ money(group.latest.gold_supply) }}</div></div></td>
          <td><div class="price"><div class="cellMain">{{ money(group.latest.silver_buy) }}</div><div class="cellSub">supply: {{ money(group.latest.silver_supply) }}</div></div></td>
          <td><div class="cellMain">{{ sampleCountLabel(group) }}</div><div class="cellSub">Detected: {{ localDateTime(group.first.detected_datetime) }}</div></td>
          <td :title="localDateTime(group.latest.sample_datetime)">{{ compactDateTime(group.latest.sample_datetime) }}</td>
        </tr>
        <template v-if="isExpanded(group)">
          <tr
            v-for="sample in group.samples"
            :key="`${sample.jackpot_id}-${sample.sample_datetime}-${sample.originalIndex}`"
            class="jackpotSampleRow"
            :class="[{ strong: sample.is_jackpot, selected: sample.originalIndex === selectedIndex }]"
            @click="selectSample(sample)"
          >
            <td>{{ sample.is_jackpot ? 'Active sample' : 'Ended sample' }}</td>
            <td><div class="cellSub" :title="localDateTime(sample.sample_datetime)">{{ compactDateTime(sample.sample_datetime) }}</div></td>
            <td><div class="cellSub">{{ fmt(sample.sample_triggers || sample.event_triggers) }}</div></td>
            <td><div class="price"><div class="cellMain">{{ money(sample.palladium_buy) }}</div><div class="cellSub">supply: {{ money(sample.palladium_supply) }}</div></div></td>
            <td><div class="price"><div class="cellMain">{{ money(sample.gold_buy) }}</div><div class="cellSub">supply: {{ money(sample.gold_supply) }}</div></div></td>
            <td><div class="price"><div class="cellMain">{{ money(sample.silver_buy) }}</div><div class="cellSub">supply: {{ money(sample.silver_supply) }}</div></div></td>
            <td colspan="2"><div class="cellSub">Detected: {{ localDateTime(sample.detected_datetime) }}</div></td>
          </tr>
        </template>
      </template>
    </tbody>
  </table>
</template>
