<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import placeholderImage from '../assets/trade-placeholder.png'
import AnnouncementOutputs from '../components/AnnouncementOutputs.vue'
import AnnouncementTemplateEditor from '../components/AnnouncementTemplateEditor.vue'
import CarrierTradeForm from '../components/CarrierTradeForm.vue'
import TradePosterEditor from '../components/TradePosterEditor.vue'
import { dataStore } from '../services/dataStoreService'

const LAYOUT_STORAGE_KEY = 'carrierTradeAnnouncements.layouts'
const DRAFT_STORAGE_KEY = 'carrierTradeAnnouncements.draft'
const LEGACY_LAYOUT_STORAGE_KEY = 'marketscout.carrierTradeAlert.layouts'
const LEGACY_DRAFT_STORAGE_KEY = 'marketscout.carrierTradeAlert.draft'

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function loadSavedLayouts() {
  return normalizeSavedLayouts(dataStore.cached(LAYOUT_STORAGE_KEY, [], { legacyKey: LEGACY_LAYOUT_STORAGE_KEY }))
}

function loadDraft() {
  return normalizeDraft(dataStore.cached(DRAFT_STORAGE_KEY, {}, { legacyKey: LEGACY_DRAFT_STORAGE_KEY }))
}

function normalizeSavedLayouts(layouts) {
  return Array.isArray(layouts) ? layouts.filter(item => item?.id && item?.name && item?.mode) : []
}

function normalizeSavedPrefixes(prefixes) {
  return Array.isArray(prefixes)
    ? prefixes
      .filter(item => item?.id && typeof item?.value === 'string' && item.value.trim())
      .map(item => ({
        id: String(item.id),
        value: item.value.trim(),
        label: String(item.label || item.value).trim(),
      }))
    : []
}

function normalizeDraft(draft) {
  return draft && typeof draft === 'object' && !Array.isArray(draft) ? draft : {}
}

const savedDraft = loadDraft()

const defaultForm = {
  commodity: 'Gold',
  profit: '12,000',
  includeProfitLabelInImage: true,
  includeStationTypeInShortAnnouncement: false,
  shortPrefixEnabled: false,
  shortPrefixId: '',
  quantity: '16k',
  type: 'Loading',
  carrierName: 'Fleet Carrier',
  carrierId: 'ABC-123',
  carrierSystem: 'Sol',
  station: 'Galileo',
  system: 'Sol',
  stationType: 'Orbis Starport',
  pads: 'Large',
}

const form = ref({ ...defaultForm, ...(savedDraft.form || {}) })
const defaultCustomAnnouncementTitleTemplate = '[carrier_name] ([[carrier_id]])'
const defaultCustomAnnouncementTemplate = '**[carrier_name] ([[carrier_id]])** is trading at **[trade_station_name]** [trade_station_type_if_planetary_in_parentheses] in **[trade_system]**. **[profit_k]**/unit profit, **[quantity_k]** units.'

function tradeTypeKey(value) {
  return String(value || '').toLowerCase() === 'unloading' ? 'unloading' : 'loading'
}

function tradeTypeLabel(value) {
  return tradeTypeKey(value) === 'unloading' ? 'Carrier Unloading' : 'Carrier Loading'
}

function defaultCustomTemplateSet() {
  return {
    loading: {
      title: defaultCustomAnnouncementTitleTemplate,
      body: defaultCustomAnnouncementTemplate,
    },
    unloading: {
      title: defaultCustomAnnouncementTitleTemplate,
      body: defaultCustomAnnouncementTemplate,
    },
  }
}

function normalizeCustomTemplateSet(draft) {
  const templates = {
    ...defaultCustomTemplateSet(),
    ...(draft.customAnnouncementTemplates || {}),
  }
  const legacyTitle = draft.customAnnouncementTitleTemplate
  const legacyBody = draft.customAnnouncementTemplate
  if (legacyTitle || legacyBody) {
    const key = tradeTypeKey(draft.form?.type || defaultForm.type)
    templates[key] = {
      title: legacyTitle || templates[key]?.title || defaultCustomAnnouncementTitleTemplate,
      body: legacyBody || templates[key]?.body || defaultCustomAnnouncementTemplate,
    }
  }
  for (const key of ['loading', 'unloading']) {
    templates[key] = {
      title: templates[key]?.title || defaultCustomAnnouncementTitleTemplate,
      body: templates[key]?.body || defaultCustomAnnouncementTemplate,
    }
  }
  return templates
}

