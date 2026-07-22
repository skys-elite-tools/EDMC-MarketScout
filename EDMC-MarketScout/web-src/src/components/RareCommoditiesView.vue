<script setup>
import { fmt, ly, money, num, rareDateTime } from '../utils.js'

defineProps({
  rows: { type: Array, default: () => [] },
  selectedIndex: { type: Number, default: -1 },
})

function profitTitle(row) {
  const avg = money(row.galactic_average_price)
  if (avg === '—') {
    return 'Profit if sold at 100x galactic average which is the maximum for fleet carriers.'
  }
  return `Galactic Average = ${avg} Cr. Profit if sold at 100x galactic average, which is the maximum for fleet carriers.`
}

function profitClass(row) {
  const profit = num(row.carrier_profit)
  if (profit === null) return ''
  return profit > 0 ? 'positive' : profit < 0 ? 'negative' : ''
}
</script>

<template>
  <table class="rareTable">
    <thead>
      <tr>
        <th>Commodity</th>
        <th>System</th>
        <th>Station</th>
        <th class="num">St. dist</th>
        <th class="num">Distance</th>
        <th class="num">Supply</th>
        <th class="num">Highest</th>
        <th class="num">Recent</th>
        <th class="num">Rec.Date</th>
        <th class="num">Buy Price</th>
        <th class="num">Gal. Avg</th>
        <th class="num">100x Gal. Avg</th>
        <th class="num">Profit</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(row, idx) in rows"
        :key="row.commodity || idx"
        :class="[{ selected: idx === selectedIndex, engineeringRare: row.is_engineering_rare }]"
      >
        <td><div class="cellMain">{{ fmt(row.commodity) }}</div><div v-if="row.is_engineering_rare" class="cellSub" :title="row.engineering_unlocks_title || ''">{{ fmt(row.engineering_unlocks) }}</div></td>
        <td>{{ fmt(row.system_name) }}</td>
        <td>{{ fmt(row.station_name) }}</td>
        <td class="num">{{ money(row.station_distance_ls) }}</td>
        <td class="num">{{ ly(row.distance_from_current_ly) }}</td>
        <td class="num">{{ money(row.usual_supply) }}</td>
        <td class="num" :title="`Highest seen: ${rareDateTime(row.highest_supply_datetime)}`">{{ money(row.highest_supply) }}</td>
        <td class="num">{{ money(row.recent_supply) }}</td>
        <td class="num">{{ rareDateTime(row.recent_supply_datetime) }}</td>
        <td class="num">{{ money(row.buy_price) }}</td>
        <td class="num">{{ money(row.galactic_average_price) }}</td>
        <td class="num">{{ money(row.galactic_average_100x) }}</td>
        <td class="num" :title="profitTitle(row)"><span class="profit" :class="profitClass(row)">{{ money(row.carrier_profit) }}</span></td>
      </tr>
    </tbody>
  </table>
</template>
