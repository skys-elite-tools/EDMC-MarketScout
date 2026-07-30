<script setup>
import { onMounted, ref, watch } from 'vue'
import RareCommoditiesFilterBar from '../components/RareCommoditiesFilterBar.vue'
import ViewHeader from '../components/ViewHeader.vue'
import { dataStore } from '../services/dataStoreService.js'
import { useStatusStore } from '../stores/statusStore.js'
import { useViewRefreshStore } from '../stores/viewRefreshStore.js'
import { fmt, ly, money, num, query, rareDateTime } from '../utils.js'

const LIMIT_STORAGE_KEY = 'rareCommodities.rowLimit'
const DEFAULT_LIMIT = 30

function rowLimit(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return DEFAULT_LIMIT
  return Math.max(1, Math.min(Math.round(number), 2000))
}

const statusStore = useStatusStore()
const viewRefreshStore = useViewRefreshStore()
const filters = ref({
  sort: 'profit_desc',
  engineeringOnly: false,
  limit: rowLimit(dataStore.cached(LIMIT_STORAGE_KEY, DEFAULT_LIMIT)),
})
const rows = ref([])
let latestRequestId = 0

async function loadRareCommodities(options = {}) {
  const requestId = ++latestRequestId
  if (!options.preserveRows) rows.value = []
  else if (statusStore.statusText && !statusStore.statusText.endsWith(' · Refreshing...')) {
    statusStore.statusText = `${statusStore.statusText} · Refreshing...`
  }
  const params = {
    sort: filters.value.sort || 'profit_desc',
    engineering_only: filters.value.engineeringOnly ? '1' : '0',
    limit: rowLimit(filters.value.limit),
  }
  filters.value.limit = params.limit
  dataStore.set(LIMIT_STORAGE_KEY, params.limit, { debounceMs: 0 })
  const res = await fetch(`/api/rare-commodities?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (requestId !== latestRequestId) return
  rows.value = data.rows || []
  statusStore.statusText = `${rows.value.length} rare commodities · ${new Date().toLocaleTimeString()}`
}

watch(
  () => viewRefreshStore.refreshSerial,
  () => loadRareCommodities(viewRefreshStore.refreshOptions),
)

onMounted(async () => {
  filters.value.limit = rowLimit(await dataStore.get(LIMIT_STORAGE_KEY, filters.value.limit))
  loadRareCommodities()
})

function profitTitle(row) {
  const avg = money(row.galactic_average_price)
  if (avg === '—') {
    return 'Profit if sold at 100x galactic average which is the maximum for fleet carriers.'
  }
  return `Galactic Average = ${avg} Cr. Profit if sold at 100x galactic average, which is the maximum for fleet carriers.`
}

function profitClass(row) {
  const profit = num(row.carrier_profit)
  if (profit === null) return ''
  return profit > 0 ? 'positive' : profit < 0 ? 'negative' : ''
}
</script>

<template>
  <section class="viewControls">
    <ViewHeader />
    <RareCommoditiesFilterBar :filters="filters" @apply="loadRareCommodities" />
  </section>

  <table class="rareTable">
    <thead>
      <tr>
        <th>Commodity</th>
        <th>System</th>
        <th>Station</th>
        <th class="num">St. dist</th>
        <th class="num">Distance</th>
        <th class="num">Supply</th>
        <th class="num">Highest</th>
        <th class="num">Recent</th>
        <th class="num">Rec.Date</th>
        <th class="num">Buy Price</th>
        <th class="num">Gal. Avg</th>
        <th class="num">100x Gal. Avg</th>
        <th class="num">Profit</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(row, idx) in rows"
        :key="row.commodity || idx"
        :class="[{ engineeringRare: row.is_engineering_rare }]"
      >
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div v-if="row.is_engineering_rare" class="cellSub" :title="row.engineering_unlocks_title || ''">{{ fmt(row.engineering_unlocks) }}</div></td>
        <td>{{ fmt(row.system_name) }}</td>
        <td>{{ fmt(row.station_name) }}</td>
        <td class="num">{{ money(row.station_distance_ls) }}</td>
        <td class="num">{{ ly(row.distance_from_current_ly) }}</td>
        <td class="num">{{ money(row.usual_supply) }}</td>
        <td class="num" :title="`Highest seen: ${rareDateTime(row.highest_supply_datetime)}`">{{ money(row.highest_supply) }}</td>
        <td class="num">{{ money(row.recent_supply) }}</td>
        <td class="num">{{ rareDateTime(row.recent_supply_datetime) }}</td>
        <td class="num">{{ money(row.buy_price) }}</td>
        <td class="num">{{ money(row.galactic_average_price) }}</td>
        <td class="num">{{ money(row.galactic_average_100x) }}</td>
        <td class="num" :title="profitTitle(row)"><span class="profit" :class="profitClass(row)">{{ money(row.carrier_profit) }}</span></td>
      </tr>
    </tbody>
  </table>
</template>
