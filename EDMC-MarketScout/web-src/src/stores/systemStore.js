import {defineStore} from 'pinia'
import {ref} from 'vue'

export const useSystemStore = defineStore('system', () => {

// --- STATE ---

// Global UI Modals
const supportOpen = ref(false)

// --- ACTIONS ---

    async function handleUpdateAction() {
        const update = updateStatus.value || {}
        if (!update.can_update) {
            const url = update.html_url || update.download_url
            if (url) window.open(url, '_blank', 'noopener')
            return
        }

        updateBusy.value = true
        try {
            const res = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
            })
            const data = await res.json()
            updateStatus.value = data.update || updateStatus.value
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
            updateBusy.value = false
        }
    }

    function openSupport() { supportOpen.value = true }
    function closeSupport() { supportOpen.value = false }

    return {
        handleUpdateAction,
        supportOpen,
        openSupport,
        closeSupport
    }
})