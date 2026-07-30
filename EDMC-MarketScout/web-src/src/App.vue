<script setup>
import { storeToRefs } from 'pinia'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import StatusStrip from './components/StatusStrip.vue'
import TargetStateToast from './components/TargetStateToast.vue'
import TopBar from './components/TopBar.vue'
import ViewControls from './components/ViewControls.vue'
import StationDetails from './components/StationDetails.vue'
import JackpotHistory from './components/JackpotHistory.vue'
import StationsView from './views/StationsView.vue'
import LedgerView from './views/LedgerView.vue'
import RareCommoditiesView from './views/RareCommoditiesView.vue'
import CommoditiesView from './views/CommoditiesView.vue'
import AnalyzeCommoditiesView from './views/AnalyzeCommoditiesView.vue'
import CarrierTradeAnnouncementsView from './views/CarrierTradeAnnouncementsView.vue'
import CarrierTradeCalculatorView from './views/CarrierTradeCalculatorView.vue'
import ConfigurationView from './views/ConfigurationView.vue'
import FooterBar from './components/FooterBar.vue'
import ModalShell from './components/ModalShell.vue'
import { useCommoditySettingsStore } from './stores/commoditySettingsStore.js'
import { useNotificationStore } from './stores/notificationStore.js'
import { useStationViewStore } from './stores/stationViewStore.js'
import { useStatusStore } from './stores/statusStore.js'
import { useStationsStore } from './stores/stationsStore.js'
import { useSystemStore } from './stores/systemStore.js'
import { useTripPlannerStore } from './stores/tripPlannerStore.js'
import { query } from './utils.js'
import { dataStore } from './services/dataStoreService.js'

const statusStore = useStatusStore()
const {
  statusText,
  latestJournalEvent,
  updateStatus,
  updateBusy,
} = storeToRefs(statusStore)

const systemStore = useSystemStore()
const { helpArticle, helpRequestId, supportOpen } = storeToRefs(systemStore)
const { openHelp } = systemStore
const tripPlannerStore = useTripPlannerStore()
const commoditySettingsStore = useCommoditySettingsStore()
const stationViewStore = useStationViewStore()
const notificationStore = useNotificationStore()
const stationsStore = useStationsStore()
const {
  stationRowsLoading,
  stationRowsRendering,
  selectedRow: selectedStationRow,
} = storeToRefs(stationsStore)

const rows = ref([])
const selectedIndex = ref(-1)
const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
let latestRowsRequestId = 0
const ACTIVE_VIEW_STORAGE_KEY = 'ui.activeView'
const LEGACY_ACTIVE_VIEW_STORAGE_KEY = 'marketscout.activeView'
const VALID_VIEWS = new Set(['stations', 'jackpots', 'ledger', 'commodities', 'rare', 'analyze', 'carrier', 'carrierCalc', 'config'])

