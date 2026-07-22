<script setup>
defineProps({
  title: { type: String, default: 'Open help' },
  label: { type: String, default: '?' },
})
const emit = defineEmits(['open'])
</script>

<template>
  <button
    type="button"
    class="infoButton"
    :title="title"
    :aria-label="title"
    @click.stop="emit('open')"
  >
    {{ label }}
  </button>
</template>
