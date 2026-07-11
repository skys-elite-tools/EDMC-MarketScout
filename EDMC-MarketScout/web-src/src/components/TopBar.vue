<script setup>
const props = defineProps({
  currentView: { type: String, required: true },
  statusText: { type: String, default: '' },
  autoRefresh: { type: Boolean, default: true },
})
const emit = defineEmits(['update:currentView', 'update:autoRefresh', 'refresh'])

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
    </nav>

    <div class="topLinks">
      <a href="#" title="Placeholder for future links">Links</a>
      <a href="#" title="Placeholder for future donation link">Donate</a>
    </div>

    <div class="status">
      <span>{{ statusText }}</span>
      <label><input type="checkbox" :checked="autoRefresh" @change="emit('update:autoRefresh', $event.target.checked)" /> Auto-refresh</label>
    </div>
  </header>
</template>
