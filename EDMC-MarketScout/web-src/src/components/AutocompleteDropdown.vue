<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  optionLabel: { type: Function, default: option => String(option || '') },
  placeholder: { type: String, default: '' },
  emptyText: { type: String, default: 'No matching options' },
  buttonTitle: { type: String, default: 'Show options' },
  maxOptions: { type: Number, default: 500 },
})

const emit = defineEmits(['update:modelValue', 'select', 'clear'])

const rootEl = ref(null)
const inputEl = ref(null)
const menuOpen = ref(false)
const showAll = ref(false)
const highlightedIndex = ref(-1)

const filteredOptions = computed(() => {
  const filter = String(props.modelValue || '').trim().toLowerCase()
  const rows = props.options || []
  if (showAll.value || !filter) return rows.slice(0, props.maxOptions)
  return rows.filter(option => props.optionLabel(option).toLowerCase().includes(filter)).slice(0, props.maxOptions)
})

function updateValue(value) {
  showAll.value = false
  highlightedIndex.value = -1
  emit('update:modelValue', value)
  if (!String(value || '').trim()) emit('clear')
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
  emit('update:modelValue', props.optionLabel(option))
  emit('select', option)
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
  if (!rootEl.value?.contains(event.target)) {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <div ref="rootEl" class="autocompleteDropdown">
    <input
      ref="inputEl"
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
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
      :title="buttonTitle"
      :aria-label="buttonTitle"
      @mousedown.prevent
      @click="openFullMenu"
    >▾</button>
    <div v-if="menuOpen" class="economyComboMenu autocompleteDropdownMenu" role="listbox">
      <button
        v-for="(option, index) in filteredOptions"
        :key="option?.market_id ?? option?.commodity ?? optionLabel(option)"
        type="button"
        class="economyComboOption autocompleteDropdownOption"
        :class="{ active: index === highlightedIndex }"
        @mousedown.prevent="chooseOption(option)"
      >
        <slot name="option" :option="option">
          {{ optionLabel(option) }}
        </slot>
      </button>
      <div v-if="!filteredOptions.length" class="economyComboEmpty">{{ emptyText }}</div>
    </div>
  </div>
</template>

<style scoped>
.autocompleteDropdown {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2rem;
  min-width: 0;
}

.autocompleteDropdown input {
  min-width: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.autocompleteDropdownMenu {
  min-width: min(28rem, calc(100vw - 3rem));
}

.autocompleteDropdownOption {
  display: grid;
  gap: 2px;
}

.autocompleteDropdownOption small {
  color: var(--muted);
  font-size: 11px;
}

.autocompleteDropdownOption:hover small,
.autocompleteDropdownOption.active small {
  color: #cfd8e3;
}
</style>
