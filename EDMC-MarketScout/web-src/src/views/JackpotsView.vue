<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import JackpotFilterBar from '../components/JackpotFilterBar.vue'
import JackpotHistory from '../components/JackpotHistory.vue'
import StationDetails from '../components/StationDetails.vue'
import ViewHeader from '../components/ViewHeader.vue'
import { dataStore } from '../services/dataStoreService.js'
import { useStatusStore } from '../stores/statusStore.js'
import { useViewRefreshStore } from '../stores/viewRefreshStore.js'

const LIMIT_STORAGE_KEY = 'jackpots.rowLimit'
const DEFAULT_LIMIT = 30

function rowLimit(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return DEFAULT_LIMIT
  return Math.max(1, Math.min(Math.round(number), 2000))
}

const statusStore = useStatusStore()
const viewRefreshStore = useViewRefreshStore()
const filters = ref({ limit: rowLimit(dataStore.cached(LIMIT_STORAGE_KEY, DEFAULT_LIMIT)) })
const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
let latestRequestId = 0

async function loadJackpots(options = {}) {
  const requestId = ++latestRequestId
  if (!options.preserveRows) {
    rows.value = []
    selectedIndex.value = -1
  } else if (statusStore.statusText && !statusStore.statusText.endsWith(' · Refreshing...')) {
    statusStore.statusText = `${statusStore.statusText} · Refreshing...`
  }
  const limit = rowLimit(filters.value.limit)
  filters.value.limit = limit
  dataStore.set(LIMIT_STORAGE_KEY, limit, { debounceMs: 0 })
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(limit)}`, { cache: 'no-store' })
  const data = await res.json()
  if (requestId !== latestRequestId) return
  rows.value = data.rows || []
  statusStore.statusText = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

function closeDetails() {
  selectedIndex.value = -1
}

watch(
  () => viewRefreshStore.refreshSerial,
  () => loadJackpots(viewRefreshStore.refreshOptions),
)

onMounted(async () => {
  filters.value.limit = rowLimit(await dataStore.get(LIMIT_STORAGE_KEY, filters.value.limit))
  loadJackpots()
})
</script>

<template>
  <section class="viewControls">
    <ViewHeader />
    <JackpotFilterBar :filters="filters" @apply="loadJackpots" />
  </section>

  <JackpotHistory
    :rows="rows"
    :selected-index="selectedIndex"
    @select="selectedIndex = $event"
  />

  <StationDetails
    v-if="selectedRow"
    :row="selectedRow"
    current-view="jackpots"
    @close="closeDetails"
  />
</template>
