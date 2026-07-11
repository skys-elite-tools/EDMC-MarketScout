<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import TopBar from './components/TopBar.vue'
import ViewControls from './components/ViewControls.vue'
import CommoditySettings from './components/CommoditySettings.vue'
import StationsTable from './components/StationsTable.vue'
import StationDetails from './components/StationDetails.vue'
import JackpotHistory from './components/JackpotHistory.vue'
import LedgerView from './components/LedgerView.vue'
import FooterBar from './components/FooterBar.vue'
import { columnKey, dedupeStationRows, query } from './utils.js'

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
const lastVersion = ref(null)
const currentView = ref('stations')
const displayColumns = ref([])
const watchedCommodities = ref(['Palladium', 'Gold', 'Silver'])
const allCommodities = ref([])
const settingsVisible = ref(false)
const commoditySearch = ref('')
const statusText = ref('Loading…')
const autoRefresh = ref(true)

const filters = ref({
  system: '',
  station: '',
  economy: 'Extraction, Refinery',
  state: '',
  source: 'Any',
  includeFc: false,
  priceThreshold: 6000,
  supplyThreshold: 10000,
  limit: 1000,
})

const ledgerFilters = ref({
  commodity: '',
  eventType: 'Any',
  showLifo: false,
})

function stationParams() {
  return {
    system: filters.value.system,
    station: filters.value.station,
    economy: filters.value.economy,
    state: filters.value.state,
    source: filters.value.source,
    include_fc: filters.value.includeFc ? '1' : '0',
    limit: filters.value.limit || '1000',
  }
}

function setSelected(idx) {
  selectedIndex.value = idx
}

async function loadStations() {
  currentView.value = 'stations'
  const res = await fetch(`/api/stations?${query(stationParams())}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = dedupeStationRows(data.rows || [])
  displayColumns.value = data.display_columns || []
  watchedCommodities.value = data.watched_commodities || watchedCommodities.value
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} rows · ${new Date().toLocaleTimeString()}`
}

async function loadJackpots() {
  currentView.value = 'jackpots'
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(filters.value.limit || '500')}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = data.rows || []
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

async function loadLedger() {
  currentView.value = 'ledger'
  const params = {
    commodity: ledgerFilters.value.commodity || '',
    event_type: ledgerFilters.value.eventType || 'Any',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/ledger?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  rows.value = data.rows || []
  selectedIndex.value = -1
  statusText.value = `${rows.value.length} trades · ${new Date().toLocaleTimeString()}`
}

function applyCurrentView() {
  if (currentView.value === 'ledger') return loadLedger()
  if (currentView.value === 'jackpots') return loadJackpots()
  return loadStations()
}

watch(currentView, () => {
  applyCurrentView()
})

async function loadCommoditySettings() {
  const [settingsRes, commoditiesRes] = await Promise.all([
    fetch('/api/settings', { cache: 'no-store' }),
    fetch('/api/commodities', { cache: 'no-store' }),
  ])
  const settings = await settingsRes.json()
  const data = await commoditiesRes.json()
  watchedCommodities.value = settings.watched_commodities || ['Palladium', 'Gold', 'Silver']
  displayColumns.value = settings.watched_columns || watchedCommodities.value.map(c => ({ commodity: c, side: 'buy' }))
  allCommodities.value = Array.from(new Set([...(data.commodities || []), ...watchedCommodities.value])).sort()
}

const filteredCommodities = computed(() => {
  const filter = (commoditySearch.value || '').toLowerCase()
  return allCommodities.value.filter(c => !filter || c.toLowerCase().includes(filter)).slice(0, 250)
})

function setWatchedCommodity(commodity, checked) {
  const set = new Set(watchedCommodities.value)
  if (checked) set.add(commodity)
  else set.delete(commodity)
  watchedCommodities.value = Array.from(set)
}

function setDisplayColumn(commodity, side, checked) {
  const key = `${commodity}::${side}`
  const map = new Map(displayColumns.value.map(c => [columnKey(c), c]))
  if (checked) map.set(key, { commodity, side })
  else map.delete(key)
  displayColumns.value = Array.from(map.values())
}

async function saveCommoditySettings() {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      watched_commodities: watchedCommodities.value,
      watched_columns: displayColumns.value,
    }),
  })
  settingsVisible.value = false
  await loadStations()
}

async function openCommoditySettings() {
  settingsVisible.value = !settingsVisible.value
  if (settingsVisible.value) await loadCommoditySettings()
}

async function pollStatus() {
  if (!autoRefresh.value) return
  const res = await fetch('/api/status', { cache: 'no-store' })
  const data = await res.json()
  if (lastVersion.value !== null && data.data_version !== lastVersion.value) {
    await applyCurrentView()
  }
  lastVersion.value = data.data_version
}

let pollTimer = null
onMounted(async () => {
  await loadCommoditySettings()
  await loadStations()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="appShell">
    <TopBar
      v-model:current-view="currentView"
      v-model:auto-refresh="autoRefresh"
      :status-text="statusText"
      @refresh="applyCurrentView"
    />

    <ViewControls
      :current-view="currentView"
      :filters="filters"
      :ledger-filters="ledgerFilters"
      @apply="applyCurrentView"
      @open-commodities="openCommoditySettings"
    />

    <CommoditySettings
      :visible="settingsVisible"
      :commodities="filteredCommodities"
      :watched-commodities="watchedCommodities"
      :display-columns="displayColumns"
      :search="commoditySearch"
      @close="settingsVisible = false"
      @save="saveCommoditySettings"
      @update:search="commoditySearch = $event"
      @toggle-watched="setWatchedCommodity"
      @toggle-display-column="setDisplayColumn"
    />

    <main>
      <section class="tablePanel">
        <StationsTable
          v-if="currentView === 'stations'"
          :rows="rows"
          :selected-index="selectedIndex"
          :display-columns="displayColumns"
          :watched-commodities="watchedCommodities"
          :price-threshold="filters.priceThreshold"
          :supply-threshold="filters.supplyThreshold"
          @select="setSelected"
        />
        <JackpotHistory
          v-else-if="currentView === 'jackpots'"
          :rows="rows"
          :selected-index="selectedIndex"
          @select="setSelected"
        />
        <LedgerView
          v-else-if="currentView === 'ledger'"
          :rows="rows"
          :selected-index="selectedIndex"
          :show-lifo="ledgerFilters.showLifo"
          @select="setSelected"
        />
      </section>

      <StationDetails
        :row="selectedRow"
        :current-view="currentView"
        :watched-commodities="watchedCommodities"
        :display-columns="displayColumns"
      />
    </main>

    <FooterBar />
  </div>
</template>
