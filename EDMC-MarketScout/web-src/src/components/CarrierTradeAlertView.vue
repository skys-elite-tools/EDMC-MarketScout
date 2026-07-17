<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const form = ref({
  commodity: 'Gold',
  profit: 12000,
  quantity: 16000,
  type: 'Loading',
  carrierName: 'Fleet Carrier',
  carrierId: 'ABC-123',
  station: 'Galileo',
  system: 'Sol',
  pads: 'Large',
})

const textColor = ref('#f6fbff')
const stageRef = ref(null)
const stageWidth = ref(0)
const defaultImageUrl = ref('')
const uploadedImageUrl = ref('')
const copied = ref(false)
let resizeObserver = null
let activeDrag = null

const layers = ref([
  { key: 'type', x: 50, y: 18 },
  { key: 'commodity', x: 50, y: 31 },
  { key: 'route', x: 50, y: 48 },
  { key: 'profit', x: 50, y: 59 },
  { key: 'carrier', x: 50, y: 78 },
])

const padLetter = computed(() => (form.value.pads || 'Large').slice(0, 1).toUpperCase())
const tradeTypeLower = computed(() => String(form.value.type || '').toLowerCase())
const imageUrl = computed(() => uploadedImageUrl.value || defaultImageUrl.value)

function formatNumber(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value || '')
  return Math.round(n).toLocaleString()
}