const textColor = ref(savedDraft.textColor || '#f6fbff')
const textStyle = ref(savedDraft.textStyle || 'classic')
const textLayout = ref(savedDraft.textLayout || savedDraft.textStyle || 'classic')
const defaultImageUrl = ref(placeholderImage)
const uploadedImageUrl = ref(savedDraft.uploadedImageUrl || '')
const customTemplateModalOpen = ref(false)
const customAnnouncementTemplates = ref(normalizeCustomTemplateSet(savedDraft))
const layoutName = ref('')
const layoutSaveStatus = ref('')
const layoutMenuOpen = ref(false)
const shortPrefixStatus = ref('')

const savedLayouts = ref(loadSavedLayouts())
const shortAnnouncementPrefixes = ref(normalizeSavedPrefixes(savedDraft.shortAnnouncementPrefixes))
const textColorPresets = ['#f6fbff', '#ffffff', '#78c8ff', '#9ff0d4', '#ffe27a', '#ff9f43', '#ff6bcb', '#b890ff']
const UPPERCASE_LAYER_KEYS = new Set(['commodity', 'carrier'])
const TEXT_LETTER_SPACING_EM = 0.02

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
const activeCustomTemplateType = computed(() => tradeTypeKey(form.value.type))
const activeCustomTemplateTypeLabel = computed(() => tradeTypeLabel(form.value.type))
const imageUrl = computed(() => uploadedImageUrl.value || defaultImageUrl.value)
const imageProfitText = computed(() => `${adValue(form.value.profit)} Cr/t${form.value.includeProfitLabelInImage === false ? '' : ' profit'}`)
const isPlanetaryStation = computed(() => String(form.value.stationType || '').toLowerCase() === 'planetary')
const selectedShortPrefix = computed(() => shortAnnouncementPrefixes.value.find(item => item.id === form.value.shortPrefixId) || null)
const activeShortPrefix = computed(() => (form.value.shortPrefixEnabled ? selectedShortPrefix.value?.value || '' : ''))

const customAnnouncementTitleTemplate = computed({
  get() {
    return customAnnouncementTemplates.value[activeCustomTemplateType.value]?.title || defaultCustomAnnouncementTitleTemplate
  },
  set(value) {
    const key = activeCustomTemplateType.value
    customAnnouncementTemplates.value[key] = {
      ...(customAnnouncementTemplates.value[key] || {}),
      title: value,
    }
  },
})

const customAnnouncementTemplate = computed({
  get() {
    return customAnnouncementTemplates.value[activeCustomTemplateType.value]?.body || defaultCustomAnnouncementTemplate
  },
  set(value) {
    const key = activeCustomTemplateType.value
    customAnnouncementTemplates.value[key] = {
      ...(customAnnouncementTemplates.value[key] || {}),
      body: value,
    }
  },
})

function adValue(value) {
  return String(value || '').trim()
}

function displayLayerText(key, value) {
  const text = String(value || '')
  return UPPERCASE_LAYER_KEYS.has(key) ? text.toUpperCase() : text
}

function tokenK(value) {
  return adValue(value).replace(/[.,]?0{3}\b/g, 'k')
}

function tokenThousand(value) {
  return adValue(value).replace(/k/gi, '.000')
}

const customAnnouncementTokens = computed(() => ({
  commodity: form.value.commodity || 'Commodity',
  carrier_name: form.value.carrierName || 'Carrier Name',
  carrier_id: form.value.carrierId || 'Carrier ID',
  carrier_system: form.value.carrierSystem || 'Carrier System',
  buying_selling: tradeTypeLower.value === 'unloading' ? 'selling' : 'buying',
  loading_unloading: tradeTypeLower.value === 'unloading' ? 'unloading' : 'loading',
  from_to: tradeTypeLower.value === 'unloading' ? 'from' : 'to',
  carrier_trade_operation_from_to: tradeTypeLower.value === 'unloading' ? 'Buy from' : 'Sell to',
  station_trade_operation_from_to: tradeTypeLower.value === 'unloading' ? 'Sell to' : 'Buy from',
  trade_system: form.value.system || 'System',
  trade_station_name: form.value.station || 'Station',
  trade_station_type: form.value.stationType || 'Station Type',
  trade_station_type_if_planetary: isPlanetaryStation.value ? form.value.stationType : '',
  trade_station_type_if_planetary_in_parentheses: isPlanetaryStation.value ? `(${form.value.stationType})` : '',
  profit: adValue(form.value.profit),
  profit_thousand: tokenThousand(form.value.profit),
  profit_k: tokenK(form.value.profit),
  quantity: adValue(form.value.quantity),
  quantity_thousand: tokenThousand(form.value.quantity),
  quantity_k: tokenK(form.value.quantity),
}))

