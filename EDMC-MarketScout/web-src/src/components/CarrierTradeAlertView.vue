<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import placeholderImage from '../assets/trade-placeholder.png'

const LAYOUT_STORAGE_KEY = 'marketscout.carrierTradeAlert.layouts'
const DRAFT_STORAGE_KEY = 'marketscout.carrierTradeAlert.draft'

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function loadSavedLayouts() {
  try {
    const layouts = JSON.parse(window.localStorage.getItem(LAYOUT_STORAGE_KEY) || '[]')
    return Array.isArray(layouts) ? layouts.filter(item => item?.id && item?.name && item?.mode) : []
  } catch (err) {
    return []
  }
}

function loadDraft() {
  try {
    const draft = JSON.parse(window.localStorage.getItem(DRAFT_STORAGE_KEY) || '{}')
    return draft && typeof draft === 'object' ? draft : {}
  } catch (err) {
    return {}
  }
}

const savedDraft = loadDraft()

const defaultForm = {
  commodity: 'Gold',
  profit: '12,000',
  includeProfitLabelInImage: true,
  quantity: '16k',
  type: 'Loading',
  carrierName: 'Fleet Carrier',
  carrierId: 'ABC-123',
  station: 'Galileo',
  system: 'Sol',
  pads: 'Large',
}

const form = ref({ ...defaultForm, ...(savedDraft.form || {}) })

const textColor = ref(savedDraft.textColor || '#f6fbff')
const textStyle = ref(savedDraft.textStyle || 'classic')
const textLayout = ref(savedDraft.textLayout || savedDraft.textStyle || 'classic')
const stageRef = ref(null)
const layoutMenuRef = ref(null)
const stageWidth = ref(0)
const defaultImageUrl = ref(placeholderImage)
const uploadedImageUrl = ref(savedDraft.uploadedImageUrl || '')
const copied = ref(false)
const layoutName = ref('')
const layoutSaveStatus = ref('')
const layoutMenuOpen = ref(false)
let resizeObserver = null
let activeDrag = null

const savedLayouts = ref(loadSavedLayouts())

const defaultLayerPositions = {
  classic: {
    type: { x: 50, y: 18 },
    commodity: { x: 50, y: 31 },
    route: { x: 50, y: 48 },
    profit: { x: 50, y: 59 },
    carrier: { x: 50, y: 78 },
  },
  floating: {
    type: { x: 92, y: 16 },
    commodity: { x: 92, y: 26 },
    station: { x: 92, y: 39 },
    system: { x: 92, y: 47 },
    pads: { x: 92, y: 55 },
    profitValue: { x: 92, y: 66 },
    quantity: { x: 92, y: 74 },
    carrierName: { x: 92, y: 84 },
    carrierId: { x: 92, y: 91 },
  },
}

const defaultFontSizes = {
  classicType: 43,
  classicCommodity: 103,
  classicRoute: 41,
  classicProfit: 42,
  classicCarrier: 72,
  type: 32,
  commodity: 68,
  station: 28,
  system: 28,
  pads: 24,
  profitValue: 30,
  quantity: 30,
  carrierName: 42,
  carrierId: 36,
}

const layerPositions = ref({
  ...clone(defaultLayerPositions),
  ...(savedDraft.layerPositions || {}),
})

const fontSizes = ref({
  ...defaultFontSizes,
  ...(savedDraft.fontSizes || {}),
})

const padLetter = computed(() => (form.value.pads || 'Large').slice(0, 1).toUpperCase())
const tradeTypeLower = computed(() => String(form.value.type || '').toLowerCase())
const imageUrl = computed(() => uploadedImageUrl.value || defaultImageUrl.value)
const imageProfitText = computed(() => `${adValue(form.value.profit)} Cr/t${form.value.includeProfitLabelInImage === false ? '' : ' profit'}`)

function adValue(value) {
  return String(value || '').trim()
}

const layerText = computed(() => ({
  type: `Carrier ${tradeTypeLower.value}`,
  commodity: form.value.commodity || 'Commodity',
  route: `${form.value.station || 'Station'} in ${form.value.system || 'System'} | ${padLetter.value}-pads`,
  profit: `${imageProfitText.value} · ${adValue(form.value.quantity)} tons`,
  carrier: `${form.value.carrierName || 'Carrier Name'} · ${form.value.carrierId || 'Carrier ID'}`,
  station: form.value.station || 'Station',
  system: form.value.system || 'System',
  pads: `${padLetter.value}-pads`,
  profitValue: imageProfitText.value,
  quantity: `${adValue(form.value.quantity)} tons`,
  carrierName: form.value.carrierName || 'Carrier Name',
  carrierId: form.value.carrierId || 'Carrier ID',
}))

