<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import InfoButton from './InfoButton.vue'
import { compactDateTime, localDateTime } from '../utils.js'
import { dataStore } from '../services/dataStoreService.js'

const EXPANDED_STORAGE_KEY = 'tripPlanner.expanded'

const props = defineProps({
  routes: { type: Array, default: () => [] },
  activeRoute: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  status: { type: String, default: '' },
  currentSystem: { type: String, default: '' },
  currentPosition: { type: Object, default: null },
})
const emit = defineEmits(['import-route', 'import-station-hints', 'start-route', 'delete-route', 'select-stop', 'open-help'])

const fileInput = ref(null)
const hintFileInput = ref(null)
const menuOpen = ref(false)
const menuEl = ref(null)
const menuStyle = ref({})
const stopsEl = ref(null)
const stopEls = ref([])
const expanded = ref(Boolean(dataStore.cached(EXPANDED_STORAGE_KEY, false)))
const focusedStopIndex = ref(0)
const visibleStopIndexes = ref([])

const hasActiveRoute = computed(() => props.activeRoute?.route_id != null)
const stops = computed(() => props.activeRoute?.stops || [])
const currentStopIndex = computed(() => {
  const current = props.currentSystem.trim().toLocaleLowerCase()
  if (!current) return -1
  return stops.value.findIndex(stop => String(stop.system_name || '').trim().toLocaleLowerCase() === current)
})
const activeDotIndex = computed(() => Math.max(0, Math.min(stops.value.length - 1, focusedStopIndex.value)))
const currentCoords = computed(() => coordsFrom(props.currentPosition))
const routeSummary = computed(() => {
  const route = props.activeRoute
  if (!route) return ''
  const parts = []
  if (Number(route.stop_count)) parts.push(`${Number(route.stop_count)} stops`)
  if (Number(route.total_jumps)) parts.push(`${Number(route.total_jumps)} jumps`)
  if (Number(route.total_distance_ly)) parts.push(`${Number(route.total_distance_ly).toFixed(1)} Ly`)
  return parts.join(' · ')
})

function coordsFrom(value) {
  const x = Number(value?.x)
  const y = Number(value?.y)
  const z = Number(value?.z)
  return Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z) ? { x, y, z } : null
}

function distanceLy(a, b) {
  if (!a || !b) return null
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
}

function chooseFile() {
  fileInput.value?.click()
}

function chooseHintFile() {
  if (!hasActiveRoute.value) return
  hintFileInput.value?.click()
}

async function importFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const content = await file.text()
  emit('import-route', { filename: file.name, content })
}

async function importHintFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !hasActiveRoute.value) return
  const content = await file.text()
  emit('import-station-hints', { filename: file.name, content, route_id: props.activeRoute?.route_id })
}

function toggleMenu(event) {
  if (menuOpen.value) {
    menuOpen.value = false
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const width = Math.min(544, window.innerWidth - 24)
  const left = Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12))
  const maxHeight = Math.max(160, Math.min(352, window.innerHeight - rect.bottom - 18))
  menuStyle.value = {
    width: `${width}px`,
    left: `${left}px`,
    top: `${rect.bottom + 6}px`,
    maxHeight: `${maxHeight}px`,
  }
  menuOpen.value = true
}

function stopVisitLabel(stop) {
  if (stop.last_station_visit_datetime) return `Visited ${compactDateTime(stop.last_station_visit_datetime)}`
  if (stop.last_system_visit_datetime) return `Visited ${compactDateTime(stop.last_system_visit_datetime)}`
  return 'Not visited yet'
}

function stopTitle(stop) {
  const lines = [
    stop.system_name,
    stopLegLabel(stop, stops.value.indexOf(stop)),
  ]
  if (stop.last_station_name && stop.last_station_visit_datetime) {
    lines.push(`Last station: ${stop.last_station_name}`)
    lines.push(`Visited: ${localDateTime(stop.last_station_visit_datetime)}`)
  } else if (stop.last_system_visit_datetime) {
    lines.push(`Visited: ${localDateTime(stop.last_system_visit_datetime)}`)
  } else {
    lines.push('Not visited yet')
  }
  return lines.join('\n')
}

function stationHintLabel(stop) {
  const name = String(stop.station_hint_name || '').trim()
  if (!name) return ''
  const parts = [name]
  if (stop.station_hint_large_pads != null) parts.push(`${Number(stop.station_hint_large_pads || 0)} L`)
  if (stop.station_hint_distance_to_arrival_ls != null) parts.push(`${Number(stop.station_hint_distance_to_arrival_ls).toLocaleString()} Ls`)
  return parts.join(' · ')
}

