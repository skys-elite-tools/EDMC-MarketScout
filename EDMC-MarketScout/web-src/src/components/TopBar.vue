<script setup>
import logoUrl from '../assets/marketscout-logo-v1.png'
import analyzeIcon from '../assets/buttons/analyze-commodities.png'
import commoditiesIcon from '../assets/buttons/commodities.png'
import configIcon from '../assets/buttons/configuration.png'
import jackpotsIcon from '../assets/buttons/jackpots.png'
import ledgerIcon from '../assets/buttons/ledger.png'
import rareIcon from '../assets/buttons/rare-commodities.png'
import stationIcon from '../assets/buttons/station.png'
import carrierIcon from '../assets/buttons/trade-carrier-announcements.png'

const props = defineProps({
  currentView: { type: String, required: true },
})
const emit = defineEmits(['update:currentView', 'refresh'])
const navItems = [
  { view: 'stations', label: 'Stations', icon: stationIcon },
  { view: 'jackpots', label: 'Jackpots', icon: jackpotsIcon },
  { view: 'ledger', label: 'Ledger', icon: ledgerIcon },
  { view: 'commodities', label: 'Commodities', icon: commoditiesIcon },
  { view: 'rare', label: 'Rare Commodities', icon: rareIcon },
  { view: 'analyze', label: 'Analyze Commodities', icon: analyzeIcon },
  { view: 'carrier', label: 'Carrier Trade Announcements', icon: carrierIcon },
  { view: 'config', label: 'Config', icon: configIcon },
]

function choose(view) {
  if (view === props.currentView) emit('refresh')
  else emit('update:currentView', view)
}
</script>

<template>
  <header class="topBar">
    <div class="brandBlock">
      <img class="appLogo" :src="logoUrl" alt="MarketScout logo" />
      <div>
        <h1>EDMC-MarketScout</h1>
        <p class="subtitle">Local-only scouting database. No uploads, no external scripts.</p>
      </div>
    </div>

    <nav class="mainNav" aria-label="Main view navigation">
      <button
        v-for="item in navItems"
        :key="item.view"
        type="button"
        class="navButton"
        :class="{ active: currentView === item.view }"
        @click="choose(item.view)"
      >
        <img class="navButtonIcon" :src="item.icon" alt="" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="topLinks">
      <a class="hiddenFutureLink" href="#" title="Placeholder for future donation link">Donate</a>
    </div>

  </header>
</template>
