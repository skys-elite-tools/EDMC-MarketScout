import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useViewRefreshStore = defineStore('viewRefresh', () => {
  const refreshSerial = ref(0)
  const refreshOptions = ref({})

  function requestRefresh(options = {}) {
    refreshOptions.value = { ...options }
    refreshSerial.value += 1
  }

  return {
    refreshSerial,
    refreshOptions,
    requestRefresh,
  }
})
