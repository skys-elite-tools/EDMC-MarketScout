<script setup>
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationsStore } from '../stores/stationsStore.js'
import { fmt, localDateTime, money, num } from '../utils.js'

const props = defineProps({
  row: { type: Object, default: null },
  currentView: { type: String, required: true },
})
const emit = defineEmits(['close'])
const stationsStore = useStationsStore()
const commoditySettingsStore = useCommoditySettingsStore()
const { selectedRow: selectedStationRow } = storeToRefs(stationsStore)
const { watchedCommodities } = storeToRefs(commoditySettingsStore)

const activeRow = computed(() => props.currentView === 'stations' ? selectedStationRow.value : props.row)

const detailCommodities = computed(() => Array.from(new Set([
  ...watchedCommodities.value,
])))

function demandText(value) {
  return num(value) === 0 ? '0/unlimited' : money(value)
}

function pendingStates(row) {
  return String(row?.station_faction_pending_states || '')
    .split('|')
    .map(state => state.trim())
    .filter(Boolean)
}

function stateDisplayName(state) {
  return String(state || '').replace(/([a-z])([A-Z])/g, '$1 $2')
}

function closeDetails() {
  if (props.currentView === 'stations') {
    stationsStore.closeDetails()
    return
  }
  emit('close')
}

const stationDetails = computed(() => {
  const row = activeRow.value || {}
  return [
    ['System', row.system], ['Station', row.station], ['Pad', row.pad], ['Type', row.type],
    ['Station Owner State', row.station_faction_state], ['Pending Owner States', pendingStates(row).map(stateDisplayName).join(', ') || null],
    ['Economies', row.economies], ['System Economy', row.system_economy],
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
          <h2>{{ fmt(activeRow.system) }}</h2>
          <p class="subtitle">{{ fmt(activeRow.station) }} | Pad {{ fmt(activeRow.pad) }}</p>
        </div>
        <button type="button" class="detailsClose" title="Close details" aria-label="Close details" @click="closeDetails">x</button>
      </div>
      <dl class="detailGrid">
        <template v-for="[k, v] in stationDetails" :key="k">
          <dt>{{ k }}</dt><dd>{{ fmt(v) }}</dd>
        </template>
      </dl>
      <div v-for="commodity in detailCommodities" :key="commodity" class="metalBlock">
        <h3>{{ commodity }}</h3>
        <dl class="detailGrid">
          <dt>Buy</dt><dd>{{ money(activeRow[`${commodity}_buy`]) }}</dd>
          <dt>Supply</dt><dd>{{ money(activeRow[`${commodity}_supply`]) }}</dd>
          <dt>Sell</dt><dd>{{ money(activeRow[`${commodity}_sell`]) }}</dd>
          <dt>Demand</dt><dd>{{ demandText(activeRow[`${commodity}_demand`]) }}</dd>
        </dl>
      </div>
    </template>

    <template v-else>
      <div class="detailsHeader">
        <h2>{{ currentView === 'ledger' ? `${fmt(activeRow.event_type).toUpperCase()} ${fmt(activeRow.commodity)}` : `Jackpot ${fmt(activeRow.jackpot_id)}` }}</h2>
        <button type="button" class="detailsClose" title="Close details" aria-label="Close details" @click="closeDetails">x</button>
      </div>
      <pre>{{ JSON.stringify(activeRow, null, 2) }}</pre>
    </template>
  </aside>
</template>
