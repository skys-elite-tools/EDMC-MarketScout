import { defineStore } from 'pinia'
import { onScopeDispose, ref } from 'vue'

export const useCarrierTripPlannerStore = defineStore('carrierTripPlanner', () => {
  const carrierTripRoutes = ref([])
  const activeCarrierTrips = ref([])
  const activeCarrierTrip = ref(null)
  const selectedCarrierTripId = ref(null)
  const carrierTripBusy = ref(false)
  const carrierTripStatus = ref('')
  let statusTimer = null

  function clearStatusTimer() {
    if (!statusTimer) return
    clearTimeout(statusTimer)
    statusTimer = null
  }

  function setStatus(message, options = {}) {
    clearStatusTimer()
    carrierTripStatus.value = message || ''
    const timeoutMs = Number(options.timeoutMs || 0)
    if (carrierTripStatus.value && timeoutMs > 0) {
      statusTimer = setTimeout(() => {
        carrierTripStatus.value = ''
        statusTimer = null
      }, timeoutMs)
    }
  }

  function setData(data) {
    carrierTripRoutes.value = Array.isArray(data?.routes) ? data.routes : []
    activeCarrierTrips.value = Array.isArray(data?.active_routes)
      ? data.active_routes
      : (data?.active_route ? [data.active_route] : [])
    const selected = activeCarrierTrips.value.find(
      route => route.carrier_trip_id === selectedCarrierTripId.value,
    ) || activeCarrierTrips.value[0] || null
    activeCarrierTrip.value = selected
    selectedCarrierTripId.value = selected?.carrier_trip_id || null
  }

  function selectCarrierTrip(carrierTripId) {
    const selected = activeCarrierTrips.value.find(route => route.carrier_trip_id === carrierTripId) || null
    activeCarrierTrip.value = selected
    selectedCarrierTripId.value = selected?.carrier_trip_id || null
  }

  async function loadCarrierTrips() {
    const res = await fetch('/api/carrier-trips', { cache: 'no-store' })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not load Carrier Trips')
    setData(data)
    return data
  }

  async function importCarrierTrip(file) {
    carrierTripBusy.value = true
    setStatus('Importing Fleet Carrier route...')
    try {
      const res = await fetch('/api/carrier-trips/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(file),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not import Fleet Carrier route')
      await loadCarrierTrips()
      setStatus(`Imported ${data.imported_stops || 0} carrier route stops.`, { timeoutMs: 3200 })
      return data
    } catch (err) {
      setStatus(err?.message || String(err))
      return null
    } finally {
      carrierTripBusy.value = false
    }
  }

  async function startCarrierTrip(carrierTripId) {
    carrierTripBusy.value = true
    selectedCarrierTripId.value = carrierTripId
    try {
      const res = await fetch('/api/carrier-trips/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ carrier_trip_id: carrierTripId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not start Carrier Trip')
      setData(data)
      return data
    } catch (err) {
      setStatus(err?.message || String(err))
      return null
    } finally {
      carrierTripBusy.value = false
    }
  }

  async function stopCarrierTrip(carrierTripId) {
    carrierTripBusy.value = true
    try {
      const res = await fetch('/api/carrier-trips/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ carrier_trip_id: carrierTripId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not pause Carrier Trip')
      setData(data)
      return data
    } catch (err) {
      setStatus(err?.message || String(err))
      return null
    } finally {
      carrierTripBusy.value = false
    }
  }

  async function setStopSkipped(payload) {
    carrierTripBusy.value = true
    try {
      const res = await fetch('/api/carrier-trips/skip-stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not update carrier route stop')
      setData(data)
      setStatus(payload?.skipped ? 'Carrier route stop skipped.' : 'Carrier route stop restored.', { timeoutMs: 2600 })
      return data
    } catch (err) {
      setStatus(err?.message || String(err))
      return null
    } finally {
      carrierTripBusy.value = false
    }
  }

  async function deleteCarrierTrip(carrierTripId) {
    carrierTripBusy.value = true
    try {
      const res = await fetch('/api/carrier-trips/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ carrier_trip_id: carrierTripId }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not delete Carrier Trip')
      setData(data)
      return data
    } catch (err) {
      setStatus(err?.message || String(err))
      return null
    } finally {
      carrierTripBusy.value = false
    }
  }

  onScopeDispose(() => clearStatusTimer())

  return {
    carrierTripRoutes,
    activeCarrierTrips,
    activeCarrierTrip,
    selectedCarrierTripId,
    carrierTripBusy,
    carrierTripStatus,
    loadCarrierTrips,
    importCarrierTrip,
    startCarrierTrip,
    stopCarrierTrip,
    selectCarrierTrip,
    setStopSkipped,
    deleteCarrierTrip,
  }
})
