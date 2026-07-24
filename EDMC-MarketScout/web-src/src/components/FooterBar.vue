<script setup>
import { nextTick, ref, watch } from 'vue'
import ModalShell from './ModalShell.vue'

const props = defineProps({
  helpArticle: { type: String, default: '' },
  helpRequestId: { type: Number, default: 0 },
})

const aboutOpen = ref(false)
const helpOpen = ref(false)

const thanks = [
  ['Elite:Dangerous Market Connector (EDMC)', 'https://github.com/EDCD/EDMarketConnector'],
  ["Conshmea's ACO Trade Helper", 'https://conshmea.com/acoTradeHelper'],
  ['Inara', 'https://inara.cz'],
  ['Spansh', 'https://spansh.co.uk'],
  ['EDDiscovery', 'https://github.com/EDDiscovery/EDDiscovery'],
  ['The very helpful people in the P.T.N.', 'https://pilotstradenetwork.com/'],
]

async function openHelp(article = '') {
  helpOpen.value = true
  if (!article) return
  await nextTick()
  document.getElementById(`help-${article}`)?.scrollIntoView({ block: 'start' })
}

watch(() => props.helpRequestId, () => {
  openHelp(props.helpArticle)
})
</script>

<template>
  <footer class="footerBar">
    <span>MarketScout Web UI</span>
    <span class="footerLinks">
      <button type="button" class="linkButton" @click="aboutOpen = true">About</button>
      <button type="button" class="linkButton" @click="openHelp()">Help</button>
      <a class="hiddenFutureLink" href="#">Donation placeholder</a>
    </span>
  </footer>

  <ModalShell v-if="aboutOpen" title="EDMC MarketScout" title-id="aboutTitle" panel-class="aboutModal" @close="aboutOpen = false">
    <p>This EDMC plug-in is meant to assist players who enjoy doing trading and trading-adjacent activities in the Elite:Dangerous PC game.</p>
    <p>o7 commanders and happy trading!</p>

    <p class="githubLine">
      <svg class="githubIcon" viewBox="0 0 16 16" aria-hidden="true">
        <path
          fill="currentColor"
          d="M8 0C3.58 0 0 3.67 0 8.2c0 3.62 2.29 6.69 5.47 7.77.4.08.55-.18.55-.4 0-.2-.01-.86-.01-1.56-2.01.38-2.53-.5-2.69-.96-.09-.24-.48-.96-.82-1.15-.28-.16-.68-.55-.01-.56.63-.01 1.08.59 1.23.84.72 1.24 1.87.89 2.33.68.07-.53.28-.89.51-1.09-1.78-.21-3.64-.91-3.64-4.03 0-.89.31-1.62.82-2.19-.08-.21-.36-1.04.08-2.16 0 0 .67-.22 2.2.84A7.35 7.35 0 0 1 8 3.96c.68 0 1.36.09 2 .27 1.53-1.06 2.2-.84 2.2-.84.44 1.12.16 1.95.08 2.16.51.57.82 1.3.82 2.19 0 3.13-1.87 3.82-3.65 4.03.29.26.54.75.54 1.51 0 1.09-.01 1.97-.01 2.24 0 .22.15.48.55.4A8.12 8.12 0 0 0 16 8.2C16 3.67 12.42 0 8 0Z"
        />
      </svg>
      <strong>Github:</strong>
      <a href="https://github.com/skys-elite-tools/EDMC-MarketScout" target="_blank" rel="noreferrer">skys-elite-tools/EDMC-MarketScout</a>
    </p>

    <h3>Inspiration and Thanks</h3>
    <p>The projects below are not affiliated with MarketScout in any way, but they were very helpful and inspirational in the creation of MarketScout:</p>
    <ul class="thanksList">
      <li v-for="[label, href] in thanks" :key="href">
        <a :href="href" target="_blank" rel="noreferrer">{{ label }}</a>
      </li>
    </ul>
  </ModalShell>

  <ModalShell v-if="helpOpen" title="Help" title-id="helpTitle" panel-class="aboutModal helpModal" @close="helpOpen = false">
    <article id="help-edmc-running" class="helpArticle">
      <h3>Data Is Recorded While EDMC Is Running</h3>
      <p>MarketScout receives live Journal and market callbacks from EDMC while EDMC and the plugin are running. EDMC does not normally replay your full historical Journal stream to plugins, so MarketScout cannot reconstruct station visits or market snapshots from before it was installed or before EDMC was open.</p>
      <p>For best results, start EDMC before flying, docking, opening station markets, or trading.</p>
    </article>
    <article id="help-best-buy" class="helpArticle">
      <h3>How Best Buy Works</h3>
      <p>Best Buy is not simply the highest profit per tonne. MarketScout combines potential profit with available supply so a commodity with a slightly lower margin but much better stock can rank higher than a commodity with only a few tonnes available.</p>
      <p><code>score = potential_profit_per_tonne * min(supply, Best Buy supply cap)</code></p>
      <p>The Best Buy settings panel lets you change the supply cap, set the minimum potential profit required for a commodity to qualify, and exclude commodities that are not practical for your trading style.</p>
    </article>
    <article id="help-eddn-station" class="helpArticle">
      <h3>EDDN Station Data</h3>
      <p>The EDDN Station status shows whether EDMC is currently configured to send station market data to the Elite Dangerous Data Network. When station data is sent to EDDN, external market tools may pick up the station's commodity prices.</p>
      <p>MarketScout currently shows this as a read-only status indicator. Change the setting in EDMC under Settings, then EDDN.</p>
    </article>
    <article id="help-rare-supply" class="helpArticle">
      <h3>Rare Commodity Supply</h3>
      <p>Rare commodity supply is meaningful only at the commodity's origin station. MarketScout records recent rare supply from origin stations and uses usual supply as a fallback when recent station data is not available.</p>
      <p>For rare station-to-station planning, custom supply values are stored in your browser and can override the usual supply for your own planning.</p>
    </article>
    <article id="help-carrier-calculator" class="helpArticle">
      <h3>Carrier Trade Calculator Formulas</h3>
      <p>The Carrier Trade Calculator estimates carrier prices and profit splits for station-to-station trades, rare commodity carrier sales, and Community Goal-style rare commodity hauling.</p>
      <p>For station-to-station trades, the price difference is divided between carrier profit, loading hauler profit, and unloading hauler profit. For rare commodity carrier sales, the sale price is capped by the maximum carrier sale price of 100x galactic average.</p>
      <p>Carrier net profit subtracts a simple two-jump operating cost: one 500 LY empty jump and one 500 LY laden jump. Tritium is estimated at 70,000 Cr/t, and hull maintenance is estimated at 100,000 Cr per jump.</p>
      <p>Fleet Carrier tritium assumptions are 68t empty and 133t laden. Squadron Carrier assumptions are 43t empty and 195t laden.</p>
    </article>
    <article id="help-spansh-tourist-route" class="helpArticle">
      <h3>Spansh Tourist Routes</h3>
      <p>MarketScout can import a <code>.json</code> file downloaded from the Spansh Tourist Route planner at <a href="https://spansh.co.uk/tourist" target="_blank" rel="noreferrer">spansh.co.uk/tourist</a>.</p>
      <p>You can also create this route on Spansh from a Systems or Stations search by using Spansh's option to create a tourist route from that search, then downloading the route result as JSON.</p>
      <p>Imported route stops are shown above the Stations table. MarketScout also saves the route stop coordinates into its local systems data so distance features can reuse them later.</p>
      <p>The number of jumps to the route start is approximate. It is calculated from straight-line distance divided by the route jump range, so the real plotted route may differ.</p>
    </article>
  </ModalShell>
</template>
