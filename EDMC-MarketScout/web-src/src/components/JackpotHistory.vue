<script setup>
import { fmt, localDateTime, money } from '../utils.js'

defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
})
const emit = defineEmits(['select'])
</script>

<template>
  <table>
    <thead><tr><th>Status</th><th>System / Station</th><th>Context</th><th>Palladium</th><th>Gold</th><th>Silver</th><th>Sample Time</th><th>Detected</th></tr></thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.jackpot_id}-${row.sample_datetime}-${idx}`" :class="[{ strong: row.is_jackpot, selected: idx === selectedIndex }]" @click="emit('select', idx)">
        <td>{{ row.is_jackpot ? 'Active sample' : 'Ended sample' }}</td>
        <td><div class="systemName">{{ fmt(row.system_name) }}</div><div class="stationName">{{ fmt(row.station_name) }} <span class="stationMeta">| Pad {{ fmt(row.largest_pad) }}</span></div></td>
        <td><div class="cellMain">{{ fmt(row.station_faction_state) }}</div><div class="cellSub">{{ fmt(row.station_economies_json) }}</div></td>
        <td><div class="price"><div class="cellMain">{{ money(row.palladium_buy) }}</div><div class="cellSub">supply: {{ money(row.palladium_supply) }}</div></div></td>
        <td><div class="price"><div class="cellMain">{{ money(row.gold_buy) }}</div><div class="cellSub">supply: {{ money(row.gold_supply) }}</div></div></td>
        <td><div class="price"><div class="cellMain">{{ money(row.silver_buy) }}</div><div class="cellSub">supply: {{ money(row.silver_supply) }}</div></div></td>
        <td>{{ localDateTime(row.sample_datetime) }}</td><td>{{ localDateTime(row.detected_datetime) }}</td>
      </tr>
    </tbody>
  </table>
</template>
