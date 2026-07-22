<script setup>
import QRCode from 'qrcode'
import { computed, onMounted, ref, watch } from 'vue'

const loading = ref(true)
const saving = ref(false)
const status = ref('')
const error = ref('')
const localAddress = ref('127.0.0.1')
const bindPort = ref(40595)
const lanEnabled = ref(false)
const lanBindAddress = ref('')
const active = ref({})
const defaults = ref({ bind_address: '127.0.0.1', bind_port: 40595, lan_enabled: false, lan_bind_address: '' })
const loopbackSuggestions = ref(['127.0.0.1', 'localhost'])
const lanSuggestions = ref([])
const mdns = ref({})
const configFile = ref('marketscout.config')
const urlCopied = ref(false)
const qrDataUrl = ref('')
const qrError = ref('')

const localUrl = computed(() => `http://${localAddress.value || defaults.value.bind_address}:${bindPort.value || defaults.value.bind_port}/`)
const shareUrl = computed(() => `http://${lanBindAddress.value || defaults.value.lan_bind_address}:${bindPort.value || defaults.value.bind_port}/`)
const saveDisabled = computed(() => saving.value || (lanEnabled.value && !String(lanBindAddress.value || '').trim()))
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
    defaults.value = data.defaults || defaults.value
    localAddress.value = data.config?.bind_address || defaults.value.bind_address
    bindPort.value = data.config?.bind_port || defaults.value.bind_port
    lanEnabled.value = Boolean(data.config?.lan_enabled)
    lanBindAddress.value = data.config?.lan_bind_address || defaults.value.lan_bind_address
    active.value = data.active || {}
    loopbackSuggestions.value = data.suggested_loopback_addresses || loopbackSuggestions.value
    lanSuggestions.value = data.suggested_lan_addresses || lanSuggestions.value
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
        bind_address: localAddress.value,
        bind_port: bindPort.value,
        lan_enabled: lanEnabled.value,
        lan_bind_address: lanBindAddress.value,
      }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Could not save configuration')
    localAddress.value = data.config?.bind_address || localAddress.value
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

function useLocalAddress(value) {
  localAddress.value = value
}

function useLanAddress(value) {
  lanBindAddress.value = value
  lanEnabled.value = true
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
            <input v-model="localAddress" type="text" list="localAddressSuggestions" />
          </label>
          <datalist id="localAddressSuggestions">
            <option v-for="value in loopbackSuggestions" :key="value" :value="value" />
          </datalist>

          <label>Port
            <input v-model.number="bindPort" type="number" min="1" max="65535" />
          </label>
        </div>

        <div class="suggestedAddresses">
          <span>Quick fill</span>
          <button v-for="value in loopbackSuggestions" :key="value" type="button" @click="useLocalAddress(value)">{{ value }}</button>
        </div>

        <label class="configCheckbox configStandaloneCheckbox">Enable LAN Address
          <input v-model="lanEnabled" type="checkbox" />
        </label>

        <div class="configurationGrid">
          <label>LAN address
            <input v-model="lanBindAddress" type="text" list="lanAddressSuggestions" :disabled="!lanEnabled" />
          </label>
          <datalist id="lanAddressSuggestions">
            <option v-for="value in lanSuggestions" :key="value" :value="value" />
          </datalist>

          <label>Port
            <span class="configStaticValue">{{ bindPort }}</span>
          </label>
        </div>

        <div class="suggestedAddresses">
          <span>LAN quick fill</span>
          <button v-for="value in lanSuggestions" :key="value" type="button" @click="useLanAddress(value)">{{ value }}</button>
          <span v-if="!lanSuggestions.length" class="configHint">No LAN IPv4 address detected.</span>
        </div>

        <div class="configurationActions">
          <button type="button" :disabled="saveDisabled" @click="saveConfig">{{ saving ? 'Saving…' : 'Save Configuration' }}</button>
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
