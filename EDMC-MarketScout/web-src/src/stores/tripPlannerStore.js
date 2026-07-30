import { defineStore } from 'pinia'
import { onScopeDispose, ref } from 'vue'

export const useTripPlannerStore = defineStore('tripPlanner', () => {
  const tripRoutes = ref([])
  const activeTripRoute = ref(null)
  const tripRouteBusy = ref(false)
  const tripRouteStatus = ref('')
  let statusTimer = null
  let stopSelectionHandler = null

  function clearStatusTimer() {
    if (!statusTimer) return
    clearTimeout(statusTimer)
    statusTimer = null
  }

  function setTripRouteStatus(message, options = {}) {
    clearStatusTimer()
    tripRouteStatus.value = message || ''
    const timeoutMs = Number(options.timeoutMs || 0)
    if (tripRouteStatus.value && timeoutMs > 0) {
      statusTimer = setTimeout(() => {
        tripRouteStatus.value = ''
        statusTimer = null
      }, timeoutMs)
    }
  }

  function setTripRouteData(data) {
    tripRoutes.value = data?.routes || []
    activeTripRoute.value = data?.active_route || null
  }

  async function loadTripRoutes() {
    const res = await fetch('/api/trip-routes', { cache: 'no-store' })
    const data = await res.json()
    setTripRouteData(data)
    return data
  }

  async function importTripRoute(file) {
    tripRouteBusy.value = true
    setTripRouteStatus('Importing route...')
    try {
      const res = await fetch('/api/trip-routes/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(file),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not import route')
      await loadTripRoutes()
      setTripRouteStatus(`Imported ${data.imported_stops || 0} route stops.`, { timeoutMs: 3200 })
      return data
    } catch (err) {
      setTripRouteStatus(err?.message || String(err))
      return null
    } finally {
      tripRouteBusy.value = false
    }
  }

  async function importTripRouteStationHints(file) {
    tripRouteBusy.value = true
    setTripRouteStatus('Importing station hints...')
    try {
      const res = await fetch('/api/trip-routes/import-station-hints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(file),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not import station hints')
      setTripRouteData(data)
      setTripRouteStatus(`Added station hints to ${data.matched_stops || 0} route stops.`, { timeoutMs: 3200 })
      return data
    } catch (err) {
      setTripRouteStatus(err?.message || String(err))
      return null
    } finally {
      tripRouteBusy.value = false
    }
  }

  async function setTripRouteStationsHints(file) {
    return importTripRouteStationHints(file)
  }

  async function startTripRoute(routeId) {
    tripRouteBusy.value = true
    try {
      const res = await fetch('/api/trip-routes/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ route_id: routeId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not start route')
      setTripRouteData(data)
      return data
    } catch (err) {
      setTripRouteStatus(err?.message || String(err))
      return null
    } finally {
      tripRouteBusy.value = false
    }
  }

  async function setTripRouteStopSkipped(payload) {
    tripRouteBusy.value = true
    try {
      const res = await fetch('/api/trip-routes/skip-stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not update route stop')
      setTripRouteData(data)
      setTripRouteStatus(payload?.skipped ? 'Route stop skipped.' : 'Route stop restored.', { timeoutMs: 2600 })
      return data
    } catch (err) {
      setTripRouteStatus(err?.message || String(err))
      return null
    } finally {
      tripRouteBusy.value = false
    }
  }

  async function deleteTripRoute(routeId) {
    tripRouteBusy.value = true
    try {
      const res = await fetch('/api/trip-routes/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ route_id: routeId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not delete route')
      setTripRouteData(data)
      return data
    } catch (err) {
      setTripRouteStatus(err?.message || String(err))
      return null
    } finally {
      tripRouteBusy.value = false
    }
  }

  function setTripRouteStopSelectionHandler(handler) {
    stopSelectionHandler = typeof handler === 'function' ? handler : null
  }

  async function selectTripRouteStop(stop) {
    if (typeof stopSelectionHandler !== 'function') return
    await stopSelectionHandler(stop)
  }

  onScopeDispose(() => {
    clearStatusTimer()
    stopSelectionHandler = null
  })

  return {
    tripRoutes,
    activeTripRoute,
    tripRouteBusy,
    tripRouteStatus,
    loadTripRoutes,
    importTripRoute,
    importTripRouteStationHints,
    setTripRouteStationsHints,
    startTripRoute,
    setTripRouteStopSkipped,
    deleteTripRoute,
    setTripRouteStopSelectionHandler,
    selectTripRouteStop,
  }
})
