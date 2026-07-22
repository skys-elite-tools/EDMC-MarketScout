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
