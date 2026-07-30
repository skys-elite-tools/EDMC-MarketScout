<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import LedgerFilterBar from '../components/LedgerFilterBar.vue'
import StationDetails from '../components/StationDetails.vue'
import ViewHeader from '../components/ViewHeader.vue'
import { dataStore } from '../services/dataStoreService.js'
import { useStatusStore } from '../stores/statusStore.js'
import { useViewRefreshStore } from '../stores/viewRefreshStore.js'
import { fmt, money, num, query, shortTime } from '../utils.js'

const LIMIT_STORAGE_KEY = 'ledger.rowLimit'
const DEFAULT_LIMIT = 30

function rowLimit(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return DEFAULT_LIMIT
  return Math.max(1, Math.min(Math.round(number), 2000))
}

const statusStore = useStatusStore()
const viewRefreshStore = useViewRefreshStore()
const filters = ref({
  commodity: '',
  eventType: 'Any',
  showLifo: false,
  limit: rowLimit(dataStore.cached(LIMIT_STORAGE_KEY, DEFAULT_LIMIT)),
})
const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
let latestRequestId = 0

async function loadLedger(options = {}) {
  const requestId = ++latestRequestId
  if (!options.preserveRows) {
    rows.value = []
    selectedIndex.value = -1
  } else if (statusStore.statusText && !statusStore.statusText.endsWith(' · Refreshing...')) {
    statusStore.statusText = `${statusStore.statusText} · Refreshing...`
  }
  const params = {
    commodity: filters.value.commodity || '',
    event_type: filters.value.eventType || 'Any',
    limit: rowLimit(filters.value.limit),
  }
  filters.value.limit = params.limit
  dataStore.set(LIMIT_STORAGE_KEY, params.limit, { debounceMs: 0 })
  const res = await fetch(`/api/ledger?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (requestId !== latestRequestId) return
  rows.value = data.rows || []
  statusStore.statusText = `${rows.value.length} trades · ${new Date().toLocaleTimeString()}`
}

function closeDetails() {
  selectedIndex.value = -1
}

watch(
  () => viewRefreshStore.refreshSerial,
  () => loadLedger(viewRefreshStore.refreshOptions),
)

onMounted(async () => {
  filters.value.limit = rowLimit(await dataStore.get(LIMIT_STORAGE_KEY, filters.value.limit))
  loadLedger()
})
</script>

<template>
  <section class="viewControls">
    <ViewHeader />
    <LedgerFilterBar :filters="filters" @apply="loadLedger" />
  </section>

  <table>
    <thead><tr><th>Time</th><th>Type</th><th>System / Station</th><th>Commodity</th><th>Qty</th><th>Unit</th><th>Total</th><th>Avg Paid</th><th>Profit</th><th>Cr/hr</th><th v-if="filters.showLifo">LIFO avg</th><th v-if="filters.showLifo">LIFO profit</th></tr></thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="row.trade_id || idx" :class="[{ selected: idx === selectedIndex, ledgerBuy: row.event_type === 'buy', ledgerSell: row.event_type === 'sell', cheap: row.event_type === 'sell' && num(row.journal_profit) > 0 }]" @click="selectedIndex = idx">
        <td>{{ shortTime(row.event_datetime) }}</td><td><span class="tradeType" :class="row.event_type">{{ row.event_type === 'buy' ? 'BUY' : row.event_type === 'sell' ? 'SELL' : fmt(row.event_type) }}</span></td>
        <td><div class="cellMain">{{ fmt(row.system_name) }}</div><div class="cellSub">{{ fmt(row.station_name) }}</div></td>
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div v-if="row.event_type === 'buy' && row.supply_at_trade != null" class="cellSub">Supply: {{ money(row.supply_at_trade) }}</div><div v-else-if="row.event_type === 'sell' && row.demand_at_trade != null" class="cellSub">Demand: {{ money(row.demand_at_trade) }}</div></td>
        <td class="num">{{ money(row.quantity) }}</td><td class="num">{{ money(row.unit_price) }}</td><td class="num">{{ money(row.total_credits) }}</td>
        <td class="num">{{ money(row.journal_avg_price_paid) }}</td><td class="num"><span class="profit" :class="{ positive: num(row.journal_profit) > 0, negative: num(row.journal_profit) < 0 }">{{ money(row.journal_profit) }}</span></td><td class="num">{{ money(row.profit_per_hour ?? row.credits_per_hour) }}</td>
        <td v-if="filters.showLifo" class="num">{{ money(row.ledger_avg_buy_price) }}</td><td v-if="filters.showLifo" class="num">{{ money(row.ledger_profit) }}</td>
      </tr>
    </tbody>
  </table>

  <StationDetails
    v-if="selectedRow"
    :row="selectedRow"
    current-view="ledger"
    @close="closeDetails"
  />
</template>
