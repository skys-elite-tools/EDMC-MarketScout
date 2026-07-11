<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  presets: { type: Array, default: () => [] },
  saveStatus: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'save'])

const sortedPresets = computed(() => {
  return [...new Set((props.presets || []).map(p => String(p || '').trim()).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
})

function updateValue(value) {
  emit('update:modelValue', value)
}

function selectPreset(event) {
  const value = event.target.value
  if (value) updateValue(value)
  event.target.value = ''
}
</script>

<template>
  <label class="economyPresetField">
    Economy
    <div class="economyPresetControls">
      <input
        :value="modelValue"
        type="text"
        list="marketscout-economy-presets"
        placeholder="Any economy"
        @input="updateValue($event.target.value)"
      />
      <datalist id="marketscout-economy-presets">
        <option v-for="preset in sortedPresets" :key="preset" :value="preset" />
      </datalist>
      <select class="presetSelect" title="Saved economy presets" @change="selectPreset">
        <option value="">Presets…</option>
        <option v-for="preset in sortedPresets" :key="preset" :value="preset">{{ preset }}</option>
      </select>
      <button type="button" title="Save current economy filter as a preset" @click="emit('save')">Save</button>
    </div>
    <span v-if="saveStatus" class="presetStatus">{{ saveStatus }}</span>
  </label>
</template>
