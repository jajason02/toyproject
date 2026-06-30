<script setup>
import { TresCanvas } from '@tresjs/core'
import { GLTFModel } from '@tresjs/cientos'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watchEffect } from 'vue'

import ShelfBook3D from './ShelfBook3D.vue'

const props = defineProps({
  reviewBooks: {
    type: Array,
    default: () => [],
  },
  wishlistBooks: {
    type: Array,
    default: () => [],
  },
  collectionBooks: {
    type: Array,
    default: () => [],
  },
  reviewTotal: {
    type: Number,
    default: 0,
  },
  wishlistTotal: {
    type: Number,
    default: 0,
  },
  collectionTotal: {
    type: Number,
    default: 0,
  },
  backgroundImage: {
    type: String,
    default: '/image/bookshelf_background_1.png',
  },
  enabledProps: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['open-shelf'])

const MODEL_PATH = '/model/arctic_tall_bookshelf_with_bottom_props.glb'
const ATTACH_POINTS_PATH = '/model/arctic_bookshelf_attach_points.json'
const MODEL_ROTATION = [-Math.PI / 2, 0, 0]
const MODEL_SCALE = [1, 1, 1]
const CAMERA_LOOK_AT = [0, 3.7, 0]
const SHELF_FRONT_LIP_DROP = 0.08
const MAX_BOOKS_PER_SHELF = 30

const modelRef = ref(null)
const attachPoints = ref(null)
const bookStates = reactive({})
const viewportWidth = ref(window.innerWidth)
const cameraPosition = computed(() => (viewportWidth.value < 640 ? [0, 3.7, 21.2] : [0, 3.7, 15.5]))

function updateViewportWidth() {
  viewportWidth.value = window.innerWidth
}

function isShelfFrontLip(name) {
  return /^bookshelf_shelf_[1-4]_(front_smooth_lip|upper_rounded_front_edge|lower_shadow_round_edge|left_rounded_lip_endcap|right_rounded_lip_endcap|minimal_carved_front_line|lip_woodgrain)/.test(
    name,
  )
}

function shelfByName(name) {
  return attachPoints.value?.shelf_slots?.find((shelf) => shelf.name === name)
}

function bookDimensions(book) {
  const pageCount = book.pageCount ?? 300
  return {
    width: Math.min(0.42, Math.max(0.28, 0.17 + pageCount / 2600)),
    depth: 0.72 + (Number(book.id) % 4) * 0.02,
    height: 1.02 + (Number(book.id) % 6) * 0.04,
  }
}

function placeBooks(books, shelfName) {
  const shelf = shelfByName(shelfName)
  if (!shelf) {
    return []
  }

  const visibleBooks = books.slice(0, MAX_BOOKS_PER_SHELF)
  const sidePadding = 0.1
  const availableWidth = shelf.x_max - shelf.x_min - sidePadding * 2
  const dimensionsList = visibleBooks.map((book) => ({
    book,
    ...bookDimensions(book),
  }))
  const naturalGap = 0.04
  const naturalWidth =
    dimensionsList.reduce((total, dimensions) => total + dimensions.width, 0) +
    Math.max(0, dimensionsList.length - 1) * naturalGap
  const widthScale = naturalWidth > availableWidth ? availableWidth / naturalWidth : 1
  const gap = naturalGap * widthScale
  let cursorX = shelf.x_min + sidePadding

  return dimensionsList.map((dimensions) => {
    const width = dimensions.width * widthScale
    const centerX = cursorX + width / 2
    const placedBook = {
      book: dimensions.book,
      bookKey: `${shelfName}-${dimensions.book.id}`,
      position: [
        centerX,
        shelf.recommended_book_center_y,
        shelf.recommended_book_base_z + dimensions.height / 2,
      ],
      ...dimensions,
      width,
    }
    cursorX += width + gap
    return placedBook
  })
}

const placedBooks = computed(() => [
  ...placeBooks(props.collectionBooks, 'book_slot_tier_2'),
  ...placeBooks(props.wishlistBooks, 'book_slot_tier_3'),
  ...placeBooks(props.reviewBooks, 'book_slot_tier_4'),
])

function toggleBook(bookKey) {
  const currentState = bookStates[bookKey] ?? 'stored'

  Object.keys(bookStates).forEach((key) => {
    if (key !== bookKey) {
      bookStates[key] = 'stored'
    }
  })

  if (currentState === 'stored') {
    bookStates[bookKey] = 'front'
  } else if (currentState === 'front') {
    bookStates[bookKey] = 'back'
  } else {
    bookStates[bookKey] = 'stored'
  }
}

onMounted(async () => {
  window.addEventListener('resize', updateViewportWidth)

  const response = await fetch(ATTACH_POINTS_PATH)
  if (!response.ok) {
    throw new Error('Failed to load bookshelf placement coordinates.')
  }
  attachPoints.value = await response.json()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateViewportWidth)
})

watchEffect(() => {
  const scene = modelRef.value?.instance?.scene
  if (!scene) {
    return
  }

  scene.traverse((child) => {
    if (isShelfFrontLip(child.name)) {
      if (child.userData.originalFrontLipZ === undefined) {
        child.userData.originalFrontLipZ = child.position.z
      }
      child.position.z = child.userData.originalFrontLipZ - SHELF_FRONT_LIP_DROP
    }

    if (child.isMesh) {
      child.castShadow = true
      child.receiveShadow = true
    }

    if (child.name.startsWith('prop_') || child.name.startsWith('optional_')) {
      child.visible = props.enabledProps.some((prefix) => child.name.startsWith(prefix))
    }
  })
})
</script>