const customTokenList = [
  ['commodity', 'Commodity name.'],
  ['carrier_name', 'Fleet Carrier display name.'],
  ['carrier_id', 'Fleet Carrier callsign/id. Double brackets render one visible bracket pair, such as [[carrier_id]] -> [ABC-123].'],
  ['carrier_system', 'Carrier system entered in the Carrier section.'],
  ['buying_selling', 'Shows selling for Unloading trades and buying for Loading trades.'],
  ['loading_unloading', 'Shows loading or unloading based on the selected trade type.'],
  ['from_to', 'Shows to for Loading trades and from for Unloading trades.'],
  ['carrier_trade_operation_from_to', 'Carrier-side trade action: Sell to for Loading, Buy from for Unloading.'],
  ['station_trade_operation_from_to', 'Station-side trade action: Buy from for Loading, Sell to for Unloading.'],
  ['trade_system', 'Trade station system.'],
  ['trade_station_name', 'Trade station name.'],
  ['trade_station_type', 'Selected trade station type.'],
  ['trade_station_type_if_planetary', 'Selected station type, but only when it is Planetary. Otherwise blank.'],
  ['trade_station_type_if_planetary_in_parentheses', 'Selected station type in parentheses, but only when it is Planetary. Otherwise blank.'],
  ['profit', 'Profit exactly as typed.'],
  ['profit_thousand', 'Profit exactly as typed, with k replaced by .000.'],
  ['profit_k', 'Profit exactly as typed, with optional separator plus three zeroes replaced by k.'],
  ['quantity', 'Quantity exactly as typed.'],
  ['quantity_thousand', 'Quantity exactly as typed, with k replaced by .000.'],
  ['quantity_k', 'Quantity exactly as typed, with optional separator plus three zeroes replaced by k.'],
]

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

const previewLayerText = computed(() => {
  const next = {}
  for (const [key, value] of Object.entries(layerText.value)) {
    next[key] = displayLayerText(key, value)
  }
  return next
})

const announcement = computed(() => {
  const direction = tradeTypeLower.value === 'unloading' ? 'to' : 'from'
  const padText = `${padLetter.value}-pads`
  const stationInfo = form.value.includeStationTypeInShortAnnouncement
    ? `(${padText}) (${form.value.stationType || 'Station Type'})`
    : `(${padText})`
  const profitUnit = 'ton'
  const quantityUnit = 'tons'
  const body = `**${form.value.carrierName || 'Carrier Name'} (${form.value.carrierId || 'Carrier ID'})** is ${tradeTypeLower.value} **${form.value.commodity || 'Commodity'}** ${direction} **${form.value.station || 'Station'}** ${stationInfo} in **${form.value.system || 'System'}**. **${adValue(form.value.profit)}**/${profitUnit} profit, **${adValue(form.value.quantity)}** ${quantityUnit}.`
  return activeShortPrefix.value ? `${activeShortPrefix.value} ${body}` : body
})

function renderCustomTemplate(template) {
  return String(template || '').replace(/\[([a-z_]+)\]/g, (match, token) => {
    if (Object.prototype.hasOwnProperty.call(customAnnouncementTokens.value, token)) {
      return customAnnouncementTokens.value[token]
    }
    return match
  })
}

const customAnnouncementTitle = computed(() => renderCustomTemplate(customAnnouncementTitleTemplate.value))
const customAnnouncement = computed(() => renderCustomTemplate(customAnnouncementTemplate.value))

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
  dataStore.set(LAYOUT_STORAGE_KEY, savedLayouts.value, { debounceMs: 0 })
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
  if (layout.customAnnouncementTemplates) {
    customAnnouncementTemplates.value = {
      ...defaultCustomTemplateSet(),
      ...clone(customAnnouncementTemplates.value),
      ...clone(layout.customAnnouncementTemplates),
    }
  } else if (Object.prototype.hasOwnProperty.call(layout, 'customAnnouncementTitleTemplate') || Object.prototype.hasOwnProperty.call(layout, 'customAnnouncementTemplate')) {
    const key = tradeTypeKey(layout.customAnnouncementTradeType || form.value.type)
    customAnnouncementTemplates.value[key] = {
      title: layout.customAnnouncementTitleTemplate || customAnnouncementTemplates.value[key]?.title || defaultCustomAnnouncementTitleTemplate,
      body: layout.customAnnouncementTemplate || customAnnouncementTemplates.value[key]?.body || defaultCustomAnnouncementTemplate,
    }
  }
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

