<script setup>
import CopyablePanel from './CopyablePanel.vue'

defineProps({
  announcement: { type: String, required: true },
  customAnnouncementTitle: { type: String, required: true },
  customAnnouncement: { type: String, required: true },
  activeCustomTemplateTypeLabel: { type: String, required: true },
})

const emit = defineEmits(['edit-template'])
</script>

<template>
  <CopyablePanel
    title="Discord/Reddit text"
    legend="Announcement"
    :value="announcement"
    copy-title="Copy announcement"
  />

  <fieldset class="outputPanel">
    <legend>Custom Announcement</legend>
    <div class="outputPanelHeader">
      <h2>For forums, reddit and more</h2>
      <span class="customTemplateTypeBadge">{{ activeCustomTemplateTypeLabel }} template</span>
    </div>
    <div class="customAnnouncementOutput">
      <CopyablePanel
        title="Title"
        :value="customAnnouncementTitle"
        copy-title="Copy custom title"
        text-class="outputTitle"
        variant="section"
      />
      <CopyablePanel
        title="Body"
        :value="customAnnouncement"
        copy-title="Copy custom body"
        variant="section"
      />
    </div>
    <button type="button" class="editTemplateButton" @click="emit('edit-template')">Edit template</button>
  </fieldset>
</template>
