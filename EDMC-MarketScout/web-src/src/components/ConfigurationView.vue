<script setup>
import { computed, onMounted, ref } from 'vue'

const loading = ref(true)
const saving = ref(false)
const status = ref('')
const error = ref('')
const bindAddress = ref('127.0.0.1')
const bindPort = ref(40595)
const active = ref({})
const defaults = ref({ bind_address: '127.0.0.1', bind_port: 40595 })
const suggestions = ref(['127.0.0.1', 'localhost'])
const mdns = ref({})
const configFile = ref('marketscout.config')
const urlCopied = ref(false)

const shareUrl = computed(() => `http://${bindAddress.value || defaults.value.bind_address}:${bindPort.value || defaults.value.bind_port}/`)
const isShareableAddress = computed(() => {
  const value = String(bindAddress.value || '').trim().toLowerCase()
  const parts = value.split('.')
  if (value === 'localhost' || value === '0.0.0.0' || value.includes(':')) return false
  if (parts.length !== 4) return false
  const numbers = parts.map((part) => Number(part))
  if (numbers.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false
  if (numbers[0] === 127) return false
  if (numbers[0] === 169 && numbers[1] === 254) return false
  return true
})
const qrCode = computed(() => makeQrCode(shareUrl.value))

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/config', { cache: 'no-store' })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not load configuration')
    bindAddress.value = data.config?.bind_address || defaults.value.bind_address
    bindPort.value = data.config?.bind_port || defaults.value.bind_port
    active.value = data.active || {}
    defaults.value = data.defaults || defaults.value
    suggestions.value = data.suggested_bind_addresses || suggestions.value
    mdns.value = data.mdns || {}
    configFile.value = data.config_file || configFile.value
  } catch (err) {
    error.value = String(err?.message || err)
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  status.value = ''
  error.value = ''
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bind_address: bindAddress.value,
        bind_port: bindPort.value,
      }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not save configuration')
    bindAddress.value = data.config?.bind_address || bindAddress.value
    bindPort.value = data.config?.bind_port || bindPort.value
    status.value = data.message || 'Saved.'
  } catch (err) {
    error.value = String(err?.message || err)
  } finally {
    saving.value = false
  }
}

function useAddress(value) {
  bindAddress.value = value
}

onMounted(loadConfig)

async function copyShareUrl() {
  await navigator.clipboard.writeText(shareUrl.value)
  urlCopied.value = true
  setTimeout(() => { urlCopied.value = false }, 1800)
}

function makeQrCode(text) {
  const version = 4
  const size = version * 4 + 17
  const dataCodewords = 80
  const eccCodewords = 20
  const modules = Array.from({ length: size }, () => Array(size).fill(false))
  const reserved = Array.from({ length: size }, () => Array(size).fill(false))

  function set(row, col, value, reserve = true) {
    if (row < 0 || col < 0 || row >= size || col >= size) return
    modules[row][col] = Boolean(value)
    if (reserve) reserved[row][col] = true
  }

  function addFinder(row, col) {
    for (let y = -1; y <= 7; y += 1) {
      for (let x = -1; x <= 7; x += 1) {
        const r = row + y
        const c = col + x
        const black = x >= 0 && x <= 6 && y >= 0 && y <= 6 && (x === 0 || x === 6 || y === 0 || y === 6 || (x >= 2 && x <= 4 && y >= 2 && y <= 4))
        set(r, c, black)
      }
    }
  }

  function addAlignment(row, col) {
    for (let y = -2; y <= 2; y += 1) {
      for (let x = -2; x <= 2; x += 1) {
        set(row + y, col + x, Math.max(Math.abs(x), Math.abs(y)) !== 1)
      }
    }
  }

  addFinder(0, 0)
  addFinder(0, size - 7)
  addFinder(size - 7, 0)
  addAlignment(26, 26)
  for (let i = 8; i < size - 8; i += 1) {
    set(6, i, i % 2 === 0)
    set(i, 6, i % 2 === 0)
  }
  set(size - 8, 8, true)
  for (let i = 0; i < 9; i += 1) {
    if (i !== 6) {
      reserved[8][i] = true
      reserved[i][8] = true
    }
  }
  for (let i = 0; i < 8; i += 1) {
    reserved[8][size - 1 - i] = true
    reserved[size - 1 - i][8] = true
  }

  const data = encodeQrData(text, dataCodewords)
  const ecc = reedSolomonRemainder(data, eccCodewords)
  const bits = [...data, ...ecc].flatMap(byte => Array.from({ length: 8 }, (_, i) => ((byte >>> (7 - i)) & 1) === 1))
  let bitIndex = 0
  let upward = true
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1
    for (let vert = 0; vert < size; vert += 1) {
      const row = upward ? size - 1 - vert : vert
      for (let j = 0; j < 2; j += 1) {
        const col = right - j
        if (reserved[row][col]) continue
        modules[row][col] = bitIndex < bits.length ? bits[bitIndex] : false
        bitIndex += 1
      }
    }
    upward = !upward
  }

  let bestModules = modules
  let bestMask = 0
  let bestPenalty = Infinity
  for (let mask = 0; mask < 8; mask += 1) {
    const candidate = modules.map(row => row.slice())
    for (let r = 0; r < size; r += 1) {
      for (let c = 0; c < size; c += 1) {
        if (!reserved[r][c] && maskApplies(mask, r, c)) candidate[r][c] = !candidate[r][c]
      }
    }
    drawFormatBits(candidate, reserved, mask)
    const penalty = qrPenalty(candidate)
    if (penalty < bestPenalty) {
      bestPenalty = penalty
      bestMask = mask
      bestModules = candidate
    }
  }
  drawFormatBits(bestModules, reserved, bestMask)
  return { size, cells: bestModules.flat() }
}

