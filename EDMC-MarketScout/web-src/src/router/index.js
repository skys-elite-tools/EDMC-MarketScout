import { createRouter, createWebHashHistory } from 'vue-router'
import AnalyzeCommoditiesView from '../views/AnalyzeCommoditiesView.vue'
import CarrierTradeAnnouncementsView from '../views/CarrierTradeAnnouncementsView.vue'
import CarrierTradeCalculatorView from '../views/CarrierTradeCalculatorView.vue'
import CarrierTripPlannerView from '../views/CarrierTripPlannerView.vue'
import CommoditiesView from '../views/CommoditiesView.vue'
import ConfigurationView from '../views/ConfigurationView.vue'
import JackpotsView from '../views/JackpotsView.vue'
import LedgerView from '../views/LedgerView.vue'
import RareCommoditiesView from '../views/RareCommoditiesView.vue'
import StationsView from '../views/StationsView.vue'

export const routes = [
  {
    path: '/',
    redirect: '/stations',
  },
  {
    path: '/stations',
    name: 'stations',
    component: StationsView,
    meta: {
      title: 'Stations',
      description: 'Lists scouting data for stations visited while EDMC was running.',
    },
  },
  {
    path: '/jackpots',
    name: 'jackpots',
    component: JackpotsView,
    meta: {
      title: 'Jackpots',
      description: 'Tracks high-value buy opportunities and how they change over time.',
    },
  },
  {
    path: '/ledger',
    name: 'ledger',
    component: LedgerView,
    meta: {
      title: 'Ledger',
      description: 'Shows Journal buy and sell entries with profit and trade-rate context.',
    },
  },
  {
    path: '/commodities',
    name: 'commodities',
    component: CommoditiesView,
    meta: {
      title: 'Commodities',
      description: 'Browses imported global commodity stats used by Best Buy calculations.',
    },
  },
  {
    path: '/rare',
    name: 'rare',
    component: RareCommoditiesView,
    meta: {
      title: 'Rare Commodities',
      description: 'Lists rare commodity sources, engineering unlock needs, and travel distances.',
      helpArticle: 'rare-supply',
    },
  },
  {
    path: '/analyze',
    name: 'analyze',
    component: AnalyzeCommoditiesView,
    meta: {
      title: 'Analyze Commodities',
      description: 'Matches pasted commodity lists against regular and rare commodity data.',
    },
  },
  {
    path: '/carrier',
    name: 'carrier',
    component: CarrierTradeAnnouncementsView,
    meta: {
      title: 'Carrier Trade Announcements',
      description: 'Creates Fleet Carrier trade announcement images and shareable text.',
    },
  },
  {
    path: '/carrier-calculator',
    name: 'carrierCalc',
    component: CarrierTradeCalculatorView,
    meta: {
      title: 'Carrier Trade Calculator',
      description: 'Calculates carrier buy/sell prices and profit splits for station trades and rare commodities.',
      helpArticle: 'carrier-calculator',
    },
  },
  {
    path: '/carrier-trip-planner',
    name: 'carrierTripPlanner',
    component: CarrierTripPlannerView,
    meta: {
      title: 'Carrier Trip Planner',
      description: 'Imports and tracks Spansh Fleet Carrier routes with distance, tritium, and refueling details.',
    },
  },
  {
    path: '/config',
    name: 'config',
    component: ConfigurationView,
    meta: {
      title: 'Configuration',
      description: 'Manages the local web address, shared port, and optional LAN access.',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/stations',
  },
]

export const viewPathByName = Object.fromEntries(
  routes
    .filter(route => route.name && route.path)
    .map(route => [route.name, route.path]),
)

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
