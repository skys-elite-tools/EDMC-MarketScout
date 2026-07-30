import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useStatusStore = defineStore('status', () => {
  const autoRefresh = ref(true)
  const statusText = ref('Loading...')
  const latestJournalEvent = ref(null)
  const edmcStatus = ref(null)
  const updateStatus = ref(null)
  const updateBusy = ref(false)
  const edmcDiscardBusy = ref(false)
  const lastDataVersion = ref(null)
  let statusRefreshHandler = null

  function setStatusRefreshHandler(handler) {
    statusRefreshHandler = typeof handler === 'function' ? handler : null
  }

  async function pollStatus(options = {}) {
    const res = await fetch('/api/status', { cache: 'no-store' })
    const data = await res.json()
    latestJournalEvent.value = data.latest_journal_event || null
    edmcStatus.value = data.edmc || null
    updateStatus.value = data.update || null
    if (typeof options.onTargetStateAlert === 'function') {
      options.onTargetStateAlert(data.current_system_target_state_alert || null)
    }
    if (!autoRefresh.value) {
      lastDataVersion.value = data.data_version
      return data
    }
    if (
      lastDataVersion.value !== null
      && data.data_version !== lastDataVersion.value
      && typeof options.onDataVersionChanged === 'function'
    ) {
      await options.onDataVersionChanged(data)
    }
    lastDataVersion.value = data.data_version
    return data
  }

  async function discardEdmcDelayedStationMessages(options = {}) {
    edmcDiscardBusy.value = true
    try {
      const res = await fetch('/api/edmc/eddn/discard-delayed-station-messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Could not clear delayed EDDN station messages')
      statusText.value = `Cleared ${Number(data.discarded || 0)} delayed EDDN station message(s) · ${new Date().toLocaleTimeString()}`
      const refresh = typeof options.refresh === 'function' ? options.refresh : statusRefreshHandler
      if (typeof refresh === 'function') await refresh()
    } catch (err) {
      statusText.value = `${err?.message || err} · ${new Date().toLocaleTimeString()}`
    } finally {
      edmcDiscardBusy.value = false
    }
  }

  return {
    autoRefresh,
    statusText,
    latestJournalEvent,
    edmcStatus,
    updateStatus,
    updateBusy,
    edmcDiscardBusy,
    setStatusRefreshHandler,
    pollStatus,
    discardEdmcDelayedStationMessages,
  }
})
