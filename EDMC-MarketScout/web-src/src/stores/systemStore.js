import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useStatusStore } from './statusStore.js'

export const useSystemStore = defineStore('system', () => {
  const helpArticle = ref('')
  const helpRequestId = ref(0)
  const supportOpen = ref(false)
  const updateModal = ref({
    visible: false,
    title: '',
    message: '',
    backupPath: '',
    pluginDir: '',
  })

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

  async function handleUpdateAction() {
    const statusStore = useStatusStore()
    const update = statusStore.updateStatus || {}
    if (!update.can_update) {
      const url = update.html_url || update.download_url
      if (url) window.open(url, '_blank', 'noopener')
      return
    }

    statusStore.updateBusy = true
    try {
      const res = await fetch('/api/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      statusStore.updateStatus = data.update || statusStore.updateStatus
      updateModal.value = {
        visible: true,
        title: data.ok ? 'Update Complete' : 'Update Could Not Be Completed',
        message: data.ok
          ? (data.message || 'Update Complete. Please restart EDMC to start using the latest version of MarketScout.')
          : `${data.message || 'The update could not be completed.'} Copy all files from the backup directory to the plugin directory if you need to restore the previous working version.`,
        backupPath: data.backup_path || '',
        pluginDir: data.plugin_dir || '',
      }
    } catch (err) {
      updateModal.value = {
        visible: true,
        title: 'Update Could Not Be Completed',
        message: `The update could not be completed. ${err?.message || err}`,
        backupPath: '',
        pluginDir: '',
      }
    } finally {
      statusStore.updateBusy = false
    }
  }

  function closeUpdateModal() {
    updateModal.value.visible = false
  }

  return {
    helpArticle,
    helpRequestId,
    supportOpen,
    updateModal,
    openHelp,
    openSupport,
    closeSupport,
    handleUpdateAction,
    closeUpdateModal,
  }
})
