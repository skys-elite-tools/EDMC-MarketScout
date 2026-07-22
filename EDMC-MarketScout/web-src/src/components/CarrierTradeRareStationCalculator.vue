<script setup>
import { computed, onMounted, ref } from 'vue'
import { fmt, money, query } from '../utils.js'
import AutocompleteDropdown from './AutocompleteDropdown.vue'

const props = defineProps({
  inputs: { type: Object, required: true },
})

const CUSTOM_SUPPLY_STORAGE_KEY = 'marketscout.rareCommodityCustomSupply'
const TRIP_PROFIT_TITLE = 'Aggregated Profit/Ship Trip = (carrier_capacity * profit) / (ceil(carrier_capacity / min(ship_cargo_capacity, origin_station_supply)) + ceil(carrier_capacity / ship_cargo_capacity)).'

const rareStationOptions = ref([])
const rareStationRows = ref([])
const rareStationStatus = ref('Loading visited stations...')
const rareStationLoading = ref(false)
const targetQuery = ref('')
const customSupplies = ref({})
const customSupplyEditing = ref('')
const customSupplyDraft = ref('')

function asNumber(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function floorCr(value) {
  return Math.floor(asNumber(value))
}

function stationLabel(station) {
  return station?.label || `${station?.station_name || 'Unknown station'} in ${station?.system_name || 'Unknown system'}`
}

const selectedStation = computed(() => {
  const id = String(props.inputs.marketId || '')
  return rareStationOptions.value.find(row => String(row.market_id) === id) || null
})

function syncTargetQuery() {
  targetQuery.value = selectedStation.value ? stationLabel(selectedStation.value) : ''
}

function loadCustomSupplies() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(CUSTOM_SUPPLY_STORAGE_KEY) || '{}')
    if (raw && typeof raw === 'object') {
      const next = {}
      for (const [commodity, value] of Object.entries(raw)) {
        const n = Number(value)
        if (commodity && Number.isFinite(n) && n >= 0) next[commodity] = Math.floor(n)
      }
      customSupplies.value = next
    }
  } catch (err) {
    customSupplies.value = {}
  }
}