function saveShortPrefix(value) {
  const cleanValue = String(value || '').trim()
  if (!cleanValue) {
    shortPrefixStatus.value = 'Enter a prefix'
    return
  }
  const existing = shortAnnouncementPrefixes.value.find(item => item.value.trim().toLowerCase() === cleanValue.toLowerCase())
  const id = existing?.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const prefix = { id, value: cleanValue, label: cleanValue }
  shortAnnouncementPrefixes.value = existing
    ? shortAnnouncementPrefixes.value.map(item => item.id === id ? prefix : item)
    : [...shortAnnouncementPrefixes.value, prefix]
  form.value.shortPrefixId = id
  form.value.shortPrefixEnabled = true
  shortPrefixStatus.value = existing ? 'Selected existing prefix' : 'Saved prefix'
  setTimeout(() => { shortPrefixStatus.value = '' }, 1800)
}

function deleteShortPrefix(id) {
  shortAnnouncementPrefixes.value = shortAnnouncementPrefixes.value.filter(item => item.id !== id)
  if (form.value.shortPrefixId === id) {
    form.value.shortPrefixId = ''
    form.value.shortPrefixEnabled = false
  }
  shortPrefixStatus.value = 'Deleted prefix'
  setTimeout(() => { shortPrefixStatus.value = '' }, 1800)
}

function normalizeHexColor(value) {
  const raw = String(value || '').trim()
  if (/^#[0-9a-f]{6}$/i.test(raw)) return raw.toLowerCase()
  if (/^[0-9a-f]{6}$/i.test(raw)) return `#${raw.toLowerCase()}`
  if (/^#[0-9a-f]{3}$/i.test(raw)) {
    const chars = raw.slice(1).toLowerCase().split('')
    return `#${chars.map(char => `${char}${char}`).join('')}`
  }
  if (/^[0-9a-f]{3}$/i.test(raw)) {
    const chars = raw.toLowerCase().split('')
    return `#${chars.map(char => `${char}${char}`).join('')}`
  }
  return ''
}

function setTextColor(value) {
  const normalized = normalizeHexColor(value)
  if (!normalized) return
  textColor.value = normalized
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
    customAnnouncementTradeType: activeCustomTemplateType.value,
    customAnnouncementTemplates: clone(customAnnouncementTemplates.value),
    customAnnouncementTitleTemplate: customAnnouncementTitleTemplate.value,
    customAnnouncementTemplate: customAnnouncementTemplate.value,
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
    customAnnouncementTemplates: customAnnouncementTemplates.value,
    customAnnouncementTitleTemplate: customAnnouncementTitleTemplate.value,
    customAnnouncementTemplate: customAnnouncementTemplate.value,
    shortAnnouncementPrefixes: shortAnnouncementPrefixes.value,
  }
  dataStore.set(DRAFT_STORAGE_KEY, draft)
}

function applyDraft(draft) {
  const normalized = normalizeDraft(draft)
  form.value = { ...defaultForm, ...(normalized.form || {}) }
  textColor.value = normalized.textColor || '#f6fbff'
  textStyle.value = normalized.textStyle || 'classic'
  textLayout.value = normalized.textLayout || normalized.textStyle || 'classic'
  uploadedImageUrl.value = normalized.uploadedImageUrl || ''
  customAnnouncementTemplates.value = normalizeCustomTemplateSet(normalized)
  shortAnnouncementPrefixes.value = normalizeSavedPrefixes(normalized.shortAnnouncementPrefixes)
  layerPositions.value = {
    ...clone(defaultLayerPositions),
    ...(normalized.layerPositions || {}),
  }
  fontSizes.value = {
    ...defaultFontSizes,
    ...(normalized.fontSizes || {}),
  }
}

async function refreshStoredAnnouncementData() {
  const [draft, layouts] = await Promise.all([
    dataStore.get(DRAFT_STORAGE_KEY, savedDraft, { legacyKey: LEGACY_DRAFT_STORAGE_KEY }),
    dataStore.get(LAYOUT_STORAGE_KEY, savedLayouts.value, { legacyKey: LEGACY_LAYOUT_STORAGE_KEY }),
  ])
  savedLayouts.value = normalizeSavedLayouts(layouts)
  applyDraft(draft)
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

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    uploadedImageUrl.value = String(reader.result || '')
  }
  reader.readAsDataURL(file)
}

