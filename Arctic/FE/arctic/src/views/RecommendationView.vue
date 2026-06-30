<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { fetchRecommendations } from '@/api/ai'
import { toggleWishlist } from '@/api/books'

const recommendation = ref(null)
const isLoading = ref(false)
const isRefreshing = ref(false)
const pendingIds = ref(new Set())
const errorMessage = ref('')
const remainingSeconds = ref(0)
let timerId = null

const daily = computed(() => recommendation.value?.daily ?? null)
const dailyBook = computed(() => daily.value?.book ?? null)
const feed = computed(() => recommendation.value?.feed ?? [])
const remainingTime = computed(() => {
  const hours = Math.floor(remainingSeconds.value / 3600)
  const minutes = Math.floor((remainingSeconds.value % 3600) / 60)
  const seconds = remainingSeconds.value % 60
  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':')
})

function updateRemainingTime() {
  const nextRefreshAt = recommendation.value?.next_refresh_at
  remainingSeconds.value = nextRefreshAt
    ? Math.max(Math.floor((new Date(nextRefreshAt) - Date.now()) / 1000), 0)
    : 0
}

async function loadRecommendations(refresh = false) {
  if (refresh) isRefreshing.value = true
  else isLoading.value = true
  errorMessage.value = ''
  try {
    recommendation.value = await fetchRecommendations()
    updateRemainingTime()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

async function handleWishlist(targetBook) {
  pendingIds.value = new Set([...pendingIds.value, targetBook.id])
  try {
    const result = await toggleWishlist(targetBook.id)
    if (dailyBook.value?.id === targetBook.id) {
      recommendation.value.daily.book.is_wishlisted = result.is_wishlisted
    }
    recommendation.value.feed = feed.value.map((item) => (
      item.book.id === targetBook.id
        ? { ...item, book: { ...item.book, is_wishlisted: result.is_wishlisted } }
        : item
    ))
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    const next = new Set(pendingIds.value)
    next.delete(targetBook.id)
    pendingIds.value = next
  }
}

onMounted(async () => {
  await loadRecommendations()
  timerId = window.setInterval(updateRemainingTime, 1000)
})

onBeforeUnmount(() => window.clearInterval(timerId))
</script>

<template>
  <main class="min-h-[calc(100vh-64px)] bg-[#f4eedf] text-[#262019]">
    <header class="border-b border-black/10">
      <div class="mx-auto max-w-[1180px] px-6 py-14 sm:px-8 lg:py-20">
        <p class="text-xs font-semibold text-[#8f826c]">CURATED FOR YOU</p>
        <h1 class="mt-4 font-serif text-4xl sm:text-6xl">도서 추천</h1>
        <p class="mt-4 max-w-2xl text-sm leading-7 text-[#786d5c] sm:text-base">
          오늘의 한 권과 취향에 맞춰 계속 달라지는 추천 도서를 만나보세요.
        </p>
      </div>
    </header>

    <div class="mx-auto max-w-[1180px] px-6 py-12 sm:px-8 lg:py-16">
      <p
        v-if="errorMessage"
        class="mb-8 border-l-2 border-[#b06a3c] bg-[#fbf3e6] px-5 py-4 text-sm text-[#9b5631]"
      >
        {{ errorMessage }}
      </p>

      <div v-if="isLoading" class="h-96 animate-pulse bg-[#dfd3bd]" />

      <template v-else-if="dailyBook">
        <section
          class="grid overflow-hidden border border-[#d4c9b5] bg-[#fbf7ee] lg:grid-cols-[0.72fr_1.28fr]"
        >
          <div class="flex items-center justify-center bg-[#e8decc] p-10 sm:p-14">
            <img
              v-if="dailyBook.cover_image"
              :src="dailyBook.cover_image"
              :alt="dailyBook.title"
              fetchpriority="high"
              decoding="async"
              class="aspect-[2/3] w-full max-w-[290px] object-cover shadow-2xl"
            />
          </div>
          <div class="flex flex-col justify-center p-8 sm:p-12 lg:p-16">
            <div class="flex items-center justify-between gap-4">
              <p class="text-xs font-semibold text-[#9a8d76]">TODAY'S PICK</p>
              <p class="font-mono text-xs text-[#6f6453]">
                다음 추천까지 {{ remainingTime }}
              </p>
            </div>
            <h2 class="mt-4 font-serif text-3xl leading-tight sm:text-5xl">
              {{ dailyBook.title }}
            </h2>
            <p class="mt-3 text-sm text-[#8a7d68]">{{ dailyBook.author }}</p>
            <div class="mt-6 flex flex-wrap gap-2">
              <span
                v-for="genre in dailyBook.genres"
                :key="genre.id"
                class="border border-[#b9aa8d] px-3 py-1 text-xs"
              >
                {{ genre.name }}
              </span>
            </div>
            <p class="mt-7 text-sm text-[#655b4d]">
              예상 평점
              <strong>{{ Number(daily.scores.expected_rating || 0).toFixed(1) }}</strong>
              · 긍정 반응
              <strong>{{ Math.round((daily.scores.positive_probability || 0) * 100) }}%</strong>
            </p>
            <div class="mt-9 flex flex-wrap gap-3">
              <RouterLink
                :to="{ name: 'book-detail', params: { bookId: dailyBook.id } }"
                class="inline-flex min-h-12 items-center bg-[#173b38] px-7 text-sm font-semibold text-white"
              >
                자세히 보기
              </RouterLink>
              <button
                class="min-h-12 border border-[#173b38] px-7 text-sm font-semibold"
                :disabled="pendingIds.has(dailyBook.id)"
                @click="handleWishlist(dailyBook)"
              >
                {{ dailyBook.is_wishlisted ? '위시리스트 제거' : '위시리스트 담기' }}
              </button>
            </div>
            <p class="mt-5 text-xs text-[#9a8d76]">
              오늘의 책은 한국시간 자정까지 고정됩니다.
            </p>
          </div>
        </section>

        <section class="mt-20">
          <div class="flex flex-wrap items-end justify-between gap-5 border-b border-[#d4c9b5] pb-5">
            <div>
              <p class="text-xs font-semibold text-[#9a8d76]">FOR YOU</p>
              <h2 class="mt-2 font-serif text-3xl">계속 둘러볼 책</h2>
            </div>
            <button
              type="button"
              class="min-h-11 border border-[#173b38] px-5 text-sm font-semibold text-[#173b38] disabled:opacity-50"
              :disabled="isRefreshing"
              @click="loadRecommendations(true)"
            >
              {{ isRefreshing ? '추천 불러오는 중' : '추천 새로고침' }}
            </button>
          </div>

          <div class="mt-8 grid gap-x-6 gap-y-12 sm:grid-cols-2 lg:grid-cols-4">
            <article v-for="item in feed" :key="item.book.id" class="min-w-0">
              <RouterLink
                :to="{ name: 'book-detail', params: { bookId: item.book.id } }"
                class="block"
              >
                <img
                  v-if="item.book.cover_image"
                  :src="item.book.cover_image"
                  :alt="item.book.title"
                  loading="lazy"
                  decoding="async"
                  class="aspect-[2/3] w-full bg-[#dfd3bd] object-cover shadow-md"
                />
                <div v-else class="aspect-[2/3] w-full bg-[#dfd3bd]" />
                <h3 class="mt-4 truncate font-serif text-xl">{{ item.book.title }}</h3>
                <p class="mt-1 truncate text-sm text-[#8a7d68]">{{ item.book.author }}</p>
              </RouterLink>
              <div class="mt-3 flex items-center justify-between gap-3">
                <span class="text-xs text-[#856f4f]">
                  예상 {{ Number(item.scores.expected_rating || 0).toFixed(1) }}
                </span>
                <button
                  class="text-xs font-semibold text-[#173b38] disabled:opacity-50"
                  :disabled="pendingIds.has(item.book.id)"
                  @click="handleWishlist(item.book)"
                >
                  {{ item.book.is_wishlisted ? '저장 취소' : '위시리스트' }}
                </button>
              </div>
            </article>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
