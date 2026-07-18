<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const ECONOMIC_STATES = [
  {
    name: 'Boom',
    description: 'Increases system wealth and trade efficiency; trade missions have double the influence effect.',
  },
  {
    name: 'Investment',
    description: 'A positive state triggered by failed expansions, increasing development and happiness.',
  },
  {
    name: 'Bust',
    description: 'Reduces system wealth and influence; trade missions have reduced or negative effects.',
  },
  {
    name: 'Famine',
    description: 'Decreases standard of living; food trading has double the influence effect, while combat does not.',
  },
  {
    name: 'Outbreak',
    description: 'Decreases standard of living; medicine trading has double the influence effect, while combat does not.',
  },
  {
    name: 'Drought',
    description: 'Causes an economic downturn due to water shortages; countered by importing water.',
  },
  {
    name: 'Blight',
    description: 'Affects crop yields; countered by importing Agronomic Treatment.',
  },
  {
    name: 'Infrastructure Failure',
    description: 'Disrupts operations and reduces security and economic standards; countered by importing food and machinery.',
  },
]

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const menuOpen = ref(false)
const showAll = ref(false)
const highlightedIndex = ref(-1)

const selectedState = computed(() => {
  const value = String(props.modelValue || '').trim().toLowerCase()
  return ECONOMIC_STATES.find(state => state.name.toLowerCase() === value) || null
})

const inputTitle = computed(() => selectedState.value?.description || 'Choose an economic state')

const filteredOptions = computed(() => {
  const filter = String(props.modelValue || '').trim().toLowerCase()
  const options = showAll.value || !filter
    ? ECONOMIC_STATES
    : ECONOMIC_STATES.filter(state => state.name.toLowerCase().includes(filter))
  return options
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
  emit('update:modelValue', option.name)
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
  if (!event.target.closest?.('.economicStateField')) {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <label class="economicStateField">
    Economic State
    <div class="economicStateCombo">
      <input
        ref="inputEl"
        :value="modelValue"
        type="text"
        placeholder="Any state"
        :title="inputTitle"
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
        title="Show all economic states"
        aria-label="Show all economic states"
        @mousedown.prevent
        @click="openFullMenu"
      >▾</button>
      <div v-if="menuOpen" class="economyComboMenu" role="listbox">
        <button
          v-for="(option, index) in filteredOptions"
          :key="option.name"
          type="button"
          class="economyComboOption"
          :class="{ active: index === highlightedIndex }"
          :title="option.description"
          @mousedown.prevent="chooseOption(option)"
        >{{ option.name }}</button>
        <div v-if="!filteredOptions.length" class="economyComboEmpty">No matching states</div>
      </div>
    </div>
  </label>
</template>
