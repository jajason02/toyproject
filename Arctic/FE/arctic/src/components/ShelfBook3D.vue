<script setup>
import { useLoop } from '@tresjs/core'
import { CanvasTexture, DoubleSide, LinearFilter, MathUtils, SRGBColorSpace } from 'three'
import { computed, onUnmounted, ref, shallowRef, watch } from 'vue'

import { getSharedSpineTexture } from './shelfBookTextures'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  bookKey: {
    type: String,
    required: true,
  },
  position: {
    type: Array,
    required: true,
  },
  width: {
    type: Number,
    required: true,
  },
  depth: {
    type: Number,
    required: true,
  },
  height: {
    type: Number,
    required: true,
  },
  activeState: {
    type: String,
    default: 'stored',
  },
})

const emit = defineEmits(['toggle'])

const groupRef = ref(null)
const rotationTarget = ref(0)
const previousState = ref('stored')
const coverTexture = shallowRef(null)
const spineTexture = shallowRef(null)
const backTexture = shallowRef(null)
let animationHandle = null
let coverRequestId = 0
let coverAbortController = null

function getOpaqueBounds(context, width, height) {
  const pixels = context.getImageData(0, 0, width, height).data
  let minX = width
  let minY = height
  let maxX = 0
  let maxY = 0

  for (let y = 0; y < height; y += 2) {
    for (let x = 0; x < width; x += 2) {
      const alpha = pixels[(y * width + x) * 4 + 3]
      if (alpha > 24) {
        minX = Math.min(minX, x)
        minY = Math.min(minY, y)
        maxX = Math.max(maxX, x)
        maxY = Math.max(maxY, y)
      }
    }
  }

  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  }
}

async function createSpineTexture(color, bookId) {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 2048

  const context = canvas.getContext('2d')
  let imageLoaded = false

  try {
    const spineNumber = (Math.abs(Number(bookId) || 0) % 5) + 1
    const response = await fetch(`/image/book_spine_tight${spineNumber}.png`)
    if (response.ok) {
      const image = await createImageBitmap(await response.blob())
      const sourceCanvas = document.createElement('canvas')
      sourceCanvas.width = image.width
      sourceCanvas.height = image.height
      const sourceContext = sourceCanvas.getContext('2d')
      sourceContext.drawImage(image, 0, 0)
      const bounds = getOpaqueBounds(sourceContext, sourceCanvas.width, sourceCanvas.height)
      context.drawImage(
        image,
        bounds.x,
        bounds.y,
        bounds.width,
        bounds.height,
        0,
        0,
        canvas.width,
        canvas.height,
      )

      // 이미지의 투명 영역은 유지하면서 책 고유 색상을 약하게 입힌다.
      context.globalCompositeOperation = 'source-atop'
      context.globalAlpha = 0.1
      context.fillStyle = color
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.globalAlpha = 1
      context.globalCompositeOperation = 'source-over'
      imageLoaded = true
      image.close()
    }
  } catch {
    // Use the generated fallback color below.
  }

  if (!imageLoaded) {
    context.fillStyle = color
    context.fillRect(0, 0, canvas.width, canvas.height)
  }

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 16
  texture.generateMipmaps = false
  texture.minFilter = LinearFilter
  texture.magFilter = LinearFilter
  return texture
}

async function createCoverTexture(coverBlob) {
  const image = await createImageBitmap(coverBlob)
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = Math.round((canvas.width * props.height) / props.depth)

  const context = canvas.getContext('2d')
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  image.close()

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  return texture
}