function encodeQrData(text, dataCodewords) {
  const bytes = Array.from(new TextEncoder().encode(text)).slice(0, 78)
  const bits = [0, 1, 0, 0]
  for (let i = 7; i >= 0; i -= 1) bits.push((bytes.length >>> i) & 1)
  for (const byte of bytes) {
    for (let i = 7; i >= 0; i -= 1) bits.push((byte >>> i) & 1)
  }
  const capacity = dataCodewords * 8
  for (let i = 0; i < 4 && bits.length < capacity; i += 1) bits.push(0)
  while (bits.length % 8 !== 0) bits.push(0)
  const data = []
  for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((acc, bit) => (acc << 1) | bit, 0))
  for (let pad = 0; data.length < dataCodewords; pad += 1) data.push(pad % 2 === 0 ? 0xec : 0x11)
  return data
}

function gfMultiply(x, y) {
  let z = 0
  for (let i = 7; i >= 0; i -= 1) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d)
    if (((y >>> i) & 1) !== 0) z ^= x
  }
  return z & 0xff
}

function reedSolomonGenerator(degree) {
  const result = Array(degree).fill(0)
  result[degree - 1] = 1
  let root = 1
  for (let i = 0; i < degree; i += 1) {
    for (let j = 0; j < degree; j += 1) {
      result[j] = gfMultiply(result[j], root)
      if (j + 1 < degree) result[j] ^= result[j + 1]
    }
    root = gfMultiply(root, 2)
  }
  return result
}

function reedSolomonRemainder(data, degree) {
  const generator = reedSolomonGenerator(degree)
  const result = Array(degree).fill(0)
  for (const byte of data) {
    const factor = byte ^ result.shift()
    result.push(0)
    for (let i = 0; i < degree; i += 1) result[i] ^= gfMultiply(generator[i], factor)
  }
  return result
}

function maskApplies(mask, row, col) {
  if (mask === 0) return (row + col) % 2 === 0
  if (mask === 1) return row % 2 === 0
  if (mask === 2) return col % 3 === 0
  if (mask === 3) return (row + col) % 3 === 0
  if (mask === 4) return (Math.floor(row / 2) + Math.floor(col / 3)) % 2 === 0
  if (mask === 5) return ((row * col) % 2) + ((row * col) % 3) === 0
  if (mask === 6) return (((row * col) % 2) + ((row * col) % 3)) % 2 === 0
  return (((row + col) % 2) + ((row * col) % 3)) % 2 === 0
}

function drawFormatBits(modules, reserved, mask) {
  let data = (1 << 3) | mask
  let rem = data
  for (let i = 0; i < 10; i += 1) rem = (rem << 1) ^ (((rem >>> 9) & 1) * 0x537)
  const bits = ((data << 10) | rem) ^ 0x5412
  const size = modules.length
  const coords1 = [[8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8], [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8]]
  const coords2 = [[size - 1, 8], [size - 2, 8], [size - 3, 8], [size - 4, 8], [size - 5, 8], [size - 6, 8], [size - 7, 8], [size - 8, 8], [8, size - 7], [8, size - 6], [8, size - 5], [8, size - 4], [8, size - 3], [8, size - 2], [8, size - 1]]
  coords1.forEach(([r, c], i) => {
    modules[r][c] = ((bits >>> i) & 1) !== 0
    reserved[r][c] = true
  })
  coords2.forEach(([r, c], i) => {
    modules[r][c] = ((bits >>> i) & 1) !== 0
    reserved[r][c] = true
  })
}