<template>
  <div
    class="bookshelf-model"
    :style="{ backgroundImage: `url(${backgroundImage})` }"
  >
    <div class="bookshelf-scene">
      <TresCanvas clear-color="#e8decc" shadows>
        <TresPerspectiveCamera
          :position="cameraPosition"
          :look-at="CAMERA_LOOK_AT"
          :fov="35"
          :near="0.1"
          :far="100"
        />

        <TresAmbientLight :intensity="1.6" />
        <TresDirectionalLight :position="[2.5, 5.5, 4]" :intensity="2.2" cast-shadow />

        <Suspense>
          <TresGroup :rotation="MODEL_ROTATION" :scale="MODEL_SCALE">
            <GLTFModel ref="modelRef" :path="MODEL_PATH" cast-shadow receive-shadow />

            <ShelfBook3D
              v-for="placedBook in placedBooks"
              :key="placedBook.bookKey"
              :book="placedBook.book"
              :book-key="placedBook.bookKey"
              :position="placedBook.position"
              :width="placedBook.width"
              :depth="placedBook.depth"
              :height="placedBook.height"
              :active-state="bookStates[placedBook.bookKey] ?? 'stored'"
              @toggle="toggleBook"
            />
          </TresGroup>
        </Suspense>
      </TresCanvas>

      <div class="pointer-events-none absolute inset-0 z-10 font-serif">
        <button
          type="button"
          class="shelf-label pointer-events-auto top-[24.5%]"
          @click="emit('open-shelf', 'reviews')"
        >
          <span>리뷰</span>
          <strong>{{ reviewBooks.length }}/{{ reviewTotal }}</strong>
        </button>
        <button
          type="button"
          class="shelf-label pointer-events-auto top-[40.5%]"
          @click="emit('open-shelf', 'wishlist')"
        >
          <span>위시리스트</span>
          <strong>{{ wishlistBooks.length }}/{{ wishlistTotal }}</strong>
        </button>
        <button
          type="button"
          class="shelf-label pointer-events-auto top-[56.5%]"
          @click="emit('open-shelf', 'collections')"
        >
          <span>컬렉션</span>
          <strong>{{ collectionBooks.length }}/{{ collectionTotal }}</strong>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bookshelf-model {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  box-sizing: border-box;
  padding: clamp(18px, 3.4vw, 38px);
  border: clamp(8px, 1.3vw, 14px) solid #8a6543;
  border-radius: 5px;
  background-color: #e8decc;
  background-position: center;
  background-size: cover;
  box-shadow:
    0 8px 12px rgb(54 34 18 / 18%),
    0 24px 42px -20px rgb(42 28 16 / 56%),
    -7px -7px 18px rgb(255 244 218 / 34%),
    inset 0 0 0 2px #caa878,
    inset 5px 5px 9px rgb(255 231 188 / 28%),
    inset -7px -7px 12px rgb(62 38 20 / 34%),
    inset 0 0 0 7px rgb(72 45 25 / 42%);
}

.bookshelf-model::before,
.bookshelf-model::after {
  position: absolute;
  z-index: 3;
  pointer-events: none;
  content: '';
}

.bookshelf-model::before {
  inset: 7px;
  border: 1px solid rgb(255 237 197 / 72%);
  box-shadow:
    inset 4px 4px 7px rgb(255 240 207 / 32%),
    inset -5px -5px 10px rgb(56 34 18 / 27%),
    0 0 0 1px rgb(72 44 24 / 28%);
}

.bookshelf-model::after {
  inset: clamp(14px, 2vw, 23px);
  border: 1px solid rgb(122 88 52 / 72%);
  box-shadow: 0 0 0 4px rgb(239 219 180 / 24%);
}

.bookshelf-scene {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgb(80 54 31 / 42%);
  border-radius: 2px;
  background: #e8decc;
  box-shadow:
    0 9px 18px rgb(39 25 14 / 30%),
    inset 5px 5px 12px rgb(255 245 220 / 20%),
    inset -8px -8px 18px rgb(48 30 16 / 24%);
}

.shelf-label {
  position: absolute;
  right: 15%;
  display: flex;
  min-width: 108px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid rgb(137 104 55 / 70%);
  background: rgb(226 194 132 / 92%);
  padding: 7px 10px;
  color: #2c2319;
  box-shadow:
    0 2px 5px rgb(26 17 9 / 24%),
    inset 0 1px 0 rgb(255 245 211 / 75%);
  font-size: clamp(9px, 1.2vw, 13px);
  font-family: inherit;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.15s ease, filter 0.15s ease;
}

.shelf-label:hover {
  filter: brightness(1.06);
  transform: translateY(-1px);
}

.shelf-label strong {
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.8em;
  font-weight: 700;
}

@media (max-width: 900px) {
  .shelf-label {
    right: 14%;
    min-width: 96px;
    gap: 9px;
    padding: 6px 8px;
  }
}

@media (max-width: 640px) {
  .bookshelf-model {
    padding: 14px;
    border-width: 8px;
  }

  .bookshelf-model::after {
    inset: 11px;
  }

  .shelf-label {
    right: 12%;
    min-width: 78px;
    gap: 6px;
    padding: 5px 6px;
    font-size: clamp(8px, 2.5vw, 11px);
  }
}

@media (max-width: 420px) {
  .shelf-label {
    right: 10%;
    min-width: 68px;
    padding: 4px 5px;
  }
}

.bookshelf-scene :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
