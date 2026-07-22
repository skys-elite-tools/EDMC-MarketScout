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
