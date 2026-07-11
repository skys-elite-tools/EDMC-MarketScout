<script setup>
import { columnKey, commodityCellParts, compactDateTime, fmt, inaraCommoditySellUrl, localDateTime, money, potentialProfitClass, quantityClass, rowFlag } from '../utils.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
  displayColumns: { type: Array, default: () => [] },
  watchedCommodities: { type: Array, default: () => [] },
  priceThreshold: { type: Number, default: 6000 },
  supplyThreshold: { type: Number, default: 10000 },
  currentSystem: { type: String, default: '' },
})
const emit = defineEmits(['select'])

function flag(row) {
  return rowFlag(row, props.watchedCommodities, props.priceThreshold, props.supplyThreshold)
}

function searchSystem(row) {
  return props.currentSystem || row.system || ''
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
        <th>Flag</th><th>System / Station</th><th>State / Economy</th><th>Best Buy</th>
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
          <div v-if="row.best_buy_commodity" class="price"><div class="cellMain">{{ row.best_buy_commodity }} @ {{ money(row.best_buy_price) }}</div><div class="cellSub">Supply: <span :class="quantityClass(row.best_buy_supply)">{{ money(row.best_buy_supply) }}</span></div><div v-if="row.best_buy_potential_profit !== null && row.best_buy_potential_profit !== undefined" class="cellSub"><a class="potentialLink" :href="inaraCommoditySellUrl(searchSystem(row), row.best_buy_inara_id)" target="_blank" rel="noopener noreferrer" @click.stop>Potential Profit: <span :class="potentialProfitClass(row.best_buy_potential_profit)">{{ money(row.best_buy_potential_profit) }}</span> Cr/t</a></div></div>
          <span v-else>—</span>
        </td>
        <td v-for="col in displayColumns" :key="columnKey(col)">
          <div class="price"><div class="cellMain">{{ commodityCellParts(row, col.commodity, col.side).price }}</div><div class="cellSub">{{ commodityCellParts(row, col.commodity, col.side).qtyName }}: <span :class="commodityCellParts(row, col.commodity, col.side).qtyClass">{{ commodityCellParts(row, col.commodity, col.side).qty }}</span></div><div v-if="commodityCellParts(row, col.commodity, col.side).hasPotentialProfit" class="cellSub"><a class="potentialLink" :href="inaraCommoditySellUrl(searchSystem(row), commodityCellParts(row, col.commodity, col.side).inaraId)" target="_blank" rel="noopener noreferrer" @click.stop>Potential Profit: <span :class="commodityCellParts(row, col.commodity, col.side).potentialProfitClass">{{ commodityCellParts(row, col.commodity, col.side).potentialProfit }}</span> Cr/t</a></div></div>
        </td>
        <td><div :title="localDateTime(row.market_updated)">{{ compactDateTime(row.market_updated) }}</div><div class="cellSub" :title="localDateTime(row.station_visit)">Visit: {{ compactDateTime(row.station_visit) }}</div></td>
      </tr>
    </tbody>
  </table>
</template>
