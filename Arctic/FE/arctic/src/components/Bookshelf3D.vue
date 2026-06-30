<script setup>
import { reactive } from 'vue'
import Book3D from './Book3D.vue'

defineProps({
  books: {
    type: Array,
    required: true,
  },
})

const states = reactive({})

function toggleBook(id) {
  const currentState = states[id] ?? 'stored'

  // 다른 책을 책장으로 돌려보냄
  Object.keys(states).forEach((bookId) => {
    if (Number(bookId) === id) return

    if (states[bookId] === 'front') {
      states[bookId] = 'front-away'
    } else if (states[bookId] === 'back') {
      states[bookId] = 'back-away'
    }
  })

  if (currentState === 'stored' || currentState === 'front-away' || currentState === 'back-away') {
    states[id] = 'front'
  } else if (currentState === 'front') {
    states[id] = 'back'
  } else {
    states[id] = 'back-away'
  }
}

function thickness(book) {
  return Math.max(0.85 * (book.pageCount ?? 300) ** 0.6, 8)
}

function offsetAt(index, books) {
  return books.slice(0, index).reduce((sum, book) => sum + thickness(book), 0)
}
</script>

<template>
  <div class="scene">
    <Book3D
      v-for="(book, index) in books"
      :key="book.id"
      :book="book"
      :active-state="states[book.id] ?? 'stored'"
      :style="{
        transform: `translateX(
          ${offsetAt(index, books) + thickness(book) / 2}px
        )`,
        top: `calc(100% - ${book.height ?? 280}px)`,
      }"
      @toggle="toggleBook"
    />
  </div>
</template>

<style scoped>
.scene {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  perspective: 800px;
  transform-style: preserve-3d;
}
</style>