function stopLegLabel(stop, index) {
  if (index === 0 && currentStopIndex.value !== 0) {
    const distance = distanceLy(currentCoords.value, coordsFrom(stop))
    if (distance == null) return '-'
    const jumpRange = Number(props.activeRoute?.jump_range_ly)
    const jumps = jumpRange > 0 ? Math.ceil(distance / jumpRange) : null
    return `${jumps == null ? '-' : jumps} jumps · ${distance.toFixed(1)} Ly from current`
  }
  return `${Number(stop.jumps || 0)} jumps · ${Number(stop.leg_distance_ly || 0).toFixed(1)} Ly`
}

function firstStopEstimateParts(stop, index) {
  if (index !== 0 || currentStopIndex.value === 0) return null
  const distance = distanceLy(currentCoords.value, coordsFrom(stop))
  if (distance == null) return null
  const jumpRange = Number(props.activeRoute?.jump_range_ly)
  const jumps = jumpRange > 0 ? Math.ceil(distance / jumpRange) : null
  return {
    jumps: jumps == null ? '-' : `${jumps} jumps`,
    distance: `${distance.toFixed(1)} Ly from current`,
  }
}

function routeTitle(route) {
  const parts = [
    route.route_name,
    `${Number(route.stop_count || 0)} stops`,
  ]
  if (Number(route.total_jumps)) parts.push(`${Number(route.total_jumps)} jumps`)
  if (Number(route.total_distance_ly)) parts.push(`${Number(route.total_distance_ly).toFixed(1)} Ly`)
  return parts.join(' · ')
}

function setStopRef(el, index) {
  if (el) stopEls.value[index] = el
}

function scrollToStop(index) {
  if (!stopsEl.value || index < 0) return
  const target = stopEls.value[index]
  if (!target) return
  focusedStopIndex.value = index
  const anchor = stopEls.value[Math.max(0, index - 1)] || target
  const left = anchor.offsetLeft - stopsEl.value.offsetLeft
  stopsEl.value.scrollTo({
    left: Math.max(0, left - 8),
    behavior: 'smooth',
  })
  window.setTimeout(syncVisibleStops, 260)
}

function stepRoute(direction) {
  if (!stops.value.length) return
  const baseIndex = activeDotIndex.value
  scrollToStop(Math.max(0, Math.min(stops.value.length - 1, baseIndex + direction)))
}

function syncFocusedStopFromScroll() {
  if (!stopsEl.value || !stopEls.value.length) return
  syncVisibleStops()
  if (stopsEl.value.scrollLeft < 12) {
    focusedStopIndex.value = 0
    return
  }
  const viewportLeft = stopsEl.value.scrollLeft + 220
  let closestIndex = 0
  let closestDistance = Number.POSITIVE_INFINITY
  stopEls.value.forEach((el, index) => {
    if (!el) return
    const left = el.offsetLeft - stopsEl.value.offsetLeft
    const distance = Math.abs(left - viewportLeft)
    if (distance < closestDistance) {
      closestIndex = index
      closestDistance = distance
    }
  })
  focusedStopIndex.value = closestIndex
}

function syncVisibleStops() {
  if (!stopsEl.value || !stopEls.value.length) {
    visibleStopIndexes.value = []
    return
  }
  const scrollerRect = stopsEl.value.getBoundingClientRect()
  visibleStopIndexes.value = stopEls.value
    .map((el, index) => ({ el, index }))
    .filter(({ el }) => el && el.getBoundingClientRect().right > scrollerRect.left + 8 && el.getBoundingClientRect().left < scrollerRect.right - 8)
    .map(({ index }) => index)
}

async function toggleExpanded() {
  expanded.value = !expanded.value
  if (!expanded.value) return
  await nextTick()
  scrollToStop(currentStopIndex.value >= 0 ? currentStopIndex.value : activeDotIndex.value)
  syncVisibleStops()
}

function onDocumentClick(event) {
  if (!menuOpen.value) return
  if (menuEl.value?.contains(event.target)) return
  menuOpen.value = false
}

watch(() => props.activeRoute?.route_id, () => {
  stopEls.value = []
  focusedStopIndex.value = 0
  visibleStopIndexes.value = []
})

watch([currentStopIndex, stops], async ([index]) => {
  if (!expanded.value) return
  if (index < 0) return
  await nextTick()
  scrollToStop(index)
  syncVisibleStops()
}, { immediate: true })

watch(expanded, value => {
  dataStore.set(EXPANDED_STORAGE_KEY, Boolean(value))
})

