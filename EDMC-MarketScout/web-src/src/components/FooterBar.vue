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
  </ModalShell>
</template>
