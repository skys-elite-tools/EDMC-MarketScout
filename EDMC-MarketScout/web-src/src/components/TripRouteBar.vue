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
const emit = defineEmits(['import-route', 'start-route', 'delete-route', 'select-stop', 'open-help'])

const fileInput = ref(null)
const menuOpen = ref(false)
const menuEl = ref(null)
const stopsEl = ref(null)
const stopEls = ref([])
const expanded = ref(Boolean(dataStore.cached(EXPANDED_STORAGE_KEY, false)))
const focusedStopIndex = ref(0)
const visibleStopIndexes = ref([])

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

async function importFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const content = await file.text()
  emit('import-route', { filename: file.name, content })
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
    <button type="button" class="tripRouteToggle" :aria-expanded="expanded" @click="toggleExpanded">
      <span class="tripRouteToggleArrow">{{ expanded ? '▲' : '▼' }}</span>
      <span>Trip Planner</span>
      <span class="tripRouteToggleArrow">{{ expanded ? '▲' : '▼' }}</span>
    </button>

    <div v-if="expanded" class="tripRouteLayout">
      <div class="tripRouteInfoPane">
        <div class="tripRouteHeader">
          <div class="tripRouteTitle">
            <span>Trip Route</span>
            <InfoButton title="Spansh Tourist Route imports" @open="emit('open-help', 'spansh-tourist-route')" />
          </div>
          <div class="tripRouteActions">
            <button
              type="button"
              class="tripRouteImportButton"
              :disabled="busy"
              title="Import a .json file downloaded from the Spansh Tourist Route planner."
              @click="chooseFile"
            >
              Add Spansh Tourist Route
            </button>
            <input ref="fileInput" class="hiddenFileInput" type="file" accept="application/json,.json" @change="importFile" />
            <div ref="menuEl" class="tripRouteMenuWrap">
              <button type="button" class="tripRouteMenuButton" :disabled="busy || !routes.length" @click.stop="menuOpen = !menuOpen">
                Routes
                <span class="buttonCount">{{ routes.length }}</span>
              </button>
              <div v-if="menuOpen" class="tripRouteMenu">
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
