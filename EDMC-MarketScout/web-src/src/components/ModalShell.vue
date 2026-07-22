<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  titleId: { type: String, default: '' },
  panelClass: { type: String, default: '' },
})

const emit = defineEmits(['close'])

const headingId = computed(() => props.titleId || `modal-${props.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`)
</script>

<template>
  <div class="modalBackdrop" @click.self="emit('close')">
    <section :class="panelClass" role="dialog" aria-modal="true" :aria-labelledby="headingId">
      <div class="modalHeader">
        <h2 :id="headingId">{{ title }}</h2>
        <slot name="header-extra"></slot>
        <button type="button" class="iconButton" title="Close" @click="emit('close')">×</button>
      </div>

      <slot></slot>

      <div v-if="$slots.actions" class="modalActions">
        <slot name="actions"></slot>
      </div>
    </section>
  </div>
</template>
