<script setup>
const props = defineProps({
  currentView: { type: String, required: true },
})
const emit = defineEmits(['update:currentView', 'refresh'])

function choose(view) {
  if (view === props.currentView) emit('refresh')
  else emit('update:currentView', view)
}
</script>

<template>
  <header class="topBar">
    <div class="brandBlock">
      <div class="logoPlaceholder">MS</div>
      <div>
        <h1>EDMC-MarketScout</h1>
        <p class="subtitle">Local-only scouting database. No uploads, no external scripts.</p>
      </div>
    </div>

    <nav class="mainNav" aria-label="Main view navigation">
      <button type="button" :class="{ active: currentView === 'stations' }" @click="choose('stations')">Stations</button>
      <button type="button" :class="{ active: currentView === 'jackpots' }" @click="choose('jackpots')">Jackpots</button>
      <button type="button" :class="{ active: currentView === 'ledger' }" @click="choose('ledger')">Ledger</button>
      <button type="button" :class="{ active: currentView === 'commodities' }" @click="choose('commodities')">Commodities</button>
      <button type="button" :class="{ active: currentView === 'rare' }" @click="choose('rare')">Rare Commodities</button>
      <button type="button" :class="{ active: currentView === 'analyze' }" @click="choose('analyze')">Analyze Commodities</button>
      <button type="button" :class="{ active: currentView === 'carrier' }" @click="choose('carrier')">Carrier Trade Alert</button>
    </nav>

    <div class="topLinks">
      <a class="hiddenFutureLink" href="#" title="Placeholder for future donation link">Donate</a>
    </div>

  </header>
</template>