function moveLayer({ key, x, y }) {
  const positions = layerPositions.value[textStyle.value]
  if (!positions?.[key]) return
  positions[key].x = x
  positions[key].y = y
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
  const text = displayLayerText(layer.key, layerText.value[layer.key])
  const fontSize = Math.max(10, Number(fontSizes.value[layer.sizeKey] || 32))
  ctx.font = `${layer.weight} ${fontSize}px system-ui, -apple-system, Segoe UI, sans-serif`
  ctx.textAlign = layer.align
  ctx.textBaseline = 'middle'
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${fontSize * TEXT_LETTER_SPACING_EM}px`
  ctx.fillStyle = textColor.value
  ctx.shadowColor = 'rgba(0,0,0,.82)'
  ctx.shadowBlur = Math.max(5, fontSize * 0.22)
  ctx.lineWidth = Math.max(3, fontSize * 0.08)
  ctx.strokeStyle = 'rgba(0,0,0,.68)'
  ctx.strokeText(text, (layer.x / 100) * width, (layer.y / 100) * height)
  ctx.fillText(text, (layer.x / 100) * width, (layer.y / 100) * height)
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px'
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

watch(textLayout, value => applyTextLayout(value))
watch([form, textColor, textStyle, textLayout, layerPositions, fontSizes, uploadedImageUrl, customAnnouncementTemplates, shortAnnouncementPrefixes], persistDraft, { deep: true })
onMounted(refreshStoredAnnouncementData)
</script>

<template>
  <div class="carrierTradeAlert">
    <div class="carrierLeftPane">
      <TradePosterEditor
        :image-url="imageUrl"
        :active-layers="activeLayers"
        :layer-text="previewLayerText"
        :font-sizes="fontSizes"
        :text-color="textColor"
        @download-image="downloadImage"
        @move-layer="moveLayer"
      />

      <AnnouncementOutputs
        :announcement="announcement"
        :custom-announcement-title="customAnnouncementTitle"
        :custom-announcement="customAnnouncement"
        :active-custom-template-type-label="activeCustomTemplateTypeLabel"
        :include-short-station-type="form.includeStationTypeInShortAnnouncement"
        :short-prefix-enabled="form.shortPrefixEnabled"
        :short-prefix-id="form.shortPrefixId"
        :short-prefixes="shortAnnouncementPrefixes"
        :short-prefix-status="shortPrefixStatus"
        @update:include-short-station-type="form.includeStationTypeInShortAnnouncement = $event"
        @update:short-prefix-enabled="form.shortPrefixEnabled = $event"
        @update:short-prefix-id="form.shortPrefixId = $event"
        @save-short-prefix="saveShortPrefix"
        @delete-short-prefix="deleteShortPrefix"
        @edit-template="customTemplateModalOpen = true"
      />
    </div>

    <CarrierTradeForm
      :form="form"
      v-model:text-color="textColor"
      :text-layout="textLayout"
      :current-layout-label="currentLayoutLabel"
      v-model:layout-menu-open="layoutMenuOpen"
      v-model:layout-name="layoutName"
      :layout-save-status="layoutSaveStatus"
      :saved-layouts="savedLayouts"
      :text-color-presets="textColorPresets"
      :font-size-for="fontSizeFor"
      :set-font-size="setFontSize"
      @file-change="onFileChange"
      @set-text-color="setTextColor"
      @select-text-layout="selectTextLayout"
      @save-current-layout="saveCurrentLayout"
      @delete-saved-layout="deleteSavedLayout"
    />

    <AnnouncementTemplateEditor
      v-if="customTemplateModalOpen"
      v-model:title-template="customAnnouncementTitleTemplate"
      v-model:body-template="customAnnouncementTemplate"
      :active-custom-template-type-label="activeCustomTemplateTypeLabel"
      :custom-token-list="customTokenList"
      @close="customTemplateModalOpen = false"
    />
  </div>
</template>

<style scoped>
.carrierTradeAlert {
  --carrier-preview-width: 36rem;
  padding: 12px 16px 18px;
  display: grid;
  grid-template-columns: minmax(24rem, var(--carrier-preview-width)) minmax(22rem, 1fr);
  gap: 16px;
  align-items: start;
}

.carrierLeftPane {
  display: grid;
  gap: 12px;
  min-width: 0;
}

@media (max-width: 1100px) {
  .carrierTradeAlert {
    grid-template-columns: 1fr;
  }
}
</style>