function loadStoredView() {
  const stored = dataStore.cached(ACTIVE_VIEW_STORAGE_KEY, 'stations', {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  return VALID_VIEWS.has(stored) ? stored : 'stations'
}

function persistCurrentView() {
  dataStore.set(ACTIVE_VIEW_STORAGE_KEY, currentView.value)
}

const currentView = ref(loadStoredView())
const updateModal = ref({
  visible: false,
  title: '',
  message: '',
  backupPath: '',
  pluginDir: '',
})
const filters = ref({})

const ledgerFilters = ref({
  commodity: '',
  eventType: 'Any',
  showLifo: false,
})

const rareFilters = ref({
  sort: 'profit_desc',
  engineeringOnly: false,
})

const commodityFilters = ref({
  sort: 'commodity_asc',
})

function setSelected(idx) {
  selectedIndex.value = idx
}

function closeDetails() {
  selectedIndex.value = -1
}

function beginRowsLoad(viewName, options = {}) {
  const preserveRows = options.preserveRows === true
  currentView.value = viewName
  if (!preserveRows) {
    selectedIndex.value = -1
    rows.value = []
  } else if (statusText.value && !statusText.value.endsWith(' · Refreshing...')) {
    statusText.value = `${statusText.value} · Refreshing...`
  }
  latestRowsRequestId += 1
  return latestRowsRequestId
}

function isActiveRowsLoad(viewName, requestId) {
  return currentView.value === viewName && requestId === latestRowsRequestId
}

async function loadStations(options = {}) {
  await stationViewStore.loadStations(options)
}

async function loadJackpots(options = {}) {
  const requestId = beginRowsLoad('jackpots', options)
  const res = await fetch(`/api/jackpots?limit=${encodeURIComponent(filters.value.limit || '500')}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('jackpots', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} jackpot samples · ${new Date().toLocaleTimeString()}`
}

async function loadLedger(options = {}) {
  const requestId = beginRowsLoad('ledger', options)
  const params = {
    commodity: ledgerFilters.value.commodity || '',
    event_type: ledgerFilters.value.eventType || 'Any',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/ledger?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('ledger', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} trades · ${new Date().toLocaleTimeString()}`
}

async function loadRareCommodities(options = {}) {
  const requestId = beginRowsLoad('rare', options)
  const params = {
    sort: rareFilters.value.sort || 'profit_desc',
    engineering_only: rareFilters.value.engineeringOnly ? '1' : '0',
    limit: filters.value.limit || '1000',
  }
  const res = await fetch(`/api/rare-commodities?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('rare', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} rare commodities · ${new Date().toLocaleTimeString()}`
}

async function loadCommodityStats(options = {}) {
  const requestId = beginRowsLoad('commodities', options)
  const params = {
    sort: commodityFilters.value.sort || 'commodity_asc',
  }
  const res = await fetch(`/api/commodity-stats?${query(params)}`, { cache: 'no-store' })
  const data = await res.json()
  if (!isActiveRowsLoad('commodities', requestId)) return
  rows.value = data.rows || []
  statusText.value = `${rows.value.length} commodities · ${new Date().toLocaleTimeString()}`
}

async function loadAnalyzeCommodities() {
  beginRowsLoad('analyze')
  statusText.value = `Analyze commodities · ${new Date().toLocaleTimeString()}`
}

async function loadCarrierTradeAlert() {
  beginRowsLoad('carrier')
  statusText.value = `Carrier trade announcements · ${new Date().toLocaleTimeString()}`
}

async function loadCarrierTradeCalculator() {
  beginRowsLoad('carrierCalc')
  statusText.value = `Carrier trade calculator · ${new Date().toLocaleTimeString()}`
}

async function loadConfiguration() {
  beginRowsLoad('config')
  statusText.value = `Configuration · ${new Date().toLocaleTimeString()}`
}

function applyCurrentView(options = {}) {
  if (currentView.value === 'config') return loadConfiguration()
  if (currentView.value === 'carrierCalc') return loadCarrierTradeCalculator()
  if (currentView.value === 'carrier') return loadCarrierTradeAlert()
  if (currentView.value === 'analyze') return loadAnalyzeCommodities()
  if (currentView.value === 'commodities') return loadCommodityStats(options)
  if (currentView.value === 'rare') return loadRareCommodities(options)
  if (currentView.value === 'ledger') return loadLedger(options)
  if (currentView.value === 'jackpots') return loadJackpots(options)
  return loadStations(options)
}

watch(currentView, () => {
  persistCurrentView()
  applyCurrentView()
})

watch(
  () => [rareFilters.value.sort, rareFilters.value.engineeringOnly],
  () => {
    if (currentView.value === 'rare') loadRareCommodities()
  }
)

watch(
  () => commodityFilters.value.sort,
  () => {
    if (currentView.value === 'commodities') loadCommodityStats()
  }
)


async function pollStatus() {
  return statusStore.pollStatus({
    onTargetStateAlert: notificationStore.updateTargetStateToast,
    onDataVersionChanged: async () => {
      await Promise.all([applyCurrentView({ preserveRows: true }), stationViewStore.loadStationFilterOptions()])
    },
  })
}

async function discardEdmcDelayedStationMessages() {
  await statusStore.discardEdmcDelayedStationMessages({ refresh: pollStatus })
}

let pollTimer = null
onMounted(async () => {
  tripPlannerStore.setTripRouteStopSelectionHandler(stationViewStore.applyTripRouteStopSelection)
  const storedView = await dataStore.get(ACTIVE_VIEW_STORAGE_KEY, currentView.value, {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  if (VALID_VIEWS.has(storedView)) currentView.value = storedView
  await Promise.all([commoditySettingsStore.loadCommoditySettings(), stationViewStore.initialize(), tripPlannerStore.loadTripRoutes()])
  await pollStatus()
  await applyCurrentView()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  tripPlannerStore.setTripRouteStopSelectionHandler(null)
  notificationStore.disposeNotifications()
})
</script>

<template>
  <div class="appShell">
    <StatusStrip
      :busy-text="stationRowsLoading ? 'Loading stations...' : (stationRowsRendering ? 'Updating table...' : '')"
      @run-update="handleUpdateAction"
      @discard-edmc-delayed="discardEdmcDelayedStationMessages"
      @open-support="systemStore.openSupport()"
    />

    <TargetStateToast />

    <TopBar
      v-model:current-view="currentView"
      @refresh="applyCurrentView"
    />

    <ViewControls
      v-if="currentView !== 'stations'"
      :current-view="currentView"
      :filters="filters"
      :ledger-filters="ledgerFilters"
      :rare-filters="rareFilters"
      :commodity-filters="commodityFilters"
      @apply="applyCurrentView"
      @open-help="openHelp"
    />

    <main :class="{ detailsOpen: currentView === 'stations' ? selectedStationRow : selectedRow }">
      <section class="tablePanel">
        <StationsView v-if="currentView === 'stations'" />
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
        <RareCommoditiesView
          v-else-if="currentView === 'rare'"
          :rows="rows"
          :selected-index="selectedIndex"
        />
        <CommoditiesView
          v-else-if="currentView === 'commodities'"
          :rows="rows"
        />
        <AnalyzeCommoditiesView
          v-else-if="currentView === 'analyze'"
        />
        <CarrierTradeAnnouncementsView
          v-else-if="currentView === 'carrier'"
        />
        <CarrierTradeCalculatorView
          v-else-if="currentView === 'carrierCalc'"
        />
        <ConfigurationView
          v-else-if="currentView === 'config'"
        />
      </section>

      <StationDetails
        v-if="selectedRow && currentView !== 'rare'"
        :row="selectedRow"
        :current-view="currentView"
        @close="closeDetails"
      />
    </main>

    <FooterBar
      :help-article="helpArticle"
      :help-request-id="helpRequestId"
    />

    <ModalShell v-if="supportOpen" title="Support MarketScout" title-id="supportTitle" panel-class="aboutModal" @close="systemStore.closeSupport()">
      <p>MarketScout is free and open source. If you find it useful and would like to support development, you can do so here:</p>
      <p>
        <a href="https://oriondreams.gumroad.com/l/MarketScout/" target="_blank" rel="noreferrer">Support MarketScout on Gumroad</a>
      </p>
      <p>Thank you for helping keep MarketScout moving forward. o7 commanders.</p>
    </ModalShell>

    <div v-if="updateModal.visible" class="modalBackdrop" @click.self="updateModal.visible = false">
      <section class="aboutModal updateModal" role="dialog" aria-modal="true" aria-labelledby="update-modal-title">
        <div class="modalHeader">
          <h2 id="update-modal-title">{{ updateModal.title }}</h2>
          <button type="button" class="iconButton" aria-label="Close" @click="updateModal.visible = false">×</button>
        </div>
        <p>{{ updateModal.message }}</p>
        <p v-if="updateModal.backupPath" class="modalPath"><strong>Backup:</strong> {{ updateModal.backupPath }}</p>
        <p v-if="updateModal.pluginDir" class="modalPath"><strong>Plugin:</strong> {{ updateModal.pluginDir }}</p>
        <div class="modalActions">
          <button type="button" @click="updateModal.visible = false">Close</button>
        </div>
      </section>
    </div>
  </div>
</template>
