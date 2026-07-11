<script setup>
import { fmt, money, num, shortTime } from '../utils.js'

defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
  showLifo: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])
</script>

<template>
  <table>
    <thead><tr><th>Time</th><th>Type</th><th>System / Station</th><th>Commodity</th><th>Qty</th><th>Unit</th><th>Total</th><th>Avg Paid</th><th>Profit</th><th>Cr/hr</th><th v-if="showLifo">LIFO avg</th><th v-if="showLifo">LIFO profit</th></tr></thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="row.trade_id || idx" :class="[{ selected: idx === selectedIndex, ledgerBuy: row.event_type === 'buy', ledgerSell: row.event_type === 'sell', cheap: row.event_type === 'sell' && num(row.journal_profit) > 0 }]" @click="emit('select', idx)">
        <td>{{ shortTime(row.event_datetime) }}</td><td><span class="tradeType" :class="row.event_type">{{ row.event_type === 'buy' ? 'BUY' : row.event_type === 'sell' ? 'SELL' : fmt(row.event_type) }}</span></td>
        <td><div class="cellMain">{{ fmt(row.system_name) }}</div><div class="cellSub">{{ fmt(row.station_name) }}</div></td>
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div v-if="row.event_type === 'buy' && row.supply_at_trade != null" class="cellSub">Supply: {{ money(row.supply_at_trade) }}</div><div v-else-if="row.event_type === 'sell' && row.demand_at_trade != null" class="cellSub">Demand: {{ money(row.demand_at_trade) }}</div></td>
        <td class="num">{{ money(row.quantity) }}</td><td class="num">{{ money(row.unit_price) }}</td><td class="num">{{ money(row.total_credits) }}</td>
        <td class="num">{{ money(row.journal_avg_price_paid) }}</td><td class="num"><span class="profit" :class="{ positive: num(row.journal_profit) > 0, negative: num(row.journal_profit) < 0 }">{{ money(row.journal_profit) }}</span></td><td class="num">{{ money(row.profit_per_hour ?? row.credits_per_hour) }}</td>
        <td v-if="showLifo" class="num">{{ money(row.ledger_avg_buy_price) }}</td><td v-if="showLifo" class="num">{{ money(row.ledger_profit) }}</td>
      </tr>
    </tbody>
  </table>
</template>
