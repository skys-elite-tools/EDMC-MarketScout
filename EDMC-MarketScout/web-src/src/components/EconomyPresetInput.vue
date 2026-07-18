<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const ELITE_ECONOMIES = [
  'Agriculture',
  'Colony',
  'Extraction',
  'High Tech',
  'Industrial',
  'Military',
  'Refinery',
  'Service',
  'Terraforming',
  'Tourism',
]

const props = defineProps({
  modelValue: { type: String, default: '' },
  presets: { type: Array, default: () => [] },
  saveStatus: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'save'])

const inputEl = ref(null)
const menuOpen = ref(false)
const showAll = ref(false)
const highlightedIndex = ref(-1)

const allOptions = computed(() => {
  return [...new Set([
    ...ELITE_ECONOMIES,
    ...(props.presets || []).map(p => String(p || '').trim()).filter(Boolean),
  ])].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
})

const filteredOptions = computed(() => {
  const filter = String(props.modelValue || '').trim().toLowerCase()
  const options = showAll.value || !filter
    ? allOptions.value
    : allOptions.value.filter(option => option.toLowerCase().includes(filter))
  return options.slice(0, 250)
})

function updateValue(value) {
  showAll.value = false
  highlightedIndex.value = -1
  emit('update:modelValue', value)
}

function openFilteredMenu() {
  if (showAll.value) {
    menuOpen.value = true
    return
  }
  showAll.value = false
  menuOpen.value = true
}

async function openFullMenu() {
  showAll.value = true
  menuOpen.value = true
  highlightedIndex.value = -1
  await nextTick()
  inputEl.value?.focus()
}

function closeMenuSoon() {
  window.setTimeout(() => {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }, 120)
}

function chooseOption(option) {
  emit('update:modelValue', option)
  menuOpen.value = false
  showAll.value = false
  highlightedIndex.value = -1
  inputEl.value?.focus()
}

function onKeydown(event) {
  if (!menuOpen.value && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
    menuOpen.value = true
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    const count = filteredOptions.value.length
    if (count) highlightedIndex.value = (highlightedIndex.value + 1) % count
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    const count = filteredOptions.value.length
    if (count) highlightedIndex.value = highlightedIndex.value <= 0 ? count - 1 : highlightedIndex.value - 1
  } else if (event.key === 'Enter' && highlightedIndex.value >= 0) {
    event.preventDefault()
    chooseOption(filteredOptions.value[highlightedIndex.value])
  } else if (event.key === 'Escape') {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }
}

function onDocumentPointerDown(event) {
  if (!event.target.closest?.('.economyPresetField')) {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <label class="economyPresetField">
    Economy
    <div class="economyPresetControls">
      <div
        class="economyCombo"
        title="You can type multiple economies separated by commas"
      >
        <input
          ref="inputEl"
          :value="modelValue"
          type="text"
          placeholder="Any economy"
          title="You can type multiple economies separated by commas"
          autocomplete="off"
          @input="updateValue($event.target.value)"
          @keyup="openFilteredMenu"
          @focus="openFilteredMenu"
          @keydown="onKeydown"
          @blur="closeMenuSoon"
        />
        <button
          type="button"
          class="economyComboToggle"
          title="Show all economy presets"
          aria-label="Show all economy presets"
          @mousedown.prevent
          @click="openFullMenu"
        >▾</button>
        <div v-if="menuOpen" class="economyComboMenu" role="listbox">
          <button
            v-for="(option, index) in filteredOptions"
            :key="option"
            type="button"
            class="economyComboOption"
            :class="{ active: index === highlightedIndex }"
            @mousedown.prevent="chooseOption(option)"
          >{{ option }}</button>
          <div v-if="!filteredOptions.length" class="economyComboEmpty">No matching economies</div>
        </div>
      </div>
      <button type="button" title="Save current economy filter as a preset" @click="emit('save')">Save Preset</button>
    </div>
    <span v-if="saveStatus" class="presetStatus">{{ saveStatus }}</span>
  </label>
</template>