const announcement = computed(() => {
  const direction = tradeTypeLower.value === 'unloading' ? 'to' : 'from'
  const padText = tradeTypeLower.value === 'unloading' ? `${padLetter.value} pads` : `${padLetter.value}-pads`
  const profitUnit = tradeTypeLower.value === 'unloading' ? 'unit' : 'ton'
  const quantityUnit = tradeTypeLower.value === 'unloading' ? 'units' : 'tons'
  return `**${form.value.carrierName || 'Carrier Name'} (${form.value.carrierId || 'Carrier ID'})** is ${tradeTypeLower.value} **${form.value.commodity || 'Commodity'}** ${direction} **${form.value.station || 'Station'}** (${padText}) in **${form.value.system || 'System'}**. **${adValue(form.value.profit)}**/${profitUnit} profit, **${adValue(form.value.quantity)}** ${quantityUnit}.`
})

const classicLayers = [
  { key: 'type', sizeKey: 'classicType', weight: 800, align: 'center' },
  { key: 'commodity', sizeKey: 'classicCommodity', weight: 950, align: 'center' },
  { key: 'route', sizeKey: 'classicRoute', weight: 750, align: 'center' },
  { key: 'profit', sizeKey: 'classicProfit', weight: 800, align: 'center' },
  { key: 'carrier', sizeKey: 'classicCarrier', weight: 950, align: 'center' },
]

const floatingLayers = [
  { key: 'type', sizeKey: 'type', weight: 800, align: 'right' },
  { key: 'commodity', sizeKey: 'commodity', weight: 950, align: 'right' },
  { key: 'station', sizeKey: 'station', weight: 800, align: 'right' },
  { key: 'system', sizeKey: 'system', weight: 800, align: 'right' },
  { key: 'pads', sizeKey: 'pads', weight: 750, align: 'right' },
  { key: 'profitValue', sizeKey: 'profitValue', weight: 850, align: 'right' },
  { key: 'quantity', sizeKey: 'quantity', weight: 850, align: 'right' },
  { key: 'carrierName', sizeKey: 'carrierName', weight: 950, align: 'right' },
  { key: 'carrierId', sizeKey: 'carrierId', weight: 900, align: 'right' },
]

const builtInLayoutNames = new Set(['classic', 'free floating'])

const activeLayers = computed(() => (textStyle.value === 'floating' ? floatingLayers : classicLayers).map(layer => ({
  ...layer,
  ...(layerPositions.value[textStyle.value][layer.key] || { x: 50, y: 50 }),
})))

const currentLayoutLabel = computed(() => {
  if (textLayout.value === 'classic') return 'Classic'
  if (textLayout.value === 'floating') return 'Free Floating'
  const layout = savedLayouts.value.find(item => `custom:${item.id}` === textLayout.value)
  return layout?.name || 'Classic'
})

function persistSavedLayouts() {
  try {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(savedLayouts.value))
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

function applyTextLayout(value) {
  if (value === 'classic' || value === 'floating') {
    textStyle.value = value
    layoutName.value = ''
    return
  }
  const layout = savedLayouts.value.find(item => `custom:${item.id}` === value)
  if (!layout) return
  layoutName.value = layout.name
  textStyle.value = layout.mode === 'floating' ? 'floating' : 'classic'
  if (layout.positions) layerPositions.value[textStyle.value] = clone(layout.positions)
  if (layout.fontSizes) fontSizes.value = { ...fontSizes.value, ...clone(layout.fontSizes) }
}

function selectTextLayout(value) {
  textLayout.value = value
  layoutMenuOpen.value = false
}

function deleteSavedLayout(id) {
  savedLayouts.value = savedLayouts.value.filter(item => item.id !== id)
  persistSavedLayouts()
  if (textLayout.value === `custom:${id}`) {
    textLayout.value = 'classic'
    layoutName.value = ''
  }
  layoutSaveStatus.value = 'Deleted layout'
  setTimeout(() => { layoutSaveStatus.value = '' }, 1800)
}

function closeLayoutMenuOnOutsideClick(event) {
  if (!layoutMenuOpen.value) return
  if (layoutMenuRef.value?.contains(event.target)) return
  layoutMenuOpen.value = false
}

function saveCurrentLayout() {
  const cleanName = String(layoutName.value || '').trim()
  if (!cleanName) {
    layoutSaveStatus.value = 'Enter a layout name'
    return
  }
  if (builtInLayoutNames.has(cleanName.toLowerCase())) {
    layoutSaveStatus.value = 'Built-in layouts cannot be overwritten'
    return
  }
  const existing = savedLayouts.value.find(item => item.name.trim().toLowerCase() === cleanName.toLowerCase())
  const id = existing?.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const layout = {
    id,
    name: cleanName,
    mode: textStyle.value,
    positions: clone(layerPositions.value[textStyle.value]),
    fontSizes: clone(fontSizes.value),
  }
  savedLayouts.value = existing
    ? savedLayouts.value.map(item => item.id === id ? layout : item)
    : [...savedLayouts.value, layout]
  persistSavedLayouts()
  textLayout.value = `custom:${id}`
  layoutSaveStatus.value = existing ? 'Updated layout' : 'Saved layout'
  setTimeout(() => { layoutSaveStatus.value = '' }, 1800)
}

function persistDraft() {
  const draft = {
    form: form.value,
    textColor: textColor.value,
    textStyle: textStyle.value,
    textLayout: textLayout.value,
    layerPositions: layerPositions.value,
    fontSizes: fontSizes.value,
    uploadedImageUrl: uploadedImageUrl.value,
  }
  try {
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft))
  } catch (err) {
    // Large uploaded images can exceed browser storage quota.
  }
}

