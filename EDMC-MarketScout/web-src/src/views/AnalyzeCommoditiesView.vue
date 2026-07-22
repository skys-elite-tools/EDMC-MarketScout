<script setup>
import { computed, ref, watch } from 'vue'
import { fmt, ly, money, num } from '../utils.js'

const STORAGE_KEY = 'marketscout.analyzeCommodities.text'

function storedText() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || ''
  } catch (err) {
    return ''
  }
}

const text = ref(storedText())
const loading = ref(false)
const regularRows = ref([])
const rareRows = ref([])
const status = ref('')
const regularSort = ref('commodity')
const rareSort = ref('commodity')

function sortText(a, b, key) {
  return String(a[key] || '').localeCompare(String(b[key] || ''))
}

function sortNumberDesc(a, b, key) {
  const av = num(a[key])
  const bv = num(b[key])
  if (av === null && bv === null) return sortText(a, b, 'commodity')
  if (av === null) return 1
  if (bv === null) return -1
  return bv - av || sortText(a, b, 'commodity')
}

const sortedRegular = computed(() => {
  const rows = [...regularRows.value]
  if (regularSort.value === 'category') {
    rows.sort((a, b) => sortText(a, b, 'category') || sortText(a, b, 'commodity'))
  } else {
    rows.sort((a, b) => sortText(a, b, 'commodity'))
  }
  return rows
})

const sortedRare = computed(() => {
  const rows = [...rareRows.value]
  if (rareSort.value === 'usual_supply_desc') {
    rows.sort((a, b) => sortNumberDesc(a, b, 'usual_supply'))
  } else {
    rows.sort((a, b) => sortText(a, b, 'commodity'))
  }
  return rows
})

watch(text, (value) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, value)
  } catch (err) {
    // Ignore private browsing or storage quota failures.
  }
})

async function analyze() {
  loading.value = true
  status.value = ''
  try {
    const res = await fetch('/api/analyze-commodities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.value }),
    })
    const data = await res.json()
    regularRows.value = data.regular || []
    rareRows.value = data.rare || []
    status.value = `${regularRows.value.length} regular / ${rareRows.value.length} rare`
  } catch (err) {
    status.value = 'Analysis failed'
    regularRows.value = []
    rareRows.value = []
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="analyzeCommodities">
    <div class="analyzeInput">
      <textarea v-model="text" rows="4" placeholder="Ultra-Compact Processor Prototypes, Eden Apples Of Aerial, Aganippe Rush"></textarea>
      <div class="analyzeActions">
        <button type="button" :disabled="loading" @click="analyze">{{ loading ? 'Analyzing...' : 'Analyze' }}</button>
        <span class="small">{{ status }}</span>
      </div>
    </div>

    <div class="analysisTables">
      <section>
        <h2>Regular</h2>
        <table class="analysisRegularTable">
          <thead>
            <tr>
              <th><button type="button" class="tableSortButton" @click="regularSort = 'commodity'">Commodity</button></th>
              <th><button type="button" class="tableSortButton" @click="regularSort = 'category'">Category</button></th>
              <th class="num">Min Price</th>
              <th class="num">Max Profit</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedRegular" :key="row.commodity">
              <td><div class="cellMain">{{ fmt(row.commodity) }}</div></td>
              <td>{{ fmt(row.category) }}</td>
              <td class="num">{{ money(row.min_buy) }}</td>
              <td class="num"><span class="profit positive">{{ money(row.max_profit) }}</span></td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2>Rare</h2>
        <table class="analysisRareTable">
          <thead>
            <tr>
              <th><button type="button" class="tableSortButton" @click="rareSort = 'commodity'">Commodity</button></th>
              <th>System</th>
              <th>Station</th>
              <th class="num" title="Distance from current system">Dist</th>
              <th class="num" title="Usual supply"><button type="button" class="tableSortButton" @click="rareSort = 'usual_supply_desc'">Supply</button></th>
              <th class="num">Buy</th>
              <th class="num" title="100x galactic average">100x</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedRare" :key="row.commodity">
              <td><div class="cellMain">{{ fmt(row.commodity) }}</div></td>
              <td>{{ fmt(row.system_name) }}</td>
              <td>{{ fmt(row.station_name) }}</td>
              <td class="num">{{ ly(row.distance_from_current_ly) }}</td>
              <td class="num">{{ money(row.usual_supply) }}</td>
              <td class="num">{{ money(row.buy_price) }}</td>
              <td class="num">{{ money(row.galactic_average_100x) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>
