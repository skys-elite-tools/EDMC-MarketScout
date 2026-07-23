<script setup>
import CopyablePanel from './CopyablePanel.vue'
import SavedTextMenu from './SavedTextMenu.vue'

defineProps({
  announcement: { type: String, required: true },
  customAnnouncementTitle: { type: String, required: true },
  customAnnouncement: { type: String, required: true },
  activeCustomTemplateTypeLabel: { type: String, required: true },
  includeShortStationType: { type: Boolean, default: false },
  shortPrefixEnabled: { type: Boolean, default: false },
  shortPrefixId: { type: String, default: '' },
  shortPrefixes: { type: Array, default: () => [] },
  shortPrefixStatus: { type: String, default: '' },
})

const emit = defineEmits([
  'edit-template',
  'update:include-short-station-type',
  'update:short-prefix-enabled',
  'update:short-prefix-id',
  'save-short-prefix',
  'delete-short-prefix',
])
</script>

<template>
  <CopyablePanel
    title="Discord/Reddit text"
    legend="Announcement"
    :value="announcement"
    copy-title="Copy announcement"
  >
    <template #header-extra>
      <div class="shortAnnouncementControls">
        <label class="shortAnnouncementToggle">
          <input
            :checked="shortPrefixEnabled"
            type="checkbox"
            @change="emit('update:short-prefix-enabled', $event.target.checked)"
          />
          Prefix
        </label>
        <SavedTextMenu
          class="shortPrefixMenu"
          :model-value="shortPrefixId"
          :items="shortPrefixes"
          label=""
          none-label="No prefix"
          placeholder="(Community Goal)"
          save-label="Save new"
          :status="shortPrefixStatus"
          button-title="Select announcement prefix"
          @update:model-value="emit('update:short-prefix-id', $event)"
          @save-new="emit('save-short-prefix', $event)"
          @delete="emit('delete-short-prefix', $event)"
        />
        <label class="shortAnnouncementToggle">
          <input
            :checked="includeShortStationType"
            type="checkbox"
            @change="emit('update:include-short-station-type', $event.target.checked)"
          />
          Station type
        </label>
      </div>
    </template>
  </CopyablePanel>

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

<style scoped>
.outputPanel {
  max-width: var(--carrier-preview-width);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  margin: 0;
  background: rgba(140,200,255,.035);
}

.outputPanel legend {
  color: #9ff0d4;
  font-weight: 900;
  padding: 0 4px;
}

.outputPanelHeader {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}

.outputPanelHeader h2 {
  margin: 0;
  color: #9ff0d4;
  font-size: 13px;
}

.customTemplateTypeBadge {
  display: inline-flex;
  align-items: center;
  min-height: 1.55rem;
  border: 1px solid rgba(245,194,75,.55);
  border-radius: 999px;
  background: rgba(245,194,75,.14);
  color: #ffe1a0;
  font-size: 11px;
  font-weight: 900;
  line-height: 1;
  padding: 0 9px;
  text-transform: uppercase;
  white-space: nowrap;
}

.shortAnnouncementControls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  min-width: 0;
}

.shortAnnouncementToggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.shortAnnouncementToggle input {
  width: auto;
}

.shortPrefixMenu {
  min-width: 11rem;
  max-width: 14rem;
}

.customAnnouncementOutput {
  display: grid;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid rgba(159,240,212,.22);
  border-radius: 4px;
  background: #0e1217;
}

.editTemplateButton {
  margin-top: 8px;
}
</style>
