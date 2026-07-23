<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import Coloris from '@melloware/coloris'
import '@melloware/coloris/dist/coloris.css'

const props = defineProps({
  form: { type: Object, required: true },
  textColor: { type: String, required: true },
  textLayout: { type: String, required: true },
  currentLayoutLabel: { type: String, required: true },
  layoutMenuOpen: { type: Boolean, required: true },
  layoutName: { type: String, required: true },
  layoutSaveStatus: { type: String, default: '' },
  savedLayouts: { type: Array, required: true },
  textColorPresets: { type: Array, required: true },
  fontSizeFor: { type: Function, required: true },
  setFontSize: { type: Function, required: true },
})

const emit = defineEmits([
  'file-change',
  'set-text-color',
  'update:textColor',
  'update:layoutMenuOpen',
  'update:layoutName',
  'select-text-layout',
  'save-current-layout',
  'delete-saved-layout',
])

const layoutMenuRef = ref(null)

function closeMenusOnOutsideClick(event) {
  if (props.layoutMenuOpen && !layoutMenuRef.value?.contains(event.target)) {
    emit('update:layoutMenuOpen', false)
  }
}

function updateTextColor(value) {
  emit('update:textColor', value)
  emit('set-text-color', value)
}

onMounted(() => {
  document.addEventListener('pointerdown', closeMenusOnOutsideClick)
  Coloris.init()
  Coloris({
    el: '.marketScoutTextColorInput',
    theme: 'polaroid',
    themeMode: 'dark',
    format: 'hex',
    formatToggle: false,
    alpha: false,
    closeButton: true,
    closeLabel: 'Done',
    swatches: props.textColorPresets,
    onChange: color => emit('set-text-color', color),
  })
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', closeMenusOnOutsideClick)
})
</script>

