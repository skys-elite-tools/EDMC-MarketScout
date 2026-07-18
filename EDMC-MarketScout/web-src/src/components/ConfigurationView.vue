<script setup>
import QRCode from 'qrcode'
import { computed, onMounted, ref, watch } from 'vue'

const loading = ref(true)
const saving = ref(false)
const status = ref('')
const error = ref('')
const bindPort = ref(40595)
const lanEnabled = ref(false)
const lanBindAddress = ref('')
const active = ref({})
const defaults = ref({ bind_address: '127.0.0.1', bind_port: 40595, lan_enabled: false, lan_bind_address: '' })
const suggestions = ref(['127.0.0.1', 'localhost'])
const mdns = ref({})
const configFile = ref('marketscout.config')
const urlCopied = ref(false)
const qrDataUrl = ref('')
const qrError = ref('')

const localUrl = computed(() => `http://${defaults.value.bind_address}:${bindPort.value || defaults.value.bind_port}/`)
const shareUrl = computed(() => `http://${lanBindAddress.value || defaults.value.lan_bind_address}:${bindPort.value || defaults.value.bind_port}/`)
const isShareableAddress = computed(() => {
  if (!lanEnabled.value) return false
  const value = String(lanBindAddress.value || '').trim().toLowerCase()
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
    bindPort.value = data.config?.bind_port || defaults.value.bind_port
    lanEnabled.value = Boolean(data.config?.lan_enabled)
    lanBindAddress.value = data.config?.lan_bind_address || defaults.value.lan_bind_address
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
        bind_port: bindPort.value,
        lan_enabled: lanEnabled.value,
        lan_bind_address: lanBindAddress.value,
      }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not save configuration')
    bindPort.value = data.config?.bind_port || bindPort.value
    lanEnabled.value = Boolean(data.config?.lan_enabled)
    lanBindAddress.value = data.config?.lan_bind_address || lanBindAddress.value
    status.value = data.message || 'Saved.'
  } catch (err) {
    error.value = String(err?.message || err)
  } finally {
    saving.value = false
  }
}

function useAddress(value) {
  lanBindAddress.value = value
  if (isShareableAddressValue(value)) lanEnabled.value = true
}

function isShareableAddressValue(value) {
  const normalized = String(value || '').trim().toLowerCase()
  const parts = normalized.split('.')
  if (normalized === 'localhost' || normalized === '0.0.0.0' || normalized.includes(':')) return false
  if (parts.length !== 4) return false
  const numbers = parts.map((part) => Number(part))
  if (numbers.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false
  if (numbers[0] === 127) return false
  if (numbers[0] === 169 && numbers[1] === 254) return false
  return true
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
        <p>MarketScout stores app-level configuration in <code>{{ configFile }}</code> in the plugin folder. Port and LAN sharing changes are applied after restarting EDMC.</p>
        <p v-if="active.url">Local Web UI: <strong>{{ active.url }}</strong></p>
        <p v-if="active.lan_url">LAN Web UI: <strong>{{ active.lan_url }}</strong></p>
        <p v-if="active.lan_error" class="configError">LAN listener could not start: {{ active.lan_error }}</p>
      </div>

      <div v-if="loading" class="placeholderBox">Loading configuration…</div>
      <template v-else>
        <div class="configurationGrid">
          <label>Local address
            <input :value="defaults.bind_address" type="text" disabled />
          </label>

          <label>Listening port
            <input v-model.number="bindPort" type="number" min="1" max="65535" />
          </label>

          <label class="configCheckbox">Enable LAN access
            <input v-model="lanEnabled" type="checkbox" />
          </label>

          <label>LAN address
            <input v-model="lanBindAddress" type="text" list="bindAddressSuggestions" />
          </label>
          <datalist id="bindAddressSuggestions">
            <option v-for="value in suggestions" :key="value" :value="value" />
          </datalist>
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
            <p>Enable LAN access and choose a LAN IPv4 address, such as a 192.168.x.x or 10.x.x.x address, to show a QR code for another device.</p>
            <p class="shareUrl">{{ lanEnabled ? shareUrl : localUrl }}</p>
          </div>
        </div>
      </template>
    </fieldset>

    <fieldset class="configurationPanel">
      <legend>Network Notes</legend>
      <p><strong>127.0.0.1</strong> is always available on this computer, so browser settings saved for MarketScout stay on a stable local address.</p>
      <p><strong>localhost</strong> also points to this computer, but browser localStorage is stored separately from 127.0.0.1.</p>
      <p>Enabling LAN access starts an additional listener for other devices on your local network. Only use that intentionally.</p>
      <p><strong>{{ mdns.name || 'marketscout.local' }}</strong>: {{ mdns.message || 'mDNS advertising is not enabled.' }}</p>
    </fieldset>
  </section>
</template>
