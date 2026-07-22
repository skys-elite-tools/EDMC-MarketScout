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