onMounted(async () => {
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('resize', syncVisibleStops)
  expanded.value = Boolean(await dataStore.get(EXPANDED_STORAGE_KEY, expanded.value))
  await nextTick()
  if (expanded.value) {
    scrollToStop(currentStopIndex.value >= 0 ? currentStopIndex.value : activeDotIndex.value)
    syncVisibleStops()
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('resize', syncVisibleStops)
})
</script>

<template>
  <section class="tripRouteBar" :class="{ tripRouteBarExpanded: expanded }" aria-label="Trip route planner">
    <div class="tripRouteToggleRow">
      <button type="button" class="tripRouteToggle" :aria-expanded="expanded" @click="toggleExpanded">
        <span class="tripRouteToggleArrow">{{ expanded ? '▲' : '▼' }}</span>
        <span>Trip Planner</span>
        <span class="tripRouteToggleArrow">{{ expanded ? '▲' : '▼' }}</span>
      </button>
      <div v-if="expanded" class="tripRouteTopTitle">
        <span>Trip Route</span>
        <InfoButton title="Spansh Tourist Route imports" @open="emit('open-help', 'spansh-tourist-route')" />
      </div>
    </div>

    <div v-if="expanded" class="tripRouteLayout">
      <div class="tripRouteInfoPane">
        <div class="tripRouteHeader">
          <div class="tripRouteActions">
            <button
              type="button"
              class="tripRouteImportButton"
              :disabled="busy"
              title="Import a .json file downloaded from the Spansh Tourist Route planner."
              @click="chooseFile"
            >
              Add Tourist Route
            </button>
            <input ref="fileInput" class="hiddenFileInput" type="file" accept="application/json,.json" @change="importFile" />
            <button
              type="button"
              class="tripRouteImportButton"
              :disabled="busy || !hasActiveRoute"
              title="Import a Spansh station/search CSV to add station hints to the active route."
              @click="chooseHintFile"
            >
              Add Stations
            </button>
            <input ref="hintFileInput" class="hiddenFileInput" type="file" accept="text/csv,.csv" @change="importHintFile" />
            <div ref="menuEl" class="tripRouteMenuWrap">
              <button type="button" class="tripRouteMenuButton" :disabled="busy || !routes.length" @click.stop="toggleMenu">
                Routes
                <span class="buttonCount">{{ routes.length }}</span>
              </button>
              <div v-if="menuOpen" class="tripRouteMenu" :style="menuStyle">
                <div v-for="route in routes" :key="route.route_id" class="tripRouteMenuItem">
                  <button type="button" class="tripRoutePickButton" :title="routeTitle(route)" @click="emit('start-route', route.route_id); menuOpen = false">
                    <span>{{ route.route_name }}</span>
                    <span>{{ routeTitle(route) }}</span>
                  </button>
                  <button type="button" class="tripRouteDeleteButton" title="Delete route" @click.stop="emit('delete-route', route.route_id)">×</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="status" class="tripRouteStatus">{{ status }}</p>
        <div v-else-if="activeRoute" class="tripRouteActiveMeta">
          <strong>{{ activeRoute.route_name }}</strong>
          <span v-if="routeSummary">{{ routeSummary }}</span>
        </div>
        <p v-else class="tripRouteEmpty">
          Import a Spansh Tourist Route JSON to pin a route.
        </p>
      </div>

      <div v-if="activeRoute" class="tripStopsPane">
        <div ref="stopsEl" class="tripStops" role="list" @scroll.passive="syncFocusedStopFromScroll">
          <button
            v-for="(stop, index) in stops"
            :key="`${stop.route_id}-${stop.stop_index}-${stop.system_address}`"
            :ref="el => setStopRef(el, index)"
            type="button"
            class="tripStop"
            :class="{ tripStopCurrent: index === currentStopIndex }"
            role="listitem"
            :title="stopTitle(stop)"
            @click="emit('select-stop', stop)"
          >
            <span v-if="index === 0" class="tripStopMarker">Start</span>
            <span v-else-if="index === stops.length - 1" class="tripStopMarker">End</span>
            <span class="tripStopName">{{ stop.system_name }}</span>
            <span v-if="stationHintLabel(stop)" class="tripStopStationHint">{{ stationHintLabel(stop) }}</span>
            <span v-if="firstStopEstimateParts(stop, index)" class="tripStopMeta">
              <span
                class="tripStopApproxJumps"
                title="Approximate jumps to the route start. Calculated from straight-line distance divided by the route jump range."
              >
                {{ firstStopEstimateParts(stop, index).jumps }}
              </span>
              <span> · {{ firstStopEstimateParts(stop, index).distance }}</span>
            </span>
            <span v-else class="tripStopMeta">{{ stopLegLabel(stop, index) }}</span>
            <span class="tripStopVisit">{{ index === currentStopIndex ? 'Current system' : stopVisitLabel(stop) }}</span>
          </button>
        </div>
        <div v-if="stops.length > 1" class="tripStopPager" aria-label="Route stop navigation">
          <button type="button" class="tripStopPagerButton" title="Previous stops" @click="stepRoute(-1)">‹</button>
          <button
            v-for="(stop, index) in stops"
            :key="`dot-${stop.route_id}-${stop.stop_index}-${stop.system_address}`"
            type="button"
            class="tripStopDot"
            :disabled="visibleStopIndexes.includes(index)"
            :class="{
              tripStopDotCurrent: index === activeDotIndex || visibleStopIndexes.includes(index),
              tripStopDotCommander: index === currentStopIndex,
              tripStopDotDisabled: visibleStopIndexes.includes(index),
            }"
            :title="stop.system_name"
            @click="scrollToStop(index)"
          />
          <button type="button" class="tripStopPagerButton" title="Next stops" @click="stepRoute(1)">›</button>
        </div>
      </div>
      <div v-else class="tripStops tripStopsPlaceholder">
        <span>No active route</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tripRouteBar {
  border-bottom: 1px solid var(--line);
  background: #101722;
  padding: 5px 10px;
  min-width: 0;
}
.tripRouteBarExpanded {
  padding: 5px 10px 7px;
}
.tripRouteToggleRow {
  position: relative;
  display: grid;
  grid-template-columns: 1fr;
  align-items: center;
}
.tripRouteToggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 1.45rem;
  padding: 2px 8px;
  border: 0;
  background: transparent;
  color: var(--text);
  font-weight: 900;
}
.tripRouteToggle:hover {
  color: var(--accent);
  background: rgba(140, 200, 255, .07);
}
.tripRouteToggleArrow {
  color: #ca84ff;
  font-size: 11px;
  line-height: 1;
}
.tripRouteTopTitle {
  position: absolute;
  left: 8px;
  top: 50%;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--accent);
  font-weight: 900;
  white-space: nowrap;
  transform: translateY(-50%);
}
.tripRouteLayout {
  display: grid;
  grid-template-columns: minmax(17rem, 19rem) minmax(22rem, 1fr);
  gap: 16px;
  align-items: stretch;
  margin-top: 5px;
}
.tripRouteInfoPane {
  display: grid;
  align-content: center;
  gap: 5px;
  min-width: 0;
  padding-right: 16px;
  border-right: 1px solid rgba(140, 200, 255, .22);
}
.tripRouteHeader {
  min-width: 0;
}
.tripRouteActions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
}
.tripRouteImportButton,
.tripRouteMenuButton {
  min-height: 1.75rem;
  padding: 4px 8px;
  font-weight: 800;
  white-space: nowrap;
}
.tripRouteImportButton {
  grid-column: 1;
  min-width: 0;
  width: 100%;
}
.tripRouteMenuWrap {
  grid-column: 2;
  grid-row: 1 / span 2;
  align-self: stretch;
  position: relative;
}
.tripRouteMenuButton {
  height: 100%;
}
.hiddenFileInput {
  display: none;
}
.tripRouteMenu {
  position: fixed;
  z-index: 20;
  max-height: 22rem;
  overflow: auto;
  border: 1px solid rgba(140, 200, 255, .30);
  border-radius: 6px;
  background: #121923;
  box-shadow: 0 18px 40px rgba(0,0,0,.42);
  padding: 6px;
}
.tripRouteMenuItem {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2rem;
  gap: 6px;
  align-items: stretch;
}
.tripRouteMenuItem + .tripRouteMenuItem {
  margin-top: 6px;
}
.tripRoutePickButton {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  text-align: left;
}
.tripRoutePickButton span:first-child {
  color: var(--text);
  font-weight: 850;
}
.tripRoutePickButton span:last-child,
.tripRouteStatus,
.tripRouteEmpty,
.tripRouteActiveMeta span {
  color: var(--muted);
  font-size: 12px;
}
.tripRouteDeleteButton {
  padding: 0;
  font-size: 18px;
}
.tripRouteStatus,
.tripRouteEmpty {
  margin: 0;
}
.tripRouteActive {
  margin-top: 8px;
}
.tripRouteActiveMeta {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.tripRouteActiveMeta strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tripRouteActiveMeta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tripStopsPane {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.tripStops {
  display: flex;
  align-items: stretch;
  overflow-x: auto;
  scrollbar-width: none;
  min-width: 0;
  padding: 0 0 2px 0;
  scroll-padding-left: 0;
}
.tripStops::-webkit-scrollbar {
  display: none;
}
.tripStopsPlaceholder {
  align-items: center;
  color: var(--muted);
  font-size: 12px;
}
.tripStop {
  position: relative;
  display: grid;
  align-content: center;
  gap: 1px;
  min-width: 13rem;
  max-width: 15rem;
  flex: 0 0 auto;
  margin-right: 7px;
  padding: 7px 34px 7px 14px;
  border: 1px solid rgba(202, 132, 255, .26);
  border-radius: 0;
  background: linear-gradient(90deg, rgba(25, 32, 43, .98), rgba(34, 42, 55, .98));
  color: var(--text);
  text-align: left;
  clip-path: polygon(0 0, calc(100% - 19px) 0, 100% 50%, calc(100% - 19px) 100%, 0 100%);
  box-shadow: 0 7px 16px rgba(0,0,0,.22);
}
.tripStopMarker {
  width: max-content;
  max-width: calc(100% - 10px);
  margin-bottom: 1px;
  padding: 1px 5px;
  border: 1px solid rgba(202, 132, 255, .38);
  border-radius: 999px;
  background: rgba(202, 132, 255, .13);
  color: #ecc9ff;
  font-size: 9px;
  font-weight: 900;
  line-height: 1.15;
  text-transform: uppercase;
}
.tripStop::before {
  content: "";
  position: absolute;
  top: 0;
  right: 13px;
  bottom: 0;
  width: 10px;
  background: linear-gradient(180deg, #f0c8ff, #b36bff);
  clip-path: polygon(0 0, 100% 50%, 0 100%, 44% 100%, 100% 50%, 44% 0);
  opacity: .96;
}
.tripStop::after {
  content: "";
  position: absolute;
  top: 0;
  right: 2px;
  bottom: 0;
  width: 17px;
  background: linear-gradient(180deg, rgba(202, 132, 255, .24), rgba(140, 200, 255, .12));
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}
.tripStop:hover {
  z-index: 2;
  border-color: rgba(202, 132, 255, .48);
  background: linear-gradient(90deg, rgba(32, 41, 56, .99), rgba(45, 55, 72, .99));
  box-shadow: 0 9px 20px rgba(175, 92, 230, .18);
}
.tripStopCurrent {
  border-color: rgba(180, 235, 255, .72);
  background: linear-gradient(90deg, rgba(34, 55, 72, .99), rgba(59, 48, 82, .99));
  box-shadow: 0 0 0 1px rgba(180, 235, 255, .24), 0 10px 22px rgba(175, 92, 230, .18);
}
.tripStopCurrent::before {
  background: linear-gradient(180deg, #d8f6ff, #c783ff);
}
.tripStopName {
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tripStopStationHint {
  color: #ecc9ff;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tripStopMeta,
.tripStopVisit {
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tripStopApproxJumps {
  cursor: help;
  font-style: italic;
  text-decoration: underline dashed rgba(202, 132, 255, .75);
  text-underline-offset: 2px;
}
.tripStopPager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex-wrap: wrap;
  min-height: 24px;
}
.tripStopPagerButton {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 24px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: var(--muted);
  font-size: 22px;
  line-height: 1;
}
.tripStopPagerButton:hover {
  color: var(--accent);
  background: rgba(140, 200, 255, .10);
}
.tripStopDot {
  position: relative;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
}
.tripStopDot::before {
  content: "";
  display: block;
  width: 8px;
  height: 8px;
  margin: 6px;
  border-radius: 999px;
  background: rgba(140, 200, 255, .28);
}
.tripStopDot:hover,
.tripStopDotCurrent {
  background: rgba(140, 200, 255, .08);
}
.tripStopDot:hover::before,
.tripStopDotCurrent::before {
  background: #ca84ff;
  box-shadow: 0 0 0 3px rgba(202, 132, 255, .18);
}
.tripStopDotDisabled {
  cursor: default;
}
.tripStopDotDisabled:hover {
  background: rgba(140, 200, 255, .08);
}
.tripStopDotCommander {
  outline: 1px solid rgba(216, 246, 255, .72);
  outline-offset: 2px;
}
@media (max-width: 980px) {
  .tripRouteLayout {
    grid-template-columns: 1fr;
  }
  .tripRouteInfoPane {
    padding-right: 0;
    padding-bottom: 7px;
    border-right: 0;
    border-bottom: 1px solid rgba(140, 200, 255, .22);
  }
}
</style>
