<script setup>
import { fmt, money } from '../utils.js'

defineProps({
  rows: { type: Array, default: () => [] },
})
</script>

<template>
  <table class="commoditiesTable">
    <thead>
      <tr>
        <th>Commodity</th>
        <th>Category</th>
        <th class="num">Min Buy</th>
        <th class="num">Avg Buy</th>
        <th class="num">Max Sell</th>
        <th class="num">Max Profit</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, idx) in rows" :key="`${row.commodity || 'commodity'}-${idx}`">
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div></td>
        <td>{{ fmt(row.category) }}</td>
        <td class="num">{{ money(row.min_buy) }}</td>
        <td class="num">{{ money(row.avg_buy) }}</td>
        <td class="num">{{ money(row.max_sell) }}</td>
        <td class="num"><span class="profit positive">{{ money(row.max_profit) }}</span></td>
      </tr>
    </tbody>
  </table>
</template>