function compactTons(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value || '')
  if (n >= 1000 && n % 1000 === 0) return `${Math.round(n / 1000)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return formatNumber(n)
}

const layerText = computed(() => ({
  type: `Carrier ${tradeTypeLower.value}`,
  commodity: form.value.commodity || 'Commodity',
  route: `${form.value.station || 'Station'} in ${form.value.system || 'System'} | ${padLetter.value}-pads`,
  profit: `${formatNumber(form.value.profit)} Cr/t profit · ${formatNumber(form.value.quantity)} tons`,
  carrier: `${form.value.carrierName || 'Carrier Name'} · ${form.value.carrierId || 'Carrier ID'}`,
}))

const announcement = computed(() => {
  return `**${form.value.carrierName || 'Carrier Name'} (${form.value.carrierId || 'Carrier ID'})** is ${tradeTypeLower.value} **${form.value.commodity || 'Commodity'}** from **${form.value.station || 'Station'}** (${padLetter.value}-pads) in **${form.value.system || 'System'}**. **${formatNumber(form.value.profit)}**/ton profit, **${compactTons(form.value.quantity)}** tons.`
})

const layerSizes = {
  type: { size: 0.036, weight: 800 },
  commodity: { size: 0.086, weight: 950 },
  route: { size: 0.034, weight: 750 },
  profit: { size: 0.035, weight: 800 },
  carrier: { size: 0.06, weight: 950 },
}

function layerStyle(layer) {
  const spec = layerSizes[layer.key] || layerSizes.route
  const size = Math.max(12, stageWidth.value * spec.size)
  return {
    left: `${layer.x}%`,
    top: `${layer.y}%`,
    color: textColor.value,
    fontSize: `${size}px`,
    fontWeight: spec.weight,
  }
}

function drawDefaultBackdrop(width = 1600, height = 900) {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  const sky = ctx.createLinearGradient(0, 0, width, height)
  sky.addColorStop(0, '#071018')
  sky.addColorStop(0.42, '#12243a')
  sky.addColorStop(1, '#2c1737')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, width, height)

  ctx.fillStyle = 'rgba(255,255,255,.8)'
  for (let i = 0; i < 180; i += 1) {
    const x = (i * 733) % width
    const y = (i * 179) % Math.round(height * 0.62)
    const r = (i % 4 === 0) ? 1.6 : 0.8
    ctx.globalAlpha = 0.25 + ((i * 17) % 70) / 100
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1

  const planet = ctx.createRadialGradient(width * 0.18, height * 0.86, 40, width * 0.18, height * 0.86, width * 0.55)
  planet.addColorStop(0, 'rgba(160,210,255,.55)')
  planet.addColorStop(0.42, 'rgba(72,110,170,.24)')
  planet.addColorStop(1, 'rgba(30,45,70,0)')
  ctx.fillStyle = planet
  ctx.fillRect(0, 0, width, height)

  ctx.strokeStyle = 'rgba(170,220,255,.34)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.ellipse(width * 0.5, height * 0.7, width * 0.52, height * 0.11, -0.12, 0, Math.PI * 2)
  ctx.stroke()

  ctx.fillStyle = 'rgba(5,8,14,.78)'
  ctx.beginPath()
  ctx.moveTo(width * 0.66, height * 0.36)
  ctx.lineTo(width * 0.91, height * 0.49)
  ctx.lineTo(width * 0.71, height * 0.55)
  ctx.closePath()
  ctx.fill()
  ctx.fillStyle = 'rgba(120,210,255,.55)'
  ctx.fillRect(width * 0.73, height * 0.465, width * 0.12, 4)

  const vignette = ctx.createRadialGradient(width * 0.5, height * 0.5, width * 0.18, width * 0.5, height * 0.5, width * 0.72)
  vignette.addColorStop(0, 'rgba(0,0,0,0)')
  vignette.addColorStop(1, 'rgba(0,0,0,.62)')
  ctx.fillStyle = vignette
  ctx.fillRect(0, 0, width, height)
  return canvas.toDataURL('image/png')
}

function updateStageSize() {
  if (!stageRef.value) return
  stageWidth.value = stageRef.value.getBoundingClientRect().width || 0
}

function startDrag(event, layer) {
  if (!stageRef.value) return
  event.preventDefault()
  const rect = stageRef.value.getBoundingClientRect()
  activeDrag = {
    key: layer.key,
    pointerId: event.pointerId,
    dx: event.clientX - (rect.left + (layer.x / 100) * rect.width),
    dy: event.clientY - (rect.top + (layer.y / 100) * rect.height),
  }
  event.currentTarget.setPointerCapture(event.pointerId)
}

function moveDrag(event) {
  if (!activeDrag || !stageRef.value || activeDrag.pointerId !== event.pointerId) return
  const rect = stageRef.value.getBoundingClientRect()
  const x = ((event.clientX - activeDrag.dx - rect.left) / rect.width) * 100
  const y = ((event.clientY - activeDrag.dy - rect.top) / rect.height) * 100
  const layer = layers.value.find(item => item.key === activeDrag.key)
  if (!layer) return
  layer.x = Math.min(96, Math.max(4, x))
  layer.y = Math.min(94, Math.max(6, y))
}

function stopDrag(event) {
  if (activeDrag?.pointerId === event.pointerId) activeDrag = null
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (uploadedImageUrl.value) URL.revokeObjectURL(uploadedImageUrl.value)
  uploadedImageUrl.value = URL.createObjectURL(file)
}

function drawCoverImage(ctx, image, width, height) {
  const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight)
  const drawWidth = image.naturalWidth * scale
  const drawHeight = image.naturalHeight * scale
  ctx.drawImage(image, (width - drawWidth) / 2, (height - drawHeight) / 2, drawWidth, drawHeight)
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function drawTextLayer(ctx, layer, width, height) {
  const spec = layerSizes[layer.key] || layerSizes.route
  const text = layerText.value[layer.key] || ''
  const fontSize = Math.max(12, width * spec.size)
  ctx.font = `${spec.weight} ${fontSize}px system-ui, -apple-system, Segoe UI, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = textColor.value
  ctx.shadowColor = 'rgba(0,0,0,.82)'
  ctx.shadowBlur = Math.max(5, fontSize * 0.22)
  ctx.lineWidth = Math.max(3, fontSize * 0.08)
  ctx.strokeStyle = 'rgba(0,0,0,.68)'
  ctx.strokeText(text, (layer.x / 100) * width, (layer.y / 100) * height)
  ctx.fillText(text, (layer.x / 100) * width, (layer.y / 100) * height)
}

