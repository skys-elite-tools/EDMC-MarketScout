<script setup>
import { ref } from 'vue'

defineProps({
  announcement: { type: String, required: true },
  customAnnouncementTitle: { type: String, required: true },
  customAnnouncement: { type: String, required: true },
  activeCustomTemplateTypeLabel: { type: String, required: true },
})

const emit = defineEmits(['edit-template'])

const copied = ref(false)
const customTitleCopied = ref(false)
const customBodyCopied = ref(false)

async function copyText(value, flag) {
  await navigator.clipboard.writeText(value)
  flag.value = true
  setTimeout(() => { flag.value = false }, 1800)
}
</script>

<template>
  <fieldset class="outputPanel">
    <legend>Announcement</legend>
    <div class="outputPanelHeader">
      <h2>Discord/Reddit text</h2>
      <button type="button" class="copySymbolButton" :title="copied ? 'Copied' : 'Copy announcement'" @click="copyText(announcement, copied)">{{ copied ? '✓' : '⧉' }}</button>
    </div>
    <p class="outputText">{{ announcement }}</p>
  </fieldset>

  <fieldset class="outputPanel">
    <legend>Custom Announcement</legend>
    <div class="outputPanelHeader">
      <h2>For forums, reddit and more</h2>
      <span class="customTemplateTypeBadge">{{ activeCustomTemplateTypeLabel }} template</span>
    </div>
    <div class="customAnnouncementOutput">
      <div class="customOutputSection">
        <div class="customOutputHeader">
          <span>Title</span>
          <button type="button" class="copySymbolButton smallCopyButton" :title="customTitleCopied ? 'Copied' : 'Copy custom title'" @click="copyText(customAnnouncementTitle, customTitleCopied)">{{ customTitleCopied ? '✓' : '⧉' }}</button>
        </div>
        <p class="outputTitle">{{ customAnnouncementTitle }}</p>
      </div>
      <div class="customOutputSection">
        <div class="customOutputHeader">
          <span>Body</span>
          <button type="button" class="copySymbolButton smallCopyButton" :title="customBodyCopied ? 'Copied' : 'Copy custom body'" @click="copyText(customAnnouncement, customBodyCopied)">{{ customBodyCopied ? '✓' : '⧉' }}</button>
        </div>
        <p class="outputText">{{ customAnnouncement }}</p>
      </div>
    </div>
    <button type="button" class="editTemplateButton" @click="emit('edit-template')">Edit template</button>
  </fieldset>
</template>
