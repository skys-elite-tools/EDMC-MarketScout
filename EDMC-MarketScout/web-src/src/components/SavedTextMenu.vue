<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Saved text' },
  noneLabel: { type: String, default: 'No selection' },
  placeholder: { type: String, default: 'New saved text' },
  saveLabel: { type: String, default: 'Save new' },
  status: { type: String, default: '' },
  buttonTitle: { type: String, default: 'Select saved text' },
})

const emit = defineEmits(['update:modelValue', 'save-new', 'delete'])

const rootEl = ref(null)
const menuOpen = ref(false)
const draftText = ref('')

const currentLabel = computed(() => {
  if (!props.modelValue) return props.noneLabel
  return props.items.find(item => item.id === props.modelValue)?.label || props.noneLabel
})

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function selectItem(id) {
  emit('update:modelValue', id)
  menuOpen.value = false
}

function saveNew() {
  const text = draftText.value.trim()
  if (!text) return
  emit('save-new', text)
  draftText.value = ''
}

function onDocumentPointerDown(event) {
  if (!rootEl.value?.contains(event.target)) {
    menuOpen.value = false
  }
}

document.addEventListener('pointerdown', onDocumentPointerDown)
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocumentPointerDown))
</script>

<template>
  <div ref="rootEl" class="savedTextMenuField">
    <span v-if="label" class="savedTextMenuLabel">{{ label }}</span>
    <div class="savedTextMenu">
      <button type="button" class="savedTextMenuButton" :title="buttonTitle" @click="toggleMenu">{{ currentLabel }} ▾</button>
      <div v-if="menuOpen" class="savedTextMenuList">
        <button type="button" class="savedTextMenuOption" :class="{ active: !modelValue }" @click="selectItem('')">{{ noneLabel }}</button>
        <div class="savedTextMenuDivider"></div>
        <div class="savedTextSaveRow">
          <label>New
            <input v-model="draftText" type="text" :placeholder="placeholder" @keydown.enter.prevent="saveNew" />
          </label>
          <button type="button" class="savedTextSaveButton" @click="saveNew">{{ saveLabel }}</button>
          <span class="small savedTextStatus">{{ status }}</span>
        </div>
        <div v-if="items.length" class="savedTextMenuDivider"></div>
        <div v-for="item in items" :key="item.id" class="savedTextMenuRow" :class="{ active: modelValue === item.id }">
          <button type="button" class="savedTextMenuOption custom" :title="item.value" @click="selectItem(item.id)">{{ item.label }}</button>
          <button type="button" class="savedTextDeleteButton" title="Delete" @click.stop="emit('delete', item.id)">🗑</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.savedTextMenuField {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 10rem;
  color: var(--muted);
  font-size: 12px;
}

.savedTextMenuLabel {
  font-size: 11px;
}

.savedTextMenu {
  position: relative;
}

.savedTextMenuButton {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.savedTextMenuList {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: auto;
  right: 0;
  width: min(24rem, calc(100vw - 3rem));
  max-height: 18rem;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #0b1016;
  box-shadow: 0 12px 30px rgba(0,0,0,.35);
  padding: 4px;
}

.savedTextMenuOption {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  border-radius: 4px;
  padding: 6px 8px;
}

.savedTextMenuOption:hover,
.savedTextMenuOption.active,
.savedTextMenuRow.active .savedTextMenuOption {
  background: #263142;
  color: white;
}

.savedTextMenuDivider {
  height: 1px;
  margin: 4px 2px;
  background: var(--line);
}

.savedTextSaveRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: end;
  padding: 6px 4px 2px;
}

.savedTextSaveRow label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
}

.savedTextSaveRow input {
  width: 100%;
  height: 2rem;
}

.savedTextSaveButton {
  white-space: nowrap;
  height: 2rem;
  padding-top: 0;
  padding-bottom: 0;
}

.savedTextStatus {
  grid-column: 1 / -1;
  min-height: 0;
}

.savedTextMenuRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2rem;
  gap: 3px;
}

.savedTextMenuOption.custom {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.savedTextDeleteButton {
  min-width: 2rem;
  padding: 0;
  text-align: center;
  border: 0;
  background: transparent;
}

.savedTextDeleteButton:hover {
  background: rgba(255, 100, 100, .12);
  border-color: rgba(255, 100, 100, .45);
}
</style>
