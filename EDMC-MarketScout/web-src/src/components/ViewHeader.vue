<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '../stores/systemStore.js'
import InfoButton from './InfoButton.vue'

const route = useRoute()
const systemStore = useSystemStore()
const title = computed(() => route.meta?.title || 'MarketScout')
const description = computed(() => route.meta?.description || '')
const helpArticle = computed(() => route.meta?.helpArticle || '')
</script>

<template>
  <div class="viewControlsHeader">
    <div class="controlGroupTitle">
      <span>{{ title }}</span>
      <InfoButton v-if="helpArticle" :title="`About ${title}`" @open="systemStore.openHelp(helpArticle)" />
    </div>
    <p v-if="$route.name === 'stations'" class="viewControlsDescription">
      Lists scouting data for stations visited
      <button type="button" class="inlineHelpLink" @click="systemStore.openHelp('edmc-running')">while EDMC was running</button>.
    </p>
    <p v-else-if="description" class="viewControlsDescription">{{ description }}</p>
  </div>
</template>
