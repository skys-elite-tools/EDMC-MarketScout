<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  imageUrl: { type: String, required: true },
  activeLayers: { type: Array, required: true },
  layerText: { type: Object, required: true },
  fontSizes: { type: Object, required: true },
  textColor: { type: String, required: true },
})

const emit = defineEmits(['download-image', 'move-layer'])

const stageRef = ref(null)
const stageWidth = ref(0)
let resizeObserver = null
let activeDrag = null

function updateStageSize() {
  if (!stageRef.value) return
  stageWidth.value = stageRef.value.getBoundingClientRect().width || 0
}

function previewFontSize(layer) {
  const exportedSize = Number(props.fontSizes[layer.sizeKey] || 32)
  return Math.max(10, exportedSize * (stageWidth.value || 1200) / 1200)
}

function layerStyle(layer) {
  const size = previewFontSize(layer)
  return {
    left: `${layer.x}%`,
    top: `${layer.y}%`,
    color: props.textColor,
    fontSize: `${size}px`,
    fontWeight: layer.weight,
    textAlign: layer.align,
    transform: layer.align === 'right' ? 'translate(-100%, -50%)' : 'translate(-50%, -50%)',
  }
}

function startDrag(event, layer) {
  if (!stageRef.value) return
  event.preventDefault()
  const rect = stageRef.value.getBoundingClientRect()
  activeDrag = {
    key: layer.key,
    pointerId: event.pointerId,
    dx: event.clientX - (rect.left + (layer.x / 100) * rect.width),
    dy: event.clientY - (rect.top + (layer.y / 100) * rect.height),
  }
  event.currentTarget.setPointerCapture(event.pointerId)
}

function moveDrag(event) {
  if (!activeDrag || !stageRef.value || activeDrag.pointerId !== event.pointerId) return
  const rect = stageRef.value.getBoundingClientRect()
  const x = ((event.clientX - activeDrag.dx - rect.left) / rect.width) * 100
  const y = ((event.clientY - activeDrag.dy - rect.top) / rect.height) * 100
  emit('move-layer', {
    key: activeDrag.key,
    x: Math.min(96, Math.max(4, x)),
    y: Math.min(94, Math.max(6, y)),
  })
}

function stopDrag(event) {
  if (activeDrag?.pointerId === event.pointerId) activeDrag = null
}

onMounted(async () => {
  await nextTick()
  updateStageSize()
  resizeObserver = new ResizeObserver(updateStageSize)
  if (stageRef.value) resizeObserver.observe(stageRef.value)
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})

watch(() => props.imageUrl, () => nextTick(updateStageSize))
</script>

<template>
  <section class="carrierSection">
    <h2>Image</h2>
    <div ref="stageRef" class="carrierImageStage">
      <img v-if="imageUrl" :src="imageUrl" alt="" />
      <div class="imageDownloadButtons" aria-label="Download image">
        <button type="button" title="Download PNG" @click="emit('download-image', 'png')">PNG ↓</button>
        <button type="button" title="Download JPG" @click="emit('download-image', 'jpg')">JPG ↓</button>
      </div>
      <div
        v-for="layer in activeLayers"
        :key="layer.key"
        class="carrierTextLayer"
        :class="`carrierLayer-${layer.key}`"
        :style="layerStyle(layer)"
        @pointerdown="startDrag($event, layer)"
        @pointermove="moveDrag"
        @pointerup="stopDrag"
        @pointercancel="stopDrag"
      >
        {{ layerText[layer.key] }}
      </div>
    </div>
  </section>
</template>