<template>
  <section class="carrierSection carrierFormPane">
    <h2>Image Options</h2>
    <div class="carrierImageTools">
      <label>Upload image <input type="file" accept="image/*" @change="emit('file-change', $event)" /></label>
      <div class="textLayoutMenuField">
        <span>Text Layout</span>
        <div ref="layoutMenuRef" class="textLayoutMenu">
          <button type="button" class="textLayoutMenuButton" @click="emit('update:layoutMenuOpen', !layoutMenuOpen)">{{ currentLayoutLabel }} ▾</button>
          <div v-if="layoutMenuOpen" class="textLayoutMenuList">
            <button type="button" class="textLayoutMenuOption" :class="{ active: textLayout === 'classic' }" @click="emit('select-text-layout', 'classic')">Classic</button>
            <button type="button" class="textLayoutMenuOption" :class="{ active: textLayout === 'floating' }" @click="emit('select-text-layout', 'floating')">Free Floating</button>
            <div class="textLayoutMenuDivider"></div>
            <div class="layoutSaveRow">
              <label>Layout name <input :value="layoutName" type="text" placeholder="My carrier layout" @input="emit('update:layoutName', $event.target.value)" @keydown.enter.prevent="emit('save-current-layout')" /></label>
              <button type="button" class="saveLayoutButton" @click="emit('save-current-layout')">Save new</button>
              <span class="small layoutSaveStatus">{{ layoutSaveStatus }}</span>
            </div>
            <div v-if="savedLayouts.length" class="textLayoutMenuDivider"></div>
            <div v-for="layout in savedLayouts" :key="layout.id" class="textLayoutMenuRow" :class="{ active: textLayout === `custom:${layout.id}` }">
              <button type="button" class="textLayoutMenuOption custom" @click="emit('select-text-layout', `custom:${layout.id}`)">{{ layout.name }}</button>
              <button type="button" class="textLayoutDeleteButton" title="Delete layout" @click.stop="emit('delete-saved-layout', layout.id)">🗑</button>
            </div>
          </div>
        </div>
      </div>
      <label class="textColorControl">Text Color
        <input
          :value="textColor"
          class="marketScoutTextColorInput"
          type="text"
          data-coloris
          spellcheck="false"
          @input="emit('update:textColor', $event.target.value)"
          @change="updateTextColor($event.target.value)"
          @blur="emit('set-text-color', $event.target.value)"
        />
      </label>
    </div>
    <h2>Trade</h2>
    <div class="carrierFormGrid">
      <fieldset class="tradeFieldset">
        <legend>Trade</legend>
        <div class="fieldWithFont">
          <label>Commodity <input v-model="form.commodity" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('commodity')" type="number" min="8" max="180" step="1" @input="setFontSize('commodity', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont profitFieldWithOptions">
          <label>Profit <input v-model="form.profit" type="text" /></label>
          <label class="inlineCheckboxLabel"><input v-model="form.includeProfitLabelInImage" type="checkbox" /> Profit label</label>
          <label>Font size <input :value="fontSizeFor('profitValue')" type="number" min="8" max="180" step="1" @input="setFontSize('profitValue', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont">
          <label>Quantity (tons) <input v-model="form.quantity" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('quantity')" type="number" min="8" max="180" step="1" @input="setFontSize('quantity', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont">
          <label>Type
            <select v-model="form.type">
              <option>Loading</option>
              <option>Unloading</option>
            </select>
          </label>
          <label>Font size <input :value="fontSizeFor('type')" type="number" min="8" max="180" step="1" @input="setFontSize('type', $event.target.value)" /></label>
        </div>
      </fieldset>
      <fieldset class="carrierFieldset">
        <legend>Carrier</legend>
        <div class="fieldWithFont">
          <label>Carrier Name <input v-model="form.carrierName" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('carrierName')" type="number" min="8" max="180" step="1" @input="setFontSize('carrierName', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont">
          <label>Carrier ID <input v-model="form.carrierId" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('carrierId')" type="number" min="8" max="180" step="1" @input="setFontSize('carrierId', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont singleFieldRow">
          <label>Carrier System <input v-model="form.carrierSystem" type="text" /></label>
        </div>
      </fieldset>
      <fieldset class="marketFieldset">
        <legend>Market</legend>
        <div class="fieldWithFont">
          <label>Station <input v-model="form.station" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('station')" type="number" min="8" max="180" step="1" @input="setFontSize('station', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont">
          <label>System <input v-model="form.system" type="text" /></label>
          <label>Font size <input :value="fontSizeFor('system')" type="number" min="8" max="180" step="1" @input="setFontSize('system', $event.target.value)" /></label>
        </div>
        <div class="fieldWithFont singleFieldRow">
          <label>Station Type
            <select v-model="form.stationType">
              <option>Dodec Starport</option>
              <option>Orbis Starport</option>
              <option>Asteroid Base</option>
              <option>Outpost</option>
              <option>Planetary</option>
            </select>
          </label>
        </div>
        <div class="fieldWithFont">
          <label>Pads
            <select v-model="form.pads">
              <option>Small</option>
              <option>Medium</option>
              <option>Large</option>
            </select>
          </label>
          <label>Font size <input :value="fontSizeFor('pads')" type="number" min="8" max="180" step="1" @input="setFontSize('pads', $event.target.value)" /></label>
        </div>
      </fieldset>
    </div>
  </section>
</template>

<style scoped>
.carrierFormPane {
  align-self: start;
  display: grid;
  gap: 10px;
  min-width: 0;
}

.carrierSection h2 {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 15px;
}

.carrierImageTools {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(10rem, .7fr) minmax(6.5rem, auto);
  gap: 12px;
  align-items: end;
}

.carrierImageTools label,
.carrierFormGrid label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.textLayoutMenuField {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
  min-width: 0;
}

.textLayoutMenu {
  position: relative;
}

.textLayoutMenuButton {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.textLayoutMenuList {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 18rem;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #0b1016;
  box-shadow: 0 12px 30px rgba(0,0,0,.35);
  padding: 4px;
}

.textLayoutMenuOption {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  border-radius: 4px;
  padding: 6px 8px;
}

.textLayoutMenuOption:hover,
.textLayoutMenuOption.active,
.textLayoutMenuRow.active .textLayoutMenuOption {
  background: #263142;
  color: white;
}

.textLayoutMenuDivider {
  height: 1px;
  margin: 4px 2px;
  background: var(--line);
}

.textLayoutMenuRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2rem;
  gap: 3px;
}

.textLayoutMenuOption.custom {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.textLayoutDeleteButton {
  min-width: 2rem;
  padding: 0;
  text-align: center;
  border: 0;
  background: transparent;
}

.textLayoutDeleteButton:hover {
  background: rgba(255, 100, 100, .12);
  border-color: rgba(255, 100, 100, .45);
}

.layoutSaveRow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: end;
  padding: 6px 4px 2px;
}

.layoutSaveRow label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 0;
}

.layoutSaveRow input {
  width: 100%;
  height: 2rem;
}

.saveLayoutButton {
  white-space: nowrap;
  height: 2rem;
  padding-top: 0;
  padding-bottom: 0;
}

.layoutSaveStatus {
  grid-column: 1 / -1;
  min-height: 0;
}

.textColorControl {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
  justify-self: end;
  min-width: 9rem;
  width: 100%;
}

.textColorControl :deep(.clr-field) {
  width: 100%;
}

.textColorControl :deep(.clr-field input) {
  width: 100%;
  padding-right: 2.4rem;
}

.carrierFormGrid {
  display: grid;
  grid-template-columns: minmax(15rem, .92fr) minmax(16rem, 1fr);
  gap: 12px;
  align-items: start;
}

.carrierFormGrid fieldset {
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 10px;
  margin: 0;
  background: rgba(255,255,255,.025);
}

.carrierFormGrid legend {
  color: var(--accent2);
  font-weight: 800;
  padding: 0 4px;
}

.tradeFieldset {
  grid-row: span 2;
}

.fieldWithFont {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 5.5rem;
  gap: 8px;
  align-items: end;
}

.profitFieldWithOptions {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 5.5rem;
}

.singleFieldRow {
  grid-template-columns: minmax(0, 1fr);
}

.fieldWithFont label {
  min-width: 0;
}

.fieldWithFont label:last-child:not(:only-child) {
  color: var(--accent);
}

.fieldWithFont .inlineCheckboxLabel {
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 2rem;
  min-height: 0;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255,255,255,.025);
  box-sizing: border-box;
  white-space: nowrap;
}

.carrierFormGrid .inlineCheckboxLabel input {
  width: auto;
}

.carrierFormGrid input,
.carrierFormGrid select {
  width: 100%;
}

@media (max-width: 1100px) {
  .carrierFormGrid,
  .carrierImageTools {
    grid-template-columns: 1fr;
  }
}
</style>
