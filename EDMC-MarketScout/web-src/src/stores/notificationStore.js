import { defineStore } from 'pinia'
import { ref } from 'vue'

const TARGET_STATE_TOAST_TIMEOUT_MS = 60000

export const useNotificationStore = defineStore('notification', () => {
  const targetStateToast = ref(null)
  const targetStateDetailsOpen = ref(false)
  const targetStateToastCountdownKey = ref(0)
  const dismissedTargetStateAlertKey = ref('')
  let targetStateToastTimer = null

  function clearTargetStateToastTimer() {
    if (!targetStateToastTimer) return
    clearTimeout(targetStateToastTimer)
    targetStateToastTimer = null
  }

  function dismissTargetStateToast() {
    if (targetStateToast.value?.key) dismissedTargetStateAlertKey.value = targetStateToast.value.key
    targetStateToast.value = null
    targetStateDetailsOpen.value = false
    clearTargetStateToastTimer()
  }

  function expireTargetStateToast() {
    if (targetStateToast.value?.key) dismissedTargetStateAlertKey.value = targetStateToast.value.key
    targetStateToast.value = null
    targetStateDetailsOpen.value = false
    targetStateToastTimer = null
  }

  function resetTargetStateToastTimer() {
    if (!targetStateToast.value?.key) return
    clearTargetStateToastTimer()
    targetStateToastCountdownKey.value += 1
    targetStateToastTimer = setTimeout(expireTargetStateToast, TARGET_STATE_TOAST_TIMEOUT_MS)
  }

  function openTargetStateDetails() {
    targetStateDetailsOpen.value = true
    resetTargetStateToastTimer()
  }

  function updateTargetStateToast(alert) {
    if (!alert?.key) {
      targetStateToast.value = null
      targetStateDetailsOpen.value = false
      clearTargetStateToastTimer()
      return
    }
    if (targetStateToast.value?.key === alert.key || dismissedTargetStateAlertKey.value === alert.key) return
    targetStateToast.value = alert
    targetStateDetailsOpen.value = false
    resetTargetStateToastTimer()
  }

  function disposeNotifications() {
    clearTargetStateToastTimer()
  }

  return {
    targetStateToast,
    targetStateDetailsOpen,
    targetStateToastCountdownKey,
    dismissTargetStateToast,
    resetTargetStateToastTimer,
    openTargetStateDetails,
    updateTargetStateToast,
    disposeNotifications,
  }
})
