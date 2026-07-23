<script setup>
import { computed } from 'vue'
import { fmt, localDateTime, money, num } from '../utils.js'

const props = defineProps({
  row: { type: Object, default: null },
  currentView: { type: String, required: true },
  watchedCommodities: { type: Array, default: () => [] },
  displayColumns: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])

const detailCommodities = computed(() => Array.from(new Set([
  ...props.watchedCommodities,
  ...props.displayColumns.map(c => c.commodity),
])))

function demandText(value) {
  return num(value) === 0 ? '0/unlimited' : money(value)
}

const stationDetails = computed(() => {
  const row = props.row || {}
  return [
    ['System', row.system], ['Station', row.station], ['Pad', row.pad], ['Type', row.type],
    ['State', row.state], ['Economies', row.economies], ['System Economy', row.system_economy],
    ['Security', row.security], ['Population', money(row.population)], ['Arrival LS', money(row.arrival_ls)],
    ['Fleet Carrier', row.fleet_carrier || 'No'], ['Planetary', row.planetary || 'No'],
    ['Source', row.source], ['Source Pulled', localDateTime(row.source_pulled)], ['Source Updated', localDateTime(row.source_updated)],
    ['Market Updated', localDateTime(row.market_updated)], ['Station Visit', localDateTime(row.station_visit)],
    ['Best Buy', row.best_buy_commodity ? `${row.best_buy_commodity} @ ${money(row.best_buy_price)} / supply ${money(row.best_buy_supply)} / potential profit ${money(row.best_buy_potential_profit)} Cr/t` : '—'],
  ]
})
</script>

<template>
  <aside class="details">
    <template v-if="currentView === 'stations'">
      <div class="detailsHeader">
        <div>
          <h2>{{ fmt(row.system) }}</h2>
          <p class="subtitle">{{ fmt(row.station) }} | Pad {{ fmt(row.pad) }}</p>
        </div>
        <button type="button" class="detailsClose" title="Close details" aria-label="Close details" @click="emit('close')">x</button>
      </div>
      <dl class="detailGrid">
        <template v-for="[k, v] in stationDetails" :key="k">
          <dt>{{ k }}</dt><dd>{{ fmt(v) }}</dd>
        </template>
      </dl>
      <div v-for="commodity in detailCommodities" :key="commodity" class="metalBlock">
        <h3>{{ commodity }}</h3>
        <dl class="detailGrid">
          <dt>Buy</dt><dd>{{ money(row[`${commodity}_buy`]) }}</dd>
          <dt>Supply</dt><dd>{{ money(row[`${commodity}_supply`]) }}</dd>
          <dt>Sell</dt><dd>{{ money(row[`${commodity}_sell`]) }}</dd>
          <dt>Demand</dt><dd>{{ demandText(row[`${commodity}_demand`]) }}</dd>
        </dl>
      </div>
    </template>

    <template v-else>
      <div class="detailsHeader">
        <h2>{{ currentView === 'ledger' ? `${fmt(row.event_type).toUpperCase()} ${fmt(row.commodity)}` : `Jackpot ${fmt(row.jackpot_id)}` }}</h2>
        <button type="button" class="detailsClose" title="Close details" aria-label="Close details" @click="emit('close')">x</button>
      </div>
      <pre>{{ JSON.stringify(row, null, 2) }}</pre>
    </template>
  </aside>
</template>
