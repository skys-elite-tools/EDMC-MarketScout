<script setup>
defineProps({
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['import'])

async function chooseFile(event) {
  const input = event.target
  const file = input.files?.[0]
  if (!file) return
  try {
    emit('import', { filename: file.name, content: await file.text() })
  } finally {
    input.value = ''
  }
}
</script>

<template>
  <div class="carrierTripImport">
    <div>
      <h2 id="carrier-trip-import-title">Trips</h2>
      <p>
        Choose a CSV or JSON Spansh export
        <span
          class="infoTooltip"
          title="JSON exports can include coordinates, fuel state, and restock quantities"
          aria-label="JSON exports can include coordinates, fuel state, and restock quantities"
        >?</span>
      </p>
    </div>
    <label class="carrierTripImportButton">
      <input type="file" accept=".csv,.json,text/csv,application/json" :disabled="busy" @change="chooseFile" />
      <span>{{ busy ? 'Importing...' : 'Import CSV/JSON' }}</span>
    </label>
  </div>
</template>

<style scoped>
.carrierTripImport {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  box-sizing: border-box;
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}

.carrierTripImport h2 {
  margin: 0 0 4px;
  color: var(--accent2);
  font-size: 15px;
}

.carrierTripImport p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.infoTooltip {
  display: inline-grid;
  width: 14px;
  height: 14px;
  margin-left: 3px;
  place-items: center;
  border: 1px solid rgba(140,200,255,.45);
  border-radius: 50%;
  color: var(--accent);
  cursor: help;
  font-size: 10px;
  font-weight: 800;
  vertical-align: -1px;
}

.carrierTripImportButton {
  flex: none;
  white-space: nowrap;
  color: var(--text);
  cursor: pointer;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: #263142;
  padding: 7px 10px;
  font-weight: 800;
}

.carrierTripImportButton:hover {
  border-color: var(--accent);
}

.carrierTripImportButton input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

@media (max-width: 700px) {
  .carrierTripImport {
    grid-template-columns: 1fr;
  }

  .carrierTripImportButton {
    justify-self: start;
    text-align: center;
  }
}
</style>
