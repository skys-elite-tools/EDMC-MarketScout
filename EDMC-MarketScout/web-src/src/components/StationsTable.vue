<script setup>
import InfoButton from './InfoButton.vue'
import { columnKey, commodityCellParts, compactDateTime, fmt, inaraCommoditySellUrl, localDateTime, money, potentialProfitClass, potentialProfitTooltip, quantityClass, rowFlag, shouldDisplayPotentialProfit } from '../utils.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
  displayColumns: { type: Array, default: () => [] },
  watchedCommodities: { type: Array, default: () => [] },
  scoutMode: { type: String, default: 'buy' },
  priceThreshold: { type: Number, default: 6000 },
  supplyThreshold: { type: Number, default: 10000 },
  sellPriceThreshold: { type: Number, default: 40000 },
  demandThreshold: { type: Number, default: 10000 },
  minimumPotentialProfit: { type: Number, default: 10000 },
  currentSystem: { type: String, default: '' },
})
const emit = defineEmits(['select', 'open-help'])

function flag(row) {
  return rowFlag(row, props.watchedCommodities, props.priceThreshold, props.supplyThreshold, props.scoutMode, props.sellPriceThreshold, props.demandThreshold)
}

function searchSystem(row) {
  return props.currentSystem || row.system || ''
}

function cellParts(row, col) {
  return commodityCellParts(row, col.commodity, col.side, props.minimumPotentialProfit)
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
        <th>Flag</th><th>System / Station</th><th>State / Economy</th>
        <th><span class="headerWithInfo">Best Buy <InfoButton title="How Best Buy works" @open="emit('open-help', 'best-buy')" /></span></th>
        <th v-for="col in displayColumns" :key="columnKey(col)">{{ col.commodity }} {{ col.side === 'buy' ? 'Buy' : 'Sell' }}</th>
        <th>Updated</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.market_id || idx}-${row.system}-${row.station}`" :class="[flag(row).cls, { selected: idx === selectedIndex }]" @click="emit('select', idx)">
        <td class="flag">
          <div v-for="item in flag(row).items" :key="item" class="flagItem">{{ flag(row).marker }} {{ item }}</div>
        </td>
        <td><div class="systemName">{{ fmt(row.system) }}</div><div class="stationName">{{ fmt(row.station) }} <span class="stationMeta">Pad {{ fmt(row.pad) }}</span></div></td>
        <td><div class="cellMain">{{ fmt(row.state) }}</div><div class="cellSub">{{ fmt(row.economies) }}</div></td>
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
</template>
