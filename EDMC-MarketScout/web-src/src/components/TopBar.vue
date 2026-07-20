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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  currentView: { type: String, required: true },
})
const emit = defineEmits(['update:currentView', 'refresh'])
const navItems = [
  { view: 'stations', label: 'Stations', icon: stationIcon },
  { view: 'jackpots', label: 'Jackpots', icon: jackpotsIcon },
  { view: 'ledger', label: 'Ledger', icon: ledgerIcon },
  { view: 'config', label: 'Config', icon: configIcon },
]
const commodityItems = [
  { view: 'commodities', label: 'List Commodities', icon: commoditiesIcon },
  { view: 'rare', label: 'Rare Commodities', icon: rareIcon },
  { view: 'analyze', label: 'Analyze Commodities', icon: analyzeIcon },
]
const carrierItems = [
  { view: 'carrier', label: 'Trade Announcements', icon: carrierIcon },
  { view: 'carrierCalc', label: 'Trade Calculator', icon: carrierIcon },
]
const commoditiesMenuOpen = ref(false)
const carrierMenuOpen = ref(false)
const mobileMenuOpen = ref(false)
const commoditiesMenuRef = ref(null)
const carrierMenuRef = ref(null)
const mobileMenuRef = ref(null)
const commoditiesActive = computed(() => commodityItems.some((item) => item.view === props.currentView))
const carrierActive = computed(() => carrierItems.some((item) => item.view === props.currentView))
const mobileNavGroups = computed(() => [
  navItems.slice(0, 3),
  commodityItems,
  carrierItems,
  navItems.slice(3),
])

function choose(view) {
  commoditiesMenuOpen.value = false
  carrierMenuOpen.value = false
  mobileMenuOpen.value = false
  if (view === props.currentView) emit('refresh')
  else emit('update:currentView', view)
}

function toggleCommoditiesMenu() {
  commoditiesMenuOpen.value = !commoditiesMenuOpen.value
  carrierMenuOpen.value = false
}

function toggleCarrierMenu() {
  carrierMenuOpen.value = !carrierMenuOpen.value
  commoditiesMenuOpen.value = false
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function handleDocumentClick(event) {
  if (commoditiesMenuRef.value && !commoditiesMenuRef.value.contains(event.target)) {
    commoditiesMenuOpen.value = false
  }
  if (carrierMenuRef.value && !carrierMenuRef.value.contains(event.target)) {
    carrierMenuOpen.value = false
  }
  if (mobileMenuRef.value && !mobileMenuRef.value.contains(event.target)) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocumentClick))
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
        v-for="item in navItems.slice(0, 3)"
        :key="item.view"
        type="button"
        class="navButton"
        :class="{ active: currentView === item.view }"
        @click="choose(item.view)"
      >
        <img class="navButtonIcon" :src="item.icon" alt="" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </button>

      <div ref="commoditiesMenuRef" class="navMenu">
        <button
          type="button"
          class="navButton navMenuButton"
          :class="{ active: commoditiesActive }"
          :aria-expanded="commoditiesMenuOpen"
          aria-haspopup="menu"
          @click.stop="toggleCommoditiesMenu"
        >
          <img class="navButtonIcon" :src="commoditiesIcon" alt="" aria-hidden="true" />
          <span>Commodities</span>
          <span class="navMenuArrow" aria-hidden="true">▾</span>
        </button>
        <div v-if="commoditiesMenuOpen" class="navMenuList" role="menu">
          <button
            v-for="item in commodityItems"
            :key="item.view"
            type="button"
            class="navMenuItem"
            :class="{ active: currentView === item.view }"
            role="menuitem"
            @click="choose(item.view)"
          >
            <img class="navButtonIcon" :src="item.icon" alt="" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </div>

      <div ref="carrierMenuRef" class="navMenu">
        <button
          type="button"
          class="navButton navMenuButton"
          :class="{ active: carrierActive }"
          :aria-expanded="carrierMenuOpen"
          aria-haspopup="menu"
          @click.stop="toggleCarrierMenu"
        >
          <img class="navButtonIcon" :src="carrierIcon" alt="" aria-hidden="true" />
          <span>Carrier Tools</span>
          <span class="navMenuArrow" aria-hidden="true">▾</span>
        </button>
        <div v-if="carrierMenuOpen" class="navMenuList" role="menu">
          <button
            v-for="item in carrierItems"
            :key="item.view"
            type="button"
            class="navMenuItem"
            :class="{ active: currentView === item.view }"
            role="menuitem"
            @click="choose(item.view)"
          >
            <img class="navButtonIcon" :src="item.icon" alt="" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </div>

      <button
        v-for="item in navItems.slice(3)"
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

    <div ref="mobileMenuRef" class="mobileNav">
      <button
        type="button"
        class="mobileNavToggle"
        :class="{ active: mobileMenuOpen }"
        :aria-expanded="mobileMenuOpen"
        aria-haspopup="menu"
        aria-label="Open navigation menu"
        @click.stop="toggleMobileMenu"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
      <div v-if="mobileMenuOpen" class="mobileNavMenu" role="menu">
        <template v-for="(group, groupIndex) in mobileNavGroups" :key="groupIndex">
          <div v-if="groupIndex > 0" class="mobileNavDivider"></div>
          <button
            v-for="item in group"
            :key="item.view"
            type="button"
            class="navMenuItem mobileNavItem"
            :class="{ active: currentView === item.view }"
            role="menuitem"
            @click="choose(item.view)"
          >
            <img class="navButtonIcon" :src="item.icon" alt="" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </template>
      </div>
    </div>

  </header>
</template>
