<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const STATE_GROUPS = [
  {
    label: 'Economy States',
    options: ['Famine', 'Bust', 'None', 'Boom', 'Investment'],
  },
  {
    label: 'Security States',
    options: ['Lockdown', 'Civil Unrest', 'None', 'Civil Liberty'],
  },
  {
    label: 'Other States',
    options: [
      'Incursion',
      'Infested',
      'Blight',
      'Drought',
      'Outbreak',
      'Infrastructure Failure',
      'Natural Disaster',
      'Revolution',
      'Cold War',
      'Trade War',
      'Pirate Attack',
      'Terrorist Attack',
      'Public Holiday',
      'Technological Leap',
      'Historic Event',
      'Colonisation',
      'War',
      'Civil War',
      'Elections',
      'Retreat',
      'Expansion',
    ],
  },
]

const STATION_OWNER_STATES = STATE_GROUPS.flatMap(group =>
  group.options.map(name => ({
    name,
    group: group.label,
    description: `${name} (${group.label})`,
  })),
)

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Station Owner State' },
  placeholder: { type: String, default: 'Any owner state' },
  buttonTitle: { type: String, default: 'Show all station owner states' },
  emptyText: { type: String, default: 'No matching states' },
})
const emit = defineEmits(['update:modelValue'])

const inputEl = ref(null)
const menuOpen = ref(false)
const showAll = ref(false)
const highlightedIndex = ref(-1)

const selectedState = computed(() => {
  const value = String(props.modelValue || '').trim().toLowerCase()
  return STATION_OWNER_STATES.find(state => state.name.toLowerCase() === value) || null
})

const inputTitle = computed(() => selectedState.value?.description || `Choose ${props.label.toLowerCase()}`)

const filteredOptions = computed(() => {
  const filter = String(props.modelValue || '').trim().toLowerCase()
  const options = showAll.value || !filter
    ? STATION_OWNER_STATES
    : STATION_OWNER_STATES.filter(state => state.name.toLowerCase().includes(filter))
  return options
})

const filteredGroups = computed(() => {
  const optionIndexes = new Map()
  filteredOptions.value.forEach((option, index) => {
    optionIndexes.set(`${option.group}:${option.name}`, index)
  })
  return STATE_GROUPS
    .map(group => ({
      label: group.label,
      options: group.options
        .map(name => {
          const index = optionIndexes.get(`${group.label}:${name}`)
          return index === undefined ? null : { ...filteredOptions.value[index], index }
        })
        .filter(Boolean),
    }))
    .filter(group => group.options.length)
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
  if (!event.target.closest?.('.stationOwnerStateField')) {
    menuOpen.value = false
    showAll.value = false
    highlightedIndex.value = -1
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <label class="stationOwnerStateField">
    {{ label }}
    <div class="stationOwnerStateCombo">
      <input
        ref="inputEl"
        :value="modelValue"
        type="text"
        :placeholder="placeholder"
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
        :title="buttonTitle"
        :aria-label="buttonTitle"
        @mousedown.prevent
        @click="openFullMenu"
      >▾</button>
      <div v-if="menuOpen" class="economyComboMenu" role="listbox">
        <div v-for="group in filteredGroups" :key="group.label" class="stationOwnerStateGroup">
          <div class="economyComboGroupLabel">{{ group.label }}</div>
          <button
            v-for="option in group.options"
            :key="`${group.label}-${option.name}`"
            type="button"
            class="economyComboOption"
            :class="{ active: option.index === highlightedIndex }"
            :title="option.description"
            @mousedown.prevent="chooseOption(option)"
          >{{ option.name }}</button>
        </div>
        <div v-if="!filteredOptions.length" class="economyComboEmpty">{{ emptyText }}</div>
      </div>
    </div>
  </label>
</template>