function createBackTexture(book) {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = Math.round((canvas.width * props.height) / props.depth)

  const context = canvas.getContext('2d')
  const padding = canvas.width * 0.09
  const centerX = canvas.width / 2
  const rating = Number(book.globalAverageRating ?? 0).toFixed(1)
  const reviewCount = Number(book.globalReviewCount ?? 0)
  const wishlistCount = Number(book.globalWishlistCount ?? 0)
  const collectionCount = Number(book.globalCollectionCount ?? 0)

  context.fillStyle = '#efe4cc'
  context.fillRect(0, 0, canvas.width, canvas.height)

  const gradient = context.createLinearGradient(0, 0, canvas.width, canvas.height)
  gradient.addColorStop(0, 'rgba(255, 252, 239, 0.72)')
  gradient.addColorStop(0.55, 'rgba(205, 179, 136, 0.08)')
  gradient.addColorStop(1, 'rgba(116, 83, 48, 0.16)')
  context.fillStyle = gradient
  context.fillRect(0, 0, canvas.width, canvas.height)

  context.strokeStyle = book.color || '#76553b'
  context.lineWidth = 12
  context.strokeRect(padding * 0.55, padding * 0.55, canvas.width - padding * 1.1, canvas.height - padding * 1.1)

  context.strokeStyle = 'rgba(92, 64, 39, 0.38)'
  context.lineWidth = 3
  context.strokeRect(padding * 0.75, padding * 0.75, canvas.width - padding * 1.5, canvas.height - padding * 1.5)

  const lines = [
    `★ ${rating}`,
    `리뷰 ${reviewCount}개`,
    `위시 ${wishlistCount}명`,
    `컬렉션 ${collectionCount}개`,
  ]
  const fontSize = Math.max(80, Math.min(58, canvas.height * 0.065))
  const lineHeight = fontSize * 1.75
  const startY = canvas.height / 2 - (lineHeight * (lines.length - 1)) / 2

  context.fillStyle = '#35291f'
  context.textAlign = 'center'
  context.textBaseline = 'middle'

  lines.forEach((line, index) => {
    context.font = `800 ${fontSize}px "Noto Sans KR", "Noto Serif KR", serif`
    context.fillText(line, centerX, startY + lineHeight * index)
  })

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 16
  texture.minFilter = LinearFilter
  texture.magFilter = LinearFilter
  return texture
}

watch(
  () => props.book.id,
  async (bookId) => {
    spineTexture.value = await getSharedSpineTexture(bookId)
  },
  { immediate: true },
)

async function loadCoverTexture(coverUrls) {
  const urls = coverUrls.filter(Boolean)
  if (!urls.length) {
    return
  }

  for (const coverUrl of urls) {
    const requestId = ++coverRequestId
    coverAbortController = new AbortController()

    try {
      const response = await fetch(coverUrl, {
        signal: coverAbortController.signal,
      })
      if (!response.ok) {
        continue
      }

      const texture = await createCoverTexture(await response.blob())
      if (requestId !== coverRequestId) {
        texture.dispose()
        return
      }

      texture.colorSpace = SRGBColorSpace
      texture.needsUpdate = true
      coverTexture.value = texture
      return
    } catch (error) {
      if (error.name === 'AbortError') {
        return
      }
    } finally {
      if (requestId === coverRequestId) {
        coverAbortController = null
      }
    }
  }

  coverTexture.value = null
}

watch(
  () => [props.book.coverUrl, props.book.coverImage],
  async ([coverUrl, coverImage]) => {
    coverRequestId += 1
    coverAbortController?.abort()
    coverAbortController = null
    coverTexture.value?.dispose()
    coverTexture.value = null

    await loadCoverTexture([coverUrl, coverImage])
  },
  { immediate: true },
)

watch(
  () => [
    props.book.globalAverageRating,
    props.book.globalReviewCount,
    props.book.globalWishlistCount,
    props.book.globalCollectionCount,
    props.book.color,
  ],
  () => {
    backTexture.value?.dispose()
    backTexture.value = createBackTexture(props.book)
  },
  { immediate: true },
)

onUnmounted(() => {
  animationHandle?.off()
  coverRequestId += 1
  coverAbortController?.abort()
  coverTexture.value?.dispose()
  backTexture.value?.dispose()
})

const storedPosition = computed(() => props.position)
const targetPosition = computed(() => {
  if (props.activeState === 'stored') {
    return storedPosition.value
  }

  return [storedPosition.value[0], storedPosition.value[1] - 1.05, storedPosition.value[2] + 0.08]
})

const { onBeforeRender } = useLoop()

function stopAnimation() {
  animationHandle?.off()
  animationHandle = null
}

