<script setup>
import { columnKey, commodityCellParts, fmt, localDateTime, money, rowFlag } from '../utils.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
  displayColumns: { type: Array, default: () => [] },
  watchedCommodities: { type: Array, default: () => [] },
  priceThreshold: { type: Number, default: 6000 },
  supplyThreshold: { type: Number, default: 10000 },
})
const emit = defineEmits(['select'])

function flag(row) {
  return rowFlag(row, props.watchedCommodities, props.priceThreshold, props.supplyThreshold)
}
</script>

<template>
  <table>
    <thead>
      <tr>
        <th>Flag</th><th>System / Station</th><th>State / Economy</th><th>Best Buy</th>
        <th v-for="col in displayColumns" :key="columnKey(col)">{{ col.commodity }} {{ col.side === 'buy' ? 'Buy' : 'Sell' }}</th>
        <th>Updated</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.market_id || idx}-${row.system}-${row.station}`" :class="[flag(row).cls, { selected: idx === selectedIndex }]" @click="emit('select', idx)">
        <td class="flag">{{ flag(row).text }}</td>
        <td><div class="systemName">{{ fmt(row.system) }}</div><div class="stationName">{{ fmt(row.station) }} <span class="stationMeta">| Pad {{ fmt(row.pad) }}</span></div></td>
        <td><div class="cellMain">{{ fmt(row.state) }}</div><div class="cellSub">{{ fmt(row.economies) }}</div></td>
        <td>
          <div v-if="row.best_buy_commodity" class="price"><div class="cellMain">{{ row.best_buy_commodity }} @ {{ money(row.best_buy_price) }}</div><div class="cellSub">supply: {{ money(row.best_buy_supply) }} · score: {{ money(row.best_buy_score) }}</div></div>
          <span v-else>—</span>
        </td>
        <td v-for="col in displayColumns" :key="columnKey(col)">
          <div class="price"><div class="cellMain">{{ commodityCellParts(row, col.commodity, col.side).price }}</div><div class="cellSub">{{ commodityCellParts(row, col.commodity, col.side).qtyName }}: {{ commodityCellParts(row, col.commodity, col.side).qty }}</div></div>
        </td>
        <td><div>{{ localDateTime(row.market_updated) }}</div><div class="cellSub">Visit: {{ localDateTime(row.station_visit) }}</div></td>
      </tr>
    </tbody>
  </table>
</template>