function previewFontSize(layer) {
  const exportedSize = Number(fontSizes.value[layer.sizeKey] || 32)
  return Math.max(10, exportedSize * (stageWidth.value || 1200) / 1200)
}

function sizeKeyFor(field) {
  if (textStyle.value === 'floating') return field
  return {
    type: 'classicType',
    commodity: 'classicCommodity',
    station: 'classicRoute',
    system: 'classicRoute',
    pads: 'classicRoute',
    profitValue: 'classicProfit',
    quantity: 'classicProfit',
    carrierName: 'classicCarrier',
    carrierId: 'classicCarrier',
  }[field] || field
}

function fontSizeFor(field) {
  return fontSizes.value[sizeKeyFor(field)]
}

function setFontSize(field, value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return
  fontSizes.value[sizeKeyFor(field)] = Math.max(8, Math.min(180, Math.round(n)))
}

function layerStyle(layer) {
  const size = previewFontSize(layer)
  return {
    left: `${layer.x}%`,
    top: `${layer.y}%`,
    color: textColor.value,
    fontSize: `${size}px`,
    fontWeight: layer.weight,
    textAlign: layer.align,
    transform: layer.align === 'right' ? 'translate(-100%, -50%)' : 'translate(-50%, -50%)',
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
  const positions = layerPositions.value[textStyle.value]
  if (!positions?.[activeDrag.key]) return
  positions[activeDrag.key].x = Math.min(96, Math.max(4, x))
  positions[activeDrag.key].y = Math.min(94, Math.max(6, y))
}

function stopDrag(event) {
  if (activeDrag?.pointerId === event.pointerId) activeDrag = null
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    uploadedImageUrl.value = String(reader.result || '')
  }
  reader.readAsDataURL(file)
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
  const text = layerText.value[layer.key] || ''
  const fontSize = Math.max(10, Number(fontSizes.value[layer.sizeKey] || 32))
  ctx.font = `${layer.weight} ${fontSize}px system-ui, -apple-system, Segoe UI, sans-serif`
  ctx.textAlign = layer.align
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
  const img = await loadImage(imageUrl.value || placeholderImage)
  drawCoverImage(ctx, img, width, height)
  for (const layer of activeLayers.value) drawTextLayer(ctx, layer, width, height)
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
  document.addEventListener('pointerdown', closeLayoutMenuOnOutsideClick)
  await nextTick()
  updateStageSize()
  resizeObserver = new ResizeObserver(updateStageSize)
  if (stageRef.value) resizeObserver.observe(stageRef.value)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', closeLayoutMenuOnOutsideClick)
  if (resizeObserver) resizeObserver.disconnect()
})

watch(imageUrl, () => nextTick(updateStageSize))
watch(textLayout, value => applyTextLayout(value))
watch([form, textColor, textStyle, textLayout, layerPositions, fontSizes, uploadedImageUrl], persistDraft, { deep: true })
</script>