async function downloadImage(format = 'png') {
  const width = 1200
  const height = 900
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  const img = await loadImage(imageUrl.value || drawDefaultBackdrop(width, height))
  drawCoverImage(ctx, img, width, height)
  for (const layer of layers.value) drawTextLayer(ctx, layer, width, height)
  const link = document.createElement('a')
  const commodity = String(form.value.commodity || 'commodity').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const isJpg = format === 'jpg'
  link.download = `carrier-trade-${commodity || 'alert'}.${isJpg ? 'jpg' : 'png'}`
  link.href = canvas.toDataURL(isJpg ? 'image/jpeg' : 'image/png', 0.92)
  link.click()
}

async function copyAnnouncement() {
  await navigator.clipboard.writeText(announcement.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1800)
}

onMounted(async () => {
  defaultImageUrl.value = drawDefaultBackdrop()
  await nextTick()
  updateStageSize()
  resizeObserver = new ResizeObserver(updateStageSize)
  if (stageRef.value) resizeObserver.observe(stageRef.value)
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  if (uploadedImageUrl.value) URL.revokeObjectURL(uploadedImageUrl.value)
})

watch(imageUrl, () => nextTick(updateStageSize))
</script>

<template>
  <div class="carrierTradeAlert">
    <section class="carrierSection">
      <h2>Trade</h2>
      <div class="carrierFormGrid">
        <fieldset>
          <legend>Trade</legend>
          <label>Commodity <input v-model="form.commodity" type="text" /></label>
          <label>Profit <input v-model.number="form.profit" type="number" min="0" /></label>
          <label>Quantity (tons) <input v-model.number="form.quantity" type="number" min="0" /></label>
          <label>Type
            <select v-model="form.type">
              <option>Loading</option>
              <option>Unloading</option>
            </select>
          </label>
        </fieldset>
        <fieldset>
          <legend>Carrier</legend>
          <label>Carrier Name <input v-model="form.carrierName" type="text" /></label>
          <label>Carrier ID <input v-model="form.carrierId" type="text" /></label>
        </fieldset>
        <fieldset>
          <legend>Market</legend>
          <label>Station <input v-model="form.station" type="text" /></label>
          <label>System <input v-model="form.system" type="text" /></label>
          <label>Pads
            <select v-model="form.pads">
              <option>Small</option>
              <option>Medium</option>
              <option>Large</option>
            </select>
          </label>
        </fieldset>
      </div>
    </section>

    <section class="carrierSection">
      <h2>Image</h2>
      <div class="carrierImageTools">
        <label>Image <span class="small">Default sci-fi backdrop is used until a file is selected.</span></label>
        <label>Upload image <input type="file" accept="image/*" @change="onFileChange" /></label>
        <label>Text Color <input v-model="textColor" type="color" /></label>
      </div>
      <div ref="stageRef" class="carrierImageStage">
        <img v-if="imageUrl" :src="imageUrl" alt="" />
        <div class="imageDownloadButtons" aria-label="Download image">
          <button type="button" title="Download PNG" @click="downloadImage('png')">PNG ↓</button>
          <button type="button" title="Download JPG" @click="downloadImage('jpg')">JPG ↓</button>
        </div>
        <div
          v-for="layer in layers"
          :key="layer.key"
          class="carrierTextLayer"
          :class="`carrierLayer-${layer.key}`"
          :style="layerStyle(layer)"
          @pointerdown="startDrag($event, layer)"
          @pointermove="moveDrag"
          @pointerup="stopDrag"
          @pointercancel="stopDrag"
        >
          {{ layerText[layer.key] }}
        </div>
      </div>
    </section>

    <section class="carrierSection">
      <h2>Announcement</h2>
      <div class="announcementBox">
        <textarea :value="announcement" readonly rows="4"></textarea>
        <button type="button" class="copySymbolButton" :title="copied ? 'Copied' : 'Copy announcement'" @click="copyAnnouncement">{{ copied ? '✓' : '⧉' }}</button>
      </div>
    </section>
  </div>
</template>
