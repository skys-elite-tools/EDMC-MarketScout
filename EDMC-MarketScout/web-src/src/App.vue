<script setup>
import { storeToRefs } from 'pinia'
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import StatusStrip from './components/StatusStrip.vue'
import TargetStateToast from './components/TargetStateToast.vue'
import TopBar from './components/TopBar.vue'
import FooterBar from './components/FooterBar.vue'
import ModalShell from './components/ModalShell.vue'
import { useCommoditySettingsStore } from './stores/commoditySettingsStore.js'
import { useNotificationStore } from './stores/notificationStore.js'
import { useStationViewStore } from './stores/stationViewStore.js'
import { useStatusStore } from './stores/statusStore.js'
import { useStationsStore } from './stores/stationsStore.js'
import { useSystemStore } from './stores/systemStore.js'
import { useTripPlannerStore } from './stores/tripPlannerStore.js'
import { useViewRefreshStore } from './stores/viewRefreshStore.js'
import { dataStore } from './services/dataStoreService.js'
import { viewPathByName } from './router/index.js'

const statusStore = useStatusStore()

const systemStore = useSystemStore()
const { helpArticle, helpRequestId, supportOpen, updateModal } = storeToRefs(systemStore)
const tripPlannerStore = useTripPlannerStore()
const commoditySettingsStore = useCommoditySettingsStore()
const stationViewStore = useStationViewStore()
const notificationStore = useNotificationStore()
const stationsStore = useStationsStore()
const viewRefreshStore = useViewRefreshStore()
const route = useRoute()
const router = useRouter()
const {
  selectedRow: selectedStationRow,
} = storeToRefs(stationsStore)

const ACTIVE_VIEW_STORAGE_KEY = 'ui.activeView'
const LEGACY_ACTIVE_VIEW_STORAGE_KEY = 'marketscout.activeView'
const currentView = computed(() => route.name || 'stations')
const detailsOpen = computed(() => currentView.value === 'stations' && selectedStationRow.value)

watch(currentView, (view) => {
  dataStore.set(ACTIVE_VIEW_STORAGE_KEY, view, { debounceMs: 0 })
  statusStore.statusText = `${route.meta?.title || 'MarketScout'} · ${new Date().toLocaleTimeString()}`
})

async function pollStatus() {
  return statusStore.pollStatus({
    onTargetStateAlert: notificationStore.updateTargetStateToast,
    onDataVersionChanged: async () => {
      viewRefreshStore.requestRefresh({ preserveRows: true, reason: 'data-version' })
      await stationViewStore.loadStationFilterOptions()
    },
  })
}

let pollTimer = null
onMounted(async () => {
  statusStore.setStatusRefreshHandler(pollStatus)
  tripPlannerStore.setTripRouteStopSelectionHandler(stationViewStore.applyTripRouteStopSelection)
  const storedView = await dataStore.get(ACTIVE_VIEW_STORAGE_KEY, currentView.value, {
    legacyKey: LEGACY_ACTIVE_VIEW_STORAGE_KEY,
    legacyJson: false,
  })
  if (route.path === '/' && viewPathByName[storedView]) {
    await router.replace(viewPathByName[storedView])
  }
  await Promise.all([commoditySettingsStore.loadCommoditySettings(), stationViewStore.initialize(), tripPlannerStore.loadTripRoutes()])
  await pollStatus()
  pollTimer = setInterval(pollStatus, 2000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  statusStore.setStatusRefreshHandler(null)
  tripPlannerStore.setTripRouteStopSelectionHandler(null)
  notificationStore.disposeNotifications()
})
</script>

<template>
  <div class="appShell">
    <StatusStrip />

    <TargetStateToast />

    <TopBar />

    <main :class="{ detailsOpen }">
      <section class="tablePanel">
        <RouterView />
      </section>
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

    <div v-if="updateModal.visible" class="modalBackdrop" @click.self="systemStore.closeUpdateModal()">
      <section class="aboutModal updateModal" role="dialog" aria-modal="true" aria-labelledby="update-modal-title">
        <div class="modalHeader">
          <h2 id="update-modal-title">{{ updateModal.title }}</h2>
          <button type="button" class="iconButton" aria-label="Close" @click="systemStore.closeUpdateModal()">×</button>
        </div>
        <p>{{ updateModal.message }}</p>
        <p v-if="updateModal.backupPath" class="modalPath"><strong>Backup:</strong> {{ updateModal.backupPath }}</p>
        <p v-if="updateModal.pluginDir" class="modalPath"><strong>Plugin:</strong> {{ updateModal.pluginDir }}</p>
        <div class="modalActions">
          <button type="button" @click="systemStore.closeUpdateModal()">Close</button>
        </div>
      </section>
    </div>
  </div>
</template>
