<script setup>
import QRCode from 'qrcode'
import { computed, onMounted, ref, watch } from 'vue'

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
const qrDataUrl = ref('')
const qrError = ref('')

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

watch([shareUrl, isShareableAddress], async () => {
  qrDataUrl.value = ''
  qrError.value = ''
  if (!isShareableAddress.value) return
  try {
    qrDataUrl.value = await QRCode.toDataURL(shareUrl.value, {
      errorCorrectionLevel: 'M',
      margin: 4,
      scale: 8,
      color: {
        dark: '#05080d',
        light: '#ffffff',
      },
    })
  } catch (err) {
    qrError.value = String(err?.message || err)
  }
}, { immediate: true })

async function copyShareUrl() {
  await navigator.clipboard.writeText(shareUrl.value)
  urlCopied.value = true
  setTimeout(() => { urlCopied.value = false }, 1800)
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
          <div class="qrCode">
            <img v-if="qrDataUrl" :src="qrDataUrl" :alt="`QR code for ${shareUrl}`" />
            <span v-else class="qrCodeStatus">{{ qrError || 'Generating…' }}</span>
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
