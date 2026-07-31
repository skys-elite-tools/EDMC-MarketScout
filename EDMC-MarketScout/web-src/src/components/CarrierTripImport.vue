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
  <section class="carrierTripImport" aria-labelledby="carrier-trip-import-title">
    <div>
      <h2 id="carrier-trip-import-title">Import Spansh Fleet Carrier Route</h2>
      <p>Choose one CSV or JSON export. JSON exports can include coordinates, fuel state, and restock quantities.</p>
    </div>
    <label class="carrierTripImportButton">
      <input type="file" accept=".csv,.json,text/csv,application/json" :disabled="busy" @change="chooseFile" />
      <span>{{ busy ? 'Importing...' : 'Choose CSV or JSON' }}</span>
    </label>
  </section>
</template>

<style scoped>
.carrierTripImport {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(255,255,255,.03);
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

.carrierTripImportButton {
  flex: none;
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
    align-items: stretch;
    flex-direction: column;
  }

  .carrierTripImportButton {
    text-align: center;
  }
}
</style>