function qrPenalty(modules) {
  const size = modules.length
  let penalty = 0
  for (let pass = 0; pass < 2; pass += 1) {
    for (let i = 0; i < size; i += 1) {
      let runColor = false
      let runLen = 0
      for (let j = 0; j < size; j += 1) {
        const color = pass === 0 ? modules[i][j] : modules[j][i]
        if (j === 0 || color !== runColor) {
          runColor = color
          runLen = 1
        } else {
          runLen += 1
          if (runLen === 5) penalty += 3
          else if (runLen > 5) penalty += 1
        }
      }
    }
  }
  for (let r = 0; r < size - 1; r += 1) {
    for (let c = 0; c < size - 1; c += 1) {
      const color = modules[r][c]
      if (color === modules[r + 1][c] && color === modules[r][c + 1] && color === modules[r + 1][c + 1]) penalty += 3
    }
  }
  const finderPattern = [true, false, true, true, true, false, true, false, false, false, false]
  for (let pass = 0; pass < 2; pass += 1) {
    for (let i = 0; i < size; i += 1) {
      for (let j = 0; j <= size - 11; j += 1) {
        const slice = Array.from({ length: 11 }, (_, k) => (pass === 0 ? modules[i][j + k] : modules[j + k][i]))
        if (slice.every((v, k) => v === finderPattern[k]) || slice.every((v, k) => v === finderPattern[10 - k])) penalty += 40
      }
    }
  }
  const dark = modules.flat().filter(Boolean).length
  penalty += Math.floor(Math.abs(dark * 20 - size * size * 10) / (size * size)) * 10
  return penalty
}
</script>

<template>
  <section class="configurationView">
    <fieldset class="configurationPanel">
      <legend>Configuration</legend>
      <div class="configurationIntro">
        <p>MarketScout stores app-level configuration in <code>{{ configFile }}</code> in the plugin folder. Listening address and port changes are applied after restarting EDMC.</p>
        <p v-if="active.url">Current Web UI: <strong>{{ active.url }}</strong></p>
      </div>

      <div v-if="loading" class="placeholderBox">Loading configuration…</div>
      <template v-else>
        <div class="configurationGrid">
          <label>Listening address
            <input v-model="bindAddress" type="text" list="bindAddressSuggestions" />
          </label>
          <datalist id="bindAddressSuggestions">
            <option v-for="value in suggestions" :key="value" :value="value" />
          </datalist>

          <label>Listening port
            <input v-model.number="bindPort" type="number" min="1" max="65535" />
          </label>
        </div>

        <div class="suggestedAddresses">
          <span>Quick fill</span>
          <button v-for="value in suggestions" :key="value" type="button" @click="useAddress(value)">{{ value }}</button>
        </div>

        <div class="configurationActions">
          <button type="button" :disabled="saving" @click="saveConfig">{{ saving ? 'Saving…' : 'Save Configuration' }}</button>
          <button type="button" @click="loadConfig">Reload</button>
          <span v-if="status" class="configStatus">{{ status }}</span>
          <span v-if="error" class="configError">{{ error }}</span>
        </div>

        <div v-if="isShareableAddress" class="qrSharePanel">
          <div>
            <h3>Open From Another Device</h3>
            <p>Scan this QR code from a device on the same network. It uses the address and port currently shown above.</p>
            <p class="shareUrl">{{ shareUrl }}</p>
            <button type="button" @click="copyShareUrl">{{ urlCopied ? 'Copied' : 'Copy URL' }}</button>
          </div>
          <div class="qrCode" :style="{ '--qr-size': qrCode.size }" :aria-label="`QR code for ${shareUrl}`">
            <span
              v-for="(cell, index) in qrCode.cells"
              :key="index"
              :class="{ on: cell }"
            ></span>
          </div>
        </div>
        <div v-else class="qrSharePanel qrSharePanelMuted">
          <div>
            <h3>Open From Another Device</h3>
            <p>Choose a LAN IPv4 address, such as a 192.168.x.x or 10.x.x.x address, to show a QR code for another device.</p>
            <p class="shareUrl">{{ shareUrl }}</p>
          </div>
        </div>
      </template>
    </fieldset>

    <fieldset class="configurationPanel">
      <legend>Network Notes</legend>
      <p><strong>127.0.0.1</strong> keeps MarketScout available only on this computer.</p>
      <p><strong>localhost</strong> also points to this computer, but browser localStorage is stored separately from 127.0.0.1.</p>
      <p>Using a LAN IP can make the Web UI reachable from other devices on your local network. Only use that intentionally.</p>
      <p><strong>{{ mdns.name || 'marketscout.local' }}</strong>: {{ mdns.message || 'mDNS advertising is not enabled.' }}</p>
    </fieldset>
  </section>
</template>
