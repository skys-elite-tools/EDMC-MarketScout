const STORE_PREFIX = 'marketscout.datastore.'
const REMOTE_DEBOUNCE_MS = 30000

function nowIso() {
  return new Date().toISOString()
}

function storage() {
  try {
    const testKey = `${STORE_PREFIX}test`
    window.localStorage.setItem(testKey, '1')
    window.localStorage.removeItem(testKey)
    return window.localStorage
  } catch (err) {
    return null
  }
}

function localStoreKey(key) {
  return `${STORE_PREFIX}${key}`
}

function parseJson(value, fallback) {
  try {
    return JSON.parse(value)
  } catch (err) {
    return fallback
  }
}

function asTime(value) {
  const time = Date.parse(value || '')
  return Number.isFinite(time) ? time : 0
}

function clone(value) {
  try {
    return JSON.parse(JSON.stringify(value))
  } catch (err) {
    return value
  }
}

class DataStoreService {
  constructor() {
    this.local = storage()
    this.remoteAvailable = null
    this.pendingRemote = new Map()
    this.flushTimer = null

    if (typeof window !== 'undefined') {
      window.addEventListener('pagehide', () => this.flushNow())
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') this.flushNow()
      })
    }
  }

  cached(key, defaultValue, options = {}) {
    const localEntry = this.readLocalEntry(key, options)
    return localEntry ? clone(localEntry.value) : clone(defaultValue)
  }

  async get(key, defaultValue, options = {}) {
    const localEntry = this.readLocalEntry(key, options)
    const remoteEntry = await this.readRemoteEntry(key)

    if (localEntry && remoteEntry) {
      if (asTime(localEntry.updated_datetime) >= asTime(remoteEntry.updated_datetime)) {
        this.queueRemote(key, localEntry.value, localEntry.updated_datetime)
        return clone(localEntry.value)
      }
      this.writeLocalEntry(key, remoteEntry.value, remoteEntry.updated_datetime)
      return clone(remoteEntry.value)
    }

    if (localEntry) {
      this.queueRemote(key, localEntry.value, localEntry.updated_datetime)
      return clone(localEntry.value)
    }

    if (remoteEntry) {
      this.writeLocalEntry(key, remoteEntry.value, remoteEntry.updated_datetime)
      return clone(remoteEntry.value)
    }

    return clone(defaultValue)
  }

  set(key, value, options = {}) {
    const updatedAt = nowIso()
    this.writeLocalEntry(key, value, updatedAt)
    if (options.remote !== false) {
      this.queueRemote(key, value, updatedAt, options.debounceMs)
    }
  }

  async flushNow() {
    if (!this.pendingRemote.size) return
    const entries = {}
    for (const [key, entry] of this.pendingRemote.entries()) entries[key] = entry
    this.pendingRemote.clear()
    if (this.flushTimer) {
      window.clearTimeout(this.flushTimer)
      this.flushTimer = null
    }
    await this.writeRemoteValues(entries)
  }

  readLocalEntry(key, options = {}) {
    if (!this.local) return null

    const canonical = parseJson(this.local.getItem(localStoreKey(key)) || '', null)
    if (canonical && typeof canonical === 'object' && Object.prototype.hasOwnProperty.call(canonical, 'value')) {
      return {
        value: canonical.value,
        updated_datetime: canonical.updated_datetime || '',
      }
    }

    const legacyKey = options.legacyKey
    if (legacyKey) {
      const legacyRaw = this.local.getItem(legacyKey)
      if (legacyRaw !== null) {
        const value = options.legacyJson === false ? legacyRaw : parseJson(legacyRaw, legacyRaw)
        const entry = { value, updated_datetime: nowIso() }
        this.writeLocalEntry(key, entry.value, entry.updated_datetime)
        return entry
      }
    }

    return null
  }

  writeLocalEntry(key, value, updatedAt = nowIso()) {
    if (!this.local) return
    try {
      this.local.setItem(localStoreKey(key), JSON.stringify({
        value,
        updated_datetime: updatedAt,
        schema_version: 1,
      }))
    } catch (err) {
      // Large values, especially uploaded poster images, can exceed browser quota.
    }
  }

  async readRemoteEntry(key) {
    const values = await this.readRemoteValues([key])
    return values[key] || null
  }

  async readRemoteValues(keys) {
    if (this.remoteAvailable === false) return {}
    try {
      const params = new URLSearchParams({ keys: keys.join(',') })
      const res = await fetch(`/api/user-data?${params}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (!data.ok || !data.values || typeof data.values !== 'object') throw new Error(data.error || 'Invalid user-data response')
      this.remoteAvailable = true
      return data.values
    } catch (err) {
      this.remoteAvailable = false
      return {}
    }
  }

  queueRemote(key, value, updatedAt = nowIso(), debounceMs = REMOTE_DEBOUNCE_MS) {
    if (this.remoteAvailable === false) return
    this.pendingRemote.set(key, {
      value: clone(value),
      updated_datetime: updatedAt,
      schema_version: 1,
    })
    if (this.flushTimer) window.clearTimeout(this.flushTimer)
    if (debounceMs <= 0) {
      this.flushNow()
      return
    }
    this.flushTimer = window.setTimeout(() => this.flushNow(), debounceMs)
  }

  async writeRemoteValues(entries) {
    if (this.remoteAvailable === false) return false
    try {
      const res = await fetch('/api/user-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries }),
      })
      const data = await res.json()
      if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`)
      if (data.values && typeof data.values === 'object') {
        for (const [key, entry] of Object.entries(data.values)) {
          if (entry && typeof entry === 'object' && Object.prototype.hasOwnProperty.call(entry, 'value')) {
            this.writeLocalEntry(key, entry.value, entry.updated_datetime || nowIso())
          }
        }
      }
      this.remoteAvailable = true
      return true
    } catch (err) {
      this.remoteAvailable = false
      return false
    }
  }
}

export const dataStore = new DataStoreService()
