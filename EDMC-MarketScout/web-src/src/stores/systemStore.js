import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSystemStore = defineStore('system', () => {
  const helpArticle = ref('')
  const helpRequestId = ref(0)
  const supportOpen = ref(false)

  function openHelp(article = '') {
    helpArticle.value = article
    helpRequestId.value += 1
  }

  function openSupport() {
    supportOpen.value = true
  }

  function closeSupport() {
    supportOpen.value = false
  }

  return {
    helpArticle,
    helpRequestId,
    supportOpen,
    openHelp,
    openSupport,
    closeSupport,
  }
})
