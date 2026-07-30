<script setup>
import { onMounted, ref, watch } from 'vue'
import CommoditiesFilterBar from '../components/CommoditiesFilterBar.vue'
import ViewHeader from '../components/ViewHeader.vue'
import { useStatusStore } from '../stores/statusStore.js'
import { useViewRefreshStore } from '../stores/viewRefreshStore.js'
import { fmt, money, query } from '../utils.js'

const statusStore = useStatusStore()
const viewRefreshStore = useViewRefreshStore()
const filters = ref({
  sort: 'commodity_asc',
})
const rows = ref([])
let latestRequestId = 0

async function loadCommodityStats(options = {}) {
  const requestId = ++latestRequestId
  if (!options.preserveRows) rows.value = []
  else if (statusStore.statusText && !statusStore.statusText.endsWith(' · Refreshing...')) {
    statusStore.statusText = `${statusStore.statusText} · Refreshing...`
  }
  const params = {
    sort: filters.value.sort || 'commodity_asc',
  }
  const res = await fetch(`/api/commodity-stats?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (requestId !== latestRequestId) return
  rows.value = data.rows || []
  statusStore.statusText = `${rows.value.length} commodities · ${new Date().toLocaleTimeString()}`
}

watch(
  () => viewRefreshStore.refreshSerial,
  () => loadCommodityStats(viewRefreshStore.refreshOptions),
)

onMounted(() => loadCommodityStats())
</script>

<template>
  <section class="viewControls">
    <ViewHeader />
    <CommoditiesFilterBar :filters="filters" @apply="loadCommodityStats" />
  </section>

  <table class="commoditiesTable">
    <thead>
      <tr>
        <th>Commodity</th>
        <th>Category</th>
        <th class="num">Min Buy</th>
        <th class="num">Avg Buy</th>
        <th class="num">Max Sell</th>
        <th class="num">Max Profit</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.commodity || 'commodity'}-${idx}`">
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div></td>
        <td>{{ fmt(row.category) }}</td>
        <td class="num">{{ money(row.min_buy) }}</td>
        <td class="num">{{ money(row.avg_buy) }}</td>
        <td class="num">{{ money(row.max_sell) }}</td>
        <td class="num"><span class="profit positive">{{ money(row.max_profit) }}</span></td>
      </tr>
    </tbody>
  </table>
</template>
