<script setup>
import { computed } from 'vue'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  activeState: {
    type: String,
    default: 'stored',
  },
})

const emit = defineEmits(['toggle'])

const bookWidth = 200
const bookHeight = computed(() => props.book.height ?? 280)

const thickness = computed(() => {
  const pages = props.book.pageCount ?? 300
  return Math.max(0.85 * pages ** 0.6, 8)
})

const animationClass = computed(
  () =>
    ({
      front: 'book-show',
      back: 'book-showback',
      'front-away': 'book-showaway',
      'back-away': 'book-putaway',
    })[props.activeState],
)
</script>

<template>
  <div class="book-container">
    <div class="book" :class="animationClass" @click="emit('toggle', book.id)">
      <!-- 앞표지 -->
      <img
        class="cover"
        :src="book.coverUrl"
        :alt="book.title"
        :style="{
          width: `${bookWidth}px`,
          height: `${bookHeight}px`,
          transform: `translateZ(${thickness / 2}px)`,
        }"
      />

      <!-- 책등 -->
      <div
        class="spine"
        :style="{
          width: `${thickness}px`,
          height: `${bookHeight}px`,
          backgroundColor: book.color,
          transform: `
            translateX(-${thickness / 2}px)
            translateY(-${bookHeight}px)
            rotateY(-90deg)
          `,
        }"
      />

      <!-- 뒤표지 -->
      <div
        class="back book-font"
        :style="{
          width: `${bookWidth}px`,
          height: `${bookHeight}px`,
          backgroundColor: book.color,
          transform: `
            translateY(-${bookHeight * 2}px)
            translateZ(-${thickness / 2}px)
            rotateY(180deg)
          `,
        }"
      >
        {{ book.description }}
      </div>

      <!-- 페이지 면 -->
      <div
        class="pages"
        :style="{
          width: `${thickness - 1}px`,
          height: `${bookHeight - 6}px`,
          transform: `
            translateY(-${bookHeight * 3 - 3}px)
            translateX(${bookWidth - thickness / 2 - 3}px)
            rotateY(90deg)
          `,
        }"
      />
    </div>
  </div>
</template>

<style scoped>
.book-container,
.book {
  position: absolute;
  transform-style: preserve-3d;
}

.book {
  cursor: pointer;
  transform: rotateY(90deg);
}

.book-font {
  font-family: 'Nanum Myeongjo', serif;
}

.cover {
  display: block;
  object-fit: cover;
  border-radius: 0 3px 3px 0;
}

.back {
  box-sizing: border-box;
  padding: 12px;
  overflow: hidden;
  font-size: 10px;
  border-radius: 3px 0 0 3px;
}

.pages {
  background: #f1f1f1;
}

/* 책장 → 앞표지 */
@keyframes book-display {
  0% {
    transform: translateX(0) rotateY(90deg);
  }
  50% {
    transform: translateZ(210px) rotateY(90deg);
  }
  100% {
    transform: translateZ(210px) rotateY(0);
  }
}

/* 앞표지 → 뒤표지 */
@keyframes book-flip {
  from {
    transform: translateZ(210px) rotateY(0);
  }
  to {
    transform: translateZ(210px) rotateY(180deg);
  }
}

/* 뒤표지 → 책장 */
@keyframes book-away {
  0% {
    transform: translateZ(210px) rotateY(180deg);
  }
  50% {
    transform: translateZ(210px) rotateY(90deg);
  }
  100% {
    transform: translateX(0) rotateY(90deg);
  }
}

/* 앞표지 → 책장 */
@keyframes book-show-away {
  0% {
    transform: translateZ(210px) rotateY(0);
  }
  50% {
    transform: translateZ(210px) rotateY(90deg);
  }
  100% {
    transform: translateX(0) rotateY(90deg);
  }
}

.book-show {
  animation: book-display 1.3s ease both;
}

.book-showback {
  animation: book-flip 0.7s ease both;
}

.book-showaway {
  animation: book-show-away 0.7s ease both;
}

.book-putaway {
  animation: book-away 0.7s ease both;
}
</style>