function saveCustomSupplies() {
  try {
    window.localStorage.setItem(CUSTOM_SUPPLY_STORAGE_KEY, JSON.stringify(customSupplies.value))
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
}

function effectiveOriginStock(row) {
  let source = row.usual_supply
  if (props.inputs.originStockMode === 'recent') {
    source = row.default_origin_stock ?? row.recent_supply ?? row.usual_supply
  } else if (props.inputs.originStockMode === 'custom') {
    source = customSupplies.value[row.commodity] ?? row.usual_supply
  }
  return Math.max(0, floorCr(source))
}

function setStockMode(mode) {
  props.inputs.originStockMode = mode
}

function customSupplyFor(row) {
  const value = customSupplies.value[row.commodity]
  return Number.isFinite(Number(value)) ? Number(value) : null
}

const calculatedRows = computed(() => {
  const capacity = Math.max(0, floorCr(props.inputs.carrierCapacity))
  const shipCapacity = Math.max(0, floorCr(props.inputs.shipCargoCapacity))
  const rows = rareStationRows.value.map(row => {
    const sellPrice = asNumber(row.sell_price)
    const originBuyPrice = asNumber(row.origin_buy_price)
    const profit = floorCr(sellPrice - originBuyPrice)
    const originStock = effectiveOriginStock(row)
    const loadCapacity = Math.min(shipCapacity, originStock)
    const loadsPerCarrier = capacity > 0 && loadCapacity > 0 ? Math.ceil(capacity / loadCapacity) : 0
    const unloadsPerCarrier = capacity > 0 && shipCapacity > 0 ? Math.ceil(capacity / shipCapacity) : 0
    const totalShipTrips = loadsPerCarrier + unloadsPerCarrier
    const profitPerCarrier = floorCr(profit * capacity)
    return {
      ...row,
      profit,
      origin_stock: originStock,
      loads_per_carrier: loadsPerCarrier,
      unloads_per_carrier: unloadsPerCarrier,
      profit_per_trip: totalShipTrips > 0 ? floorCr(profitPerCarrier / totalShipTrips) : 0,
      profit_per_carrier: profitPerCarrier,
    }
  })
  const sort = props.inputs.sort
  rows.sort((a, b) => {
    if (sort === 'profit_carrier_desc') {
      return b.profit_per_carrier - a.profit_per_carrier || String(a.commodity || '').localeCompare(String(b.commodity || ''))
    }
    return b.profit_per_trip - a.profit_per_trip || String(a.commodity || '').localeCompare(String(b.commodity || ''))
  })
  return rows
})

function selectTarget(station) {
  const nextMarketId = String(station.market_id)
  if (props.inputs.marketId === nextMarketId) {
    if (!rareStationRows.value.length) loadRows()
    return
  }
  props.inputs.marketId = nextMarketId
  loadRows()
}

function clearTarget() {
  props.inputs.marketId = ''
  rareStationRows.value = []
}

function updateTargetQuery(value) {
  targetQuery.value = value
  const match = rareStationOptions.value.find(station => stationLabel(station).trim().toLowerCase() === String(value || '').trim().toLowerCase())
  if (match) {
    selectTarget(match)
  } else if (!String(value || '').trim()) {
    clearTarget()
  }
}

function startCustomSupplyEdit(row) {
  customSupplyEditing.value = row.commodity || ''
  const current = customSupplyFor(row)
  customSupplyDraft.value = current === null ? String(effectiveOriginStock(row)) : String(current)
}

function cancelCustomSupplyEdit() {
  customSupplyEditing.value = ''
  customSupplyDraft.value = ''
}

function saveCustomSupply(row) {
  const commodity = row.commodity || ''
  if (!commodity) return
  const raw = String(customSupplyDraft.value ?? '').trim()
  const next = { ...customSupplies.value }
  if (raw === '') {
    delete next[commodity]
  } else {
    const n = Number(raw)
    if (!Number.isFinite(n) || n < 0) return
    next[commodity] = Math.floor(n)
  }
  customSupplies.value = next
  saveCustomSupplies()
  cancelCustomSupplyEdit()
}

async function loadOptions() {
  rareStationStatus.value = 'Loading visited stations...'
  try {
    const res = await fetch('/api/rare-station-trade-options', { cache: 'no-store' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    rareStationOptions.value = data.rows || []
    if (props.inputs.marketId && !selectedStation.value) {
      props.inputs.marketId = ''
    }
    if (!props.inputs.marketId && rareStationOptions.value.length) {
      props.inputs.marketId = String(rareStationOptions.value[0].market_id)
    }
    syncTargetQuery()
    rareStationStatus.value = rareStationOptions.value.length ? `${rareStationOptions.value.length} visited stations` : 'No visited stations with market data yet'
    await loadRows()
  } catch (err) {
    rareStationOptions.value = []
    props.inputs.marketId = ''
    syncTargetQuery()
    rareStationStatus.value = 'Could not load visited stations'
  }
}

async function loadRows() {
  if (!props.inputs.marketId) {
    rareStationRows.value = []
    return
  }
  rareStationLoading.value = true
  try {
    const params = query({ market_id: props.inputs.marketId })
    const res = await fetch(`/api/rare-station-trade?${params}`, { cache: 'no-store' })
    const data = await res.json()
    rareStationRows.value = data.rows || []
  } catch (err) {
    rareStationRows.value = []
  } finally {
    rareStationLoading.value = false
  }
}

loadCustomSupplies()
onMounted(loadOptions)
</script>

<template>
  <section class="calculatorWidePanel">
    <fieldset class="calculatorInputs rareStationControls">
      <legend>Rare Commodity Station Trade</legend>
      <div class="calculatorGrid rareStationGrid">
        <label class="rareStationTargetField">Target Station
          <AutocompleteDropdown
            :model-value="targetQuery"
            :options="rareStationOptions"
            :option-label="stationLabel"
            placeholder="Select a visited station"
            empty-text="No matching target stations"
            button-title="Show target stations"
            @update:model-value="updateTargetQuery"
            @select="selectTarget"
            @clear="clearTarget"
          >
            <template #option="{ option }">
              <span>{{ fmt(option.station_name) }}</span>
              <small>{{ fmt(option.system_name) }}</small>
            </template>
          </AutocompleteDropdown>
        </label>
        <label>Carrier Capacity
          <input v-model.number="inputs.carrierCapacity" type="number" min="0" step="100" />
        </label>
        <label title="This is used for calculating the aggregated profit / trip">Ship Cargo Capacity
          <input v-model.number="inputs.shipCargoCapacity" type="number" min="0" step="10" />
        </label>
        <label>Sort
          <select v-model="inputs.sort">
            <option value="profit_trip_desc">Agg. Profit/Trip</option>
            <option value="profit_carrier_desc">Profit / Carrier</option>
          </select>
        </label>
        <div class="supplyModeField">
          <span>Supply</span>
          <div class="supplyModeButtons" role="group" aria-label="Origin stock source">
            <button type="button" :class="{ active: inputs.originStockMode === 'usual' }" @click="setStockMode('usual')">Usual</button>
            <button type="button" :class="{ active: inputs.originStockMode === 'recent' }" @click="setStockMode('recent')">Most Recent</button>
            <button type="button" :class="{ active: inputs.originStockMode === 'custom' }" @click="setStockMode('custom')">Custom</button>
          </div>
        </div>
      </div>
      <p class="calculatorHint">
        Origin Stock uses {{ inputs.originStockMode === 'usual' ? 'usual supply' : inputs.originStockMode === 'custom' ? 'custom supply where set, falling back to usual supply' : 'the most recently seen supply at the commodity origin, falling back to usual supply' }}.
        {{ rareStationStatus }}<span v-if="selectedStation"> · {{ selectedStation.label }}</span>
      </p>
    </fieldset>

    <div class="tableWrap">
      <table class="rareStationTradeTable">
        <thead>
          <tr>
            <th>Commodity</th>
            <th class="num">Sell Price</th>
            <th class="num">Profit</th>
            <th class="num">Origin Buy Price</th>
            <th class="num">Origin Stock</th>
            <th class="num" :title="TRIP_PROFIT_TITLE">Agg. Profit/Trip</th>
            <th class="num">Profit / Carrier</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rareStationLoading">
            <td colspan="7">Loading station prices...</td>
          </tr>
          <tr v-else-if="!calculatedRows.length">
            <td colspan="7">No rare commodity matches found for this station yet.</td>
          </tr>
          <template v-else>
            <tr v-for="row in calculatedRows" :key="row.commodity">
              <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div class="cellSub">{{ fmt(row.station_name) }} in {{ fmt(row.system_name) }}</div></td>
              <td class="num">{{ money(row.sell_price) }}</td>
              <td class="num"><span class="profit" :class="{ positive: row.profit > 0, negative: row.profit < 0 }">{{ money(row.profit) }}</span></td>
              <td class="num">{{ money(row.origin_buy_price) }}</td>
              <td class="num">
                <div v-if="customSupplyEditing === row.commodity" class="customSupplyEditor">
                  <input v-model="customSupplyDraft" type="number" min="0" step="1" aria-label="Custom supply" />
                  <button type="button" @click="saveCustomSupply(row)">Save</button>
                  <button type="button" class="secondary" @click="cancelCustomSupplyEdit">Cancel</button>
                </div>
                <div v-else class="supplyCell">
                  <span :title="customSupplyFor(row) !== null ? `Custom supply: ${money(customSupplyFor(row))}` : ''">{{ money(row.origin_stock) }}</span>
                  <button type="button" class="secondary compactButton" @click="startCustomSupplyEdit(row)">Set Custom</button>
                </div>
              </td>
              <td class="num" :title="`${TRIP_PROFIT_TITLE} Loads: ${row.loads_per_carrier}; unloads: ${row.unloads_per_carrier}.`">
                <div>{{ money(row.profit_per_trip) }}</div>
                <div class="cellSub tripCounts">Loads {{ money(row.loads_per_carrier) }} / Unloads {{ money(row.unloads_per_carrier) }}</div>
              </td>
              <td class="num">{{ money(row.profit_per_carrier) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>