function animateBook() {
  const group = groupRef.value
  if (!group) {
    return
  }

  const [targetX, targetY, targetZ] = targetPosition.value
  group.position.x = MathUtils.lerp(group.position.x, targetX, 0.14)
  group.position.y = MathUtils.lerp(group.position.y, targetY, 0.14)
  group.position.z = MathUtils.lerp(group.position.z, targetZ, 0.14)
  group.rotation.z = MathUtils.lerp(group.rotation.z, rotationTarget.value, 0.14)

  const positionSettled =
    Math.abs(group.position.x - targetX) < 0.002
    && Math.abs(group.position.y - targetY) < 0.002
    && Math.abs(group.position.z - targetZ) < 0.002
  const rotationSettled =
    Math.abs(group.rotation.z - rotationTarget.value) < 0.002

  if (!positionSettled || !rotationSettled) {
    return
  }

  group.position.set(targetX, targetY, targetZ)
  group.rotation.z = rotationTarget.value

  if (props.activeState === 'stored' && rotationTarget.value === -Math.PI * 2) {
    group.rotation.z = 0
    rotationTarget.value = 0
  }

  stopAnimation()
}

function startAnimation() {
  if (!animationHandle) {
    animationHandle = onBeforeRender(animateBook)
  }
}

watch(
  () => props.activeState,
  (state, oldState) => {
    if (state === 'front') {
      rotationTarget.value = -Math.PI / 2
    } else if (state === 'back') {
      rotationTarget.value = -Math.PI * 1.5
    } else {
      rotationTarget.value = previousState.value === 'back' ? -Math.PI * 2 : 0
    }
    previousState.value = state

    if (oldState !== undefined) {
      startAnimation()
    }
  },
  { immediate: true },
)

function handleClick(event) {
  event.stopPropagation()
  emit('toggle', props.bookKey)
}
</script>

<template>
  <TresGroup ref="groupRef" :position="position" @click="handleClick">
    <TresMesh cast-shadow receive-shadow>
      <TresBoxGeometry :args="[width, depth, height]" />
      <TresMeshStandardMaterial :color="book.color" :roughness="0.72" :metalness="0.04" />
    </TresMesh>

    <TresGroup :position="[width / 2 + 0.003, 0, 0]" :rotation="[0, Math.PI / 2, 0]">
      <TresMesh :rotation="[0, 0, Math.PI / 2]" cast-shadow receive-shadow>
        <TresPlaneGeometry :args="[depth, height]" />
        <TresMeshStandardMaterial
          v-if="coverTexture"
          :key="coverTexture.uuid"
          color="#ffffff"
          :map="coverTexture"
          :roughness="0.62"
          :side="DoubleSide"
        />
        <TresMeshStandardMaterial v-else color="#ffffff" :roughness="0.62" :side="DoubleSide" />
      </TresMesh>
    </TresGroup>

    <TresGroup :position="[-width / 2 - 0.001, 0, 0]" :rotation="[0, -Math.PI / 2, 0]">
      <TresMesh :rotation="[0, 0, -Math.PI / 2]" cast-shadow receive-shadow>
        <TresPlaneGeometry :args="[depth, height]" />
        <TresMeshStandardMaterial
          v-if="backTexture"
          :key="backTexture.uuid"
          color="#ffffff"
          :map="backTexture"
          :roughness="0.82"
          :metalness="0"
          :side="DoubleSide"
        />
        <TresMeshStandardMaterial
          v-else
          color="#efe4cc"
          :roughness="0.82"
          :metalness="0"
          :side="DoubleSide"
        />
      </TresMesh>
    </TresGroup>

    <TresMesh
      :position="[0, -depth / 2 - 0.004, 0]"
      :rotation="[Math.PI / 2, 0, 0]"
      cast-shadow
      receive-shadow
    >
      <TresPlaneGeometry :args="[width, height * 0.98]" />
      <TresMeshStandardMaterial
        v-if="spineTexture"
        color="#ffffff"
        :map="spineTexture"
        :roughness="0.76"
        :metalness="0.02"
        :side="DoubleSide"
        :transparent="true"
        :alpha-test="0.02"
      />
      <TresMeshStandardMaterial
        v-else
        :color="book.color"
        :roughness="0.76"
        :metalness="0.02"
        :side="DoubleSide"
      />
    </TresMesh>
  </TresGroup>
</template>
