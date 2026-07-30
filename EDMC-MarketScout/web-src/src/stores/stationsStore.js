import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useCommoditySettingsStore } from './commoditySettingsStore.js'
import { useStatusStore } from './statusStore.js'
import { dedupeStationRows, query } from '../utils.js'

const DEFAULT_STATION_ROW_LIMIT = 30

function afterBrowserPaint() {
  return new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
}

export const useStationsStore = defineStore('stations', () => {
  const rows = ref([])
  const selectedIndex = ref(-1)
  const stationPage = ref({ totalCount: 0, hasMore: false, nextOffset: null, limit: DEFAULT_STATION_ROW_LIMIT, offset: 0 })
  const stationRowsLoading = ref(false)
  const stationRowsRendering = ref(false)
  let latestRowsRequestId = 0

  const selectedRow = computed(() => selectedIndex.value >= 0 ? rows.value[selectedIndex.value] : null)
  const stationStatusLabel = computed(() => {
    const total = Number(stationPage.value.totalCount || rows.value.length)
    const shown = rows.value.length
    if (total && shown < total) return `Showing ${shown.toLocaleString()} of ${total.toLocaleString()} stations`
    return `${shown.toLocaleString()} stations`
  })
  const loadMoreLabel = computed(() => (
    stationPage.value.hasMore
      ? `Load More (${rows.value.length.toLocaleString()} of ${Number(stationPage.value.totalCount || 0).toLocaleString()})`
      : `Showing ${rows.value.length.toLocaleString()} station${rows.value.length === 1 ? '' : 's'}`
  ))

  function setSelectedIndex(index) {
    selectedIndex.value = index
  }

  function closeDetails() {
    selectedIndex.value = -1
  }

  function beginStationRowsLoad(options = {}) {
    const preserveRows = options.preserveRows === true
    if (!preserveRows) {
      selectedIndex.value = -1
      rows.value = []
    }
    latestRowsRequestId += 1
    return latestRowsRequestId
  }

  function isActiveRowsLoad(requestId) {
    return requestId === latestRowsRequestId
  }

  async function loadStations(options = {}) {
    const statusStore = useStatusStore()
    const commoditySettingsStore = useCommoditySettingsStore()
    const append = options.append === true
    const rowLimit = Number(options.rowLimit || DEFAULT_STATION_ROW_LIMIT)
    const offset = append ? Number(stationPage.value.nextOffset || rows.value.length || 0) : 0
    const requestLimit = append ? rowLimit : (options.preserveRows ? Math.max(rowLimit, rows.value.length || 0) : rowLimit)
    const requestId = beginStationRowsLoad({ ...options, preserveRows: append || options.preserveRows })
    stationRowsLoading.value = true
    if (!append) {
      stationPage.value = { totalCount: 0, hasMore: false, nextOffset: null, limit: requestLimit, offset: 0 }
    }
    statusStore.statusText = append ? `${stationStatusLabel.value} · Loading more...` : 'Loading stations...'
    try {
      const params = typeof options.params === 'function' ? options.params(offset, requestLimit) : { ...(options.params || {}), offset, limit: requestLimit }
      const res = await fetch(`/api/stations?${query(params)}`, { cache: 'no-store' })
      const data = await res.json()
      if (!isActiveRowsLoad(requestId)) return
      const nextRows = data.rows || []
      rows.value = append ? dedupeStationRows([...rows.value, ...nextRows]) : dedupeStationRows(nextRows)
      commoditySettingsStore.applyWatchedCommoditiesFromStations(data.watched_commodities)
      stationPage.value = {
        totalCount: Number(data.total_count || rows.value.length),
        hasMore: Boolean(data.has_more),
        nextOffset: data.next_offset ?? null,
        limit: Number(data.limit || rowLimit),
        offset: Number(data.offset || offset),
      }
      await afterBrowserPaint()
      statusStore.statusText = `${stationStatusLabel.value} · ${new Date().toLocaleTimeString()}`
    } finally {
      if (isActiveRowsLoad(requestId)) stationRowsLoading.value = false
    }
  }

  async function loadMoreStations(options = {}) {
    if (!stationPage.value.hasMore || stationRowsLoading.value) return
    await loadStations({ ...options, append: true })
  }

  async function renderStationRows(change) {
    stationRowsRendering.value = true
    try {
      if (typeof change === 'function') change()
      await afterBrowserPaint()
    } finally {
      stationRowsRendering.value = false
    }
  }

  return {
    rows,
    selectedIndex,
    selectedRow,
    stationPage,
    stationRowsLoading,
    stationRowsRendering,
    stationStatusLabel,
    loadMoreLabel,
    setSelectedIndex,
    closeDetails,
    loadStations,
    loadMoreStations,
    renderStationRows,
  }
})