<template>
  <div class="carrierTradeAlert">
    <div class="carrierLeftPane">
      <section class="carrierSection">
        <h2>Image</h2>
        <div ref="stageRef" class="carrierImageStage">
          <img v-if="imageUrl" :src="imageUrl" alt="" />
          <div class="imageDownloadButtons" aria-label="Download image">
            <button type="button" title="Download PNG" @click="downloadImage('png')">PNG ↓</button>
            <button type="button" title="Download JPG" @click="downloadImage('jpg')">JPG ↓</button>
          </div>
          <div
            v-for="layer in activeLayers"
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

    <section class="carrierSection carrierFormPane">
      <h2>Image Options</h2>
      <div class="carrierImageTools">
        <label>Upload image <input type="file" accept="image/*" @change="onFileChange" /></label>
        <div class="textLayoutMenuField">
          <span>Text Layout</span>
          <div ref="layoutMenuRef" class="textLayoutMenu">
            <button type="button" class="textLayoutMenuButton" @click="layoutMenuOpen = !layoutMenuOpen">{{ currentLayoutLabel }} ▾</button>
            <div v-if="layoutMenuOpen" class="textLayoutMenuList">
              <button type="button" class="textLayoutMenuOption" :class="{ active: textLayout === 'classic' }" @click="selectTextLayout('classic')">Classic</button>
              <button type="button" class="textLayoutMenuOption" :class="{ active: textLayout === 'floating' }" @click="selectTextLayout('floating')">Free Floating</button>
              <div class="textLayoutMenuDivider"></div>
              <div class="layoutSaveRow">
                <label>Layout name <input v-model="layoutName" type="text" placeholder="My carrier layout" @keydown.enter.prevent="saveCurrentLayout" /></label>
                <button type="button" class="saveLayoutButton" @click="saveCurrentLayout">Save new</button>
                <span class="small layoutSaveStatus">{{ layoutSaveStatus }}</span>
              </div>
              <div v-if="savedLayouts.length" class="textLayoutMenuDivider"></div>
              <div v-for="layout in savedLayouts" :key="layout.id" class="textLayoutMenuRow" :class="{ active: textLayout === `custom:${layout.id}` }">
                <button type="button" class="textLayoutMenuOption custom" @click="selectTextLayout(`custom:${layout.id}`)">{{ layout.name }}</button>
                <button type="button" class="textLayoutDeleteButton" title="Delete layout" @click.stop="deleteSavedLayout(layout.id)">🗑</button>
              </div>
            </div>
          </div>
        </div>
        <label>Text Color <input v-model="textColor" type="color" /></label>
      </div>
      <h2>Trade</h2>
      <div class="carrierFormGrid">
        <fieldset class="tradeFieldset">
          <legend>Trade</legend>
          <div class="fieldWithFont">
            <label>Commodity <input v-model="form.commodity" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('commodity')" type="number" min="8" max="180" step="1" @input="setFontSize('commodity', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont profitFieldWithOptions">
            <label>Profit <input v-model="form.profit" type="text" /></label>
            <label class="inlineCheckboxLabel"><input v-model="form.includeProfitLabelInImage" type="checkbox" /> Profit label</label>
            <label>Font size <input :value="fontSizeFor('profitValue')" type="number" min="8" max="180" step="1" @input="setFontSize('profitValue', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont">
            <label>Quantity (tons) <input v-model="form.quantity" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('quantity')" type="number" min="8" max="180" step="1" @input="setFontSize('quantity', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont">
            <label>Type
              <select v-model="form.type">
                <option>Loading</option>
                <option>Unloading</option>
              </select>
            </label>
            <label>Font size <input :value="fontSizeFor('type')" type="number" min="8" max="180" step="1" @input="setFontSize('type', $event.target.value)" /></label>
          </div>
        </fieldset>
        <fieldset class="carrierFieldset">
          <legend>Carrier</legend>
          <div class="fieldWithFont">
            <label>Carrier Name <input v-model="form.carrierName" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('carrierName')" type="number" min="8" max="180" step="1" @input="setFontSize('carrierName', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont">
            <label>Carrier ID <input v-model="form.carrierId" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('carrierId')" type="number" min="8" max="180" step="1" @input="setFontSize('carrierId', $event.target.value)" /></label>
          </div>
        </fieldset>
        <fieldset class="marketFieldset">
          <legend>Market</legend>
          <div class="fieldWithFont">
            <label>Station <input v-model="form.station" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('station')" type="number" min="8" max="180" step="1" @input="setFontSize('station', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont">
            <label>System <input v-model="form.system" type="text" /></label>
            <label>Font size <input :value="fontSizeFor('system')" type="number" min="8" max="180" step="1" @input="setFontSize('system', $event.target.value)" /></label>
          </div>
          <div class="fieldWithFont">
            <label>Pads
              <select v-model="form.pads">
                <option>Small</option>
                <option>Medium</option>
                <option>Large</option>
              </select>
            </label>
            <label>Font size <input :value="fontSizeFor('pads')" type="number" min="8" max="180" step="1" @input="setFontSize('pads', $event.target.value)" /></label>
          </div>
        </fieldset>
      </div>
    </section>
  </div>
</template>
