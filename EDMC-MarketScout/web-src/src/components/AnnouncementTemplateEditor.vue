<script setup>
import { computed } from 'vue'
import ModalShell from './ModalShell.vue'

const props = defineProps({
  titleTemplate: { type: String, required: true },
  bodyTemplate: { type: String, required: true },
  activeCustomTemplateTypeLabel: { type: String, required: true },
  customTokenList: { type: Array, required: true },
})

const emit = defineEmits(['close', 'update:titleTemplate', 'update:bodyTemplate'])

const editableTitle = computed({
  get: () => props.titleTemplate,
  set: value => emit('update:titleTemplate', value),
})

const editableBody = computed({
  get: () => props.bodyTemplate,
  set: value => emit('update:bodyTemplate', value),
})
</script>

<template>
  <ModalShell
    title="Custom Announcement Template"
    title-id="customTemplateTitle"
    panel-class="templateModal"
    @close="emit('close')"
  >
    <template #header-extra>
      <span class="customTemplateTypeBadge">{{ activeCustomTemplateTypeLabel }} template</span>
    </template>

    <div class="templateEditorGrid">
      <div>
        <h3>Tokens</h3>
        <div class="tokenList">
          <code v-for="[token, help] in customTokenList" :key="token" :title="help">[{{ token }}]</code>
        </div>
      </div>
      <div class="templateFields">
        <label>Announcement Title
          <input v-model="editableTitle" type="text" spellcheck="false" />
        </label>
        <label class="templateTextArea">Announcement Body
          <textarea v-model="editableBody" rows="14" spellcheck="false"></textarea>
        </label>
      </div>
    </div>

    <template #actions>
      <button type="button" @click="emit('close')">Done</button>
    </template>
  </ModalShell>
</template>

<style scoped>
:deep(.templateModal) {
  width: min(56rem, 100%);
  max-height: min(84vh, 52rem);
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  background: #111820;
  box-shadow: 0 24px 80px rgba(0,0,0,.55);
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

.templateEditorGrid {
  display: grid;
  grid-template-columns: minmax(13rem, .75fr) minmax(20rem, 1fr);
  gap: 16px;
  align-items: start;
}

.templateEditorGrid h3 {
  margin: 0 0 8px;
  color: var(--accent2);
}

.tokenList {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tokenList code {
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #0b1016;
  color: var(--accent);
  font: 12px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.templateFields {
  display: grid;
  gap: 10px;
}

.templateFields label,
.templateTextArea {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--muted);
  font-size: 12px;
}

.templateFields input {
  width: 100%;
}

.templateTextArea textarea {
  width: 100%;
  min-height: 18rem;
  resize: vertical;
  background: #0e1217;
  color: var(--text);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 8px 10px;
  font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

@media (max-width: 1100px) {
  .templateEditorGrid {
    grid-template-columns: 1fr;
  }
}
</style>
