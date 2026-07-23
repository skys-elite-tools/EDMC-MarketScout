<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  value: { type: String, required: true },
  legend: { type: String, default: '' },
  copyTitle: { type: String, default: 'Copy text' },
  textClass: { type: String, default: 'outputText' },
  variant: {
    type: String,
    default: 'panel',
    validator: value => ['panel', 'section'].includes(value),
  },
})

const copied = ref(false)

async function copyValue() {
  await navigator.clipboard.writeText(props.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1800)
}
</script>

<template>
  <fieldset v-if="variant === 'panel'" class="outputPanel">
    <legend v-if="legend">{{ legend }}</legend>
    <div class="outputPanelHeader">
      <h2>{{ title }}</h2>
      <slot name="header-extra"></slot>
      <button type="button" class="copySymbolButton" :title="copied ? 'Copied' : copyTitle" @click="copyValue">{{ copied ? '✓' : '⧉' }}</button>
    </div>
    <p :class="textClass">{{ value }}</p>
    <slot></slot>
  </fieldset>

  <div v-else class="customOutputSection">
    <div class="customOutputHeader">
      <span>{{ title }}</span>
      <button type="button" class="copySymbolButton smallCopyButton" :title="copied ? 'Copied' : copyTitle" @click="copyValue">{{ copied ? '✓' : '⧉' }}</button>
    </div>
    <p :class="textClass">{{ value }}</p>
    <slot></slot>
  </div>
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

.outputText,
.outputTitle {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.outputText {
  color: var(--text);
  line-height: 1.45;
}

.outputTitle {
  color: white;
  font-weight: 900;
}

.customOutputSection {
  display: grid;
  gap: 4px;
}

.customOutputSection + .customOutputSection {
  padding-top: 10px;
  border-top: 1px solid rgba(159,240,212,.16);
}

.customOutputHeader {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.copySymbolButton {
  min-width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  font-size: 18px;
  font-weight: 900;
}

.smallCopyButton {
  min-width: 1.75rem;
  height: 1.75rem;
  font-size: 14px;
}
</style>
