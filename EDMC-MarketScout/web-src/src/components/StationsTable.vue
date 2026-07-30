<script setup>
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import InfoButton from './InfoButton.vue'
import { useCommoditySettingsStore } from '../stores/commoditySettingsStore.js'
import { useStationViewStore } from '../stores/stationViewStore.js'
import { useStatusStore } from '../stores/statusStore.js'
import { useStationsStore } from '../stores/stationsStore.js'
import { useSystemStore } from '../stores/systemStore.js'
import { columnKey, commodityCellParts, compactDateTime, fmt, inaraCommoditySellUrl, localDateTime, money, potentialProfitClass, potentialProfitTooltip, quantityClass, rowFlag, shouldDisplayPotentialProfit } from '../utils.js'

const stationsStore = useStationsStore()
const stationViewStore = useStationViewStore()
const commoditySettingsStore = useCommoditySettingsStore()
const statusStore = useStatusStore()
const systemStore = useSystemStore()
const {
  rows,
  selectedIndex,
  stationRowsLoading,
  stationPage,
  loadMoreLabel,
} = storeToRefs(stationsStore)
const {
  watchedCommodities,
  minimumPotentialProfit,
} = storeToRefs(commoditySettingsStore)
const {
  filters,
  stationScoutMode,
  stationRowLimit,
} = storeToRefs(stationViewStore)
const { latestJournalEvent } = storeToRefs(statusStore)
const displayColumns = computed(() => {
  const side = stationScoutMode.value === 'sell' ? 'sell' : 'buy'
  return watchedCommodities.value.map(commodity => ({ commodity, side }))
})

function flag(row) {
  return rowFlag(
    row,
    watchedCommodities.value,
    filters.value.priceThreshold,
    filters.value.supplyThreshold,
    stationScoutMode.value,
    filters.value.sellPriceThreshold,
    filters.value.demandThreshold,
  )
}

function searchSystem(row) {
  return latestJournalEvent.value?.system || row.system || ''
}

function cellParts(row, col) {
  return commodityCellParts(row, col.commodity, col.side, minimumPotentialProfit.value)
}

function pendingStates(row) {
  return String(row?.station_faction_pending_states || '')
    .split('|')
    .map(state => state.trim())
    .filter(Boolean)
}

function firstPendingState(row) {
  return stateDisplayName(pendingStates(row)[0] || '')
}

function pendingStateTitle(row) {
  const states = pendingStates(row).map(stateDisplayName)
  return states.length ? `Pending station owner states: ${states.join(', ')}` : ''
}

function stateDisplayName(state) {
  return String(state || '').replace(/([a-z])([A-Z])/g, '$1 $2')
}

function loadMoreStations() {
  stationsStore.loadMoreStations({ rowLimit: stationRowLimit.value, params: stationViewStore.stationParams })
}
</script>

<template>
  <table class="stationsTable">
    <colgroup>
      <col class="stationFlagCol" />
      <col class="stationIdentityCol" />
      <col class="stationStateCol" />
      <col class="stationBestBuyCol" />
      <col v-for="col in displayColumns" :key="`col-${columnKey(col)}`" class="stationCommodityCol" />
      <col class="stationUpdatedCol" />
    </colgroup>
    <thead>
      <tr>
        <th>Flag</th><th>System / Station</th><th>Owner State / Economy</th>
        <th><span class="headerWithInfo">Best Buy <InfoButton title="How Best Buy works" @open="systemStore.openHelp('best-buy')" /></span></th>
        <th v-for="col in displayColumns" :key="columnKey(col)">{{ col.commodity }} {{ col.side === 'buy' ? 'Buy' : 'Sell' }}</th>
        <th>Updated</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.market_id || idx}-${row.system}-${row.station}`" :class="[flag(row).cls, { selected: idx === selectedIndex }]" @click="stationsStore.setSelectedIndex(idx)">
        <td class="flag">
          <div v-for="item in flag(row).items" :key="item" class="flagItem">{{ flag(row).marker }} {{ item }}</div>
        </td>
        <td><div class="systemName">{{ fmt(row.system) }}</div><div class="stationName">{{ fmt(row.station) }} <span class="stationMeta">Pad {{ fmt(row.pad) }}</span></div></td>
        <td>
          <div class="cellMain">{{ fmt(row.station_faction_state) }}</div>
          <div v-if="firstPendingState(row)" class="pendingStateBadge" :title="pendingStateTitle(row)">
            Pending: {{ firstPendingState(row) }}
          </div>
          <div class="cellSub">{{ fmt(row.economies) }}</div>
        </td>
        <td>
          <div v-if="row.best_buy_commodity" class="price"><div class="cellMain">{{ row.best_buy_commodity }} @ {{ money(row.best_buy_price) }}</div><div class="cellSub">Supply: <span :class="quantityClass(row.best_buy_supply)">{{ money(row.best_buy_supply) }}</span></div><div v-if="shouldDisplayPotentialProfit(row.best_buy_potential_profit, minimumPotentialProfit)" class="cellSub"><a class="potentialLink" :href="inaraCommoditySellUrl(searchSystem(row), row.best_buy_inara_id)" :title="potentialProfitTooltip(row.best_buy_max_sell)" target="_blank" rel="noopener noreferrer" @click.stop>Potential Profit: <span :class="potentialProfitClass(row.best_buy_potential_profit)">{{ money(row.best_buy_potential_profit) }}</span> Cr/t</a></div></div>
          <div v-else class="price"><span>—</span></div>
        </td>
        <td v-for="col in displayColumns" :key="columnKey(col)">
          <div class="price">
            <div class="cellMain">{{ cellParts(row, col).price }}</div>
            <div v-if="cellParts(row, col).showQuantity" class="cellSub">
              {{ cellParts(row, col).qtyName }}:
              <span :class="cellParts(row, col).qtyClass">{{ cellParts(row, col).qty }}</span>
            </div>
            <div v-if="cellParts(row, col).hasPotentialProfit" class="cellSub">
              <a class="potentialLink" :href="inaraCommoditySellUrl(searchSystem(row), cellParts(row, col).inaraId)" :title="potentialProfitTooltip(cellParts(row, col).maxSell)" target="_blank" rel="noopener noreferrer" @click.stop>Potential Profit: <span :class="cellParts(row, col).potentialProfitClass">{{ cellParts(row, col).potentialProfit }}</span> Cr/t</a>
            </div>
            <div v-if="cellParts(row, col).hasSellProfit" class="cellSub" :title="cellParts(row, col).sellProfitBasis ? `Based on ${cellParts(row, col).sellProfitBasis}.` : ''">
              Profit: <span :class="cellParts(row, col).sellProfitClass">{{ cellParts(row, col).sellProfit }}</span> Cr/t
            </div>
          </div>
        </td>
        <td><div :title="localDateTime(row.market_updated)">{{ compactDateTime(row.market_updated) }}</div><div class="cellSub" :title="localDateTime(row.station_visit)">Visit: {{ compactDateTime(row.station_visit) }}</div></td>
      </tr>
    </tbody>
  </table>
  <div class="stationLoadMoreBar">
    <button
      type="button"
      class="loadMoreButton"
      :class="{ loading: stationRowsLoading }"
      :disabled="stationRowsLoading || !stationPage.hasMore"
      :aria-busy="stationRowsLoading ? 'true' : 'false'"
      @click="loadMoreStations"
    >
      <span v-if="stationRowsLoading" class="loadMoreSpinner" aria-hidden="true"></span>
      <span>{{ stationRowsLoading ? 'Loading more stations...' : loadMoreLabel }}</span>
    </button>
  </div>
</template>
