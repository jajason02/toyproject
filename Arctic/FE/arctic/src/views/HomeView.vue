<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchBooks, fetchGenres, materializeBook, toggleCollection, toggleWishlist } from '@/api/books'

const route = useRoute()
const router = useRouter()

const books = ref([])
const booksHasMore = ref(false)
const booksPage = ref(1)
const isLoadingMore = ref(false)
const genres = ref([])
const isLoading = ref(false)
const navigatingBookKey = ref(null)
const pendingActions = ref({})
const errorMessage = ref('')
const loadMoreTrigger = ref(null)
let loadMoreObserver = null

const searchInput = ref(route.query.q || '')
const selectedGenreId = ref(route.query.genre ? Number(route.query.genre) : null)
const ordering = ref(route.query.ordering || 'latest')

async function loadGenres() {
  try {
    genres.value = await fetchGenres()
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function fetchFromQuery(query, page = 1) {
  if (page === 1) {
    isLoading.value = true
  } else {
    isLoadingMore.value = true
  }
  errorMessage.value = ''
  try {
    const data = await fetchBooks({
      ordering: query.ordering || 'latest',
      genre: query.genre ? Number(query.genre) : null,
      search: query.q || '',
      page,
    })
    const results = data?.results ?? data
    if (page === 1) {
      books.value = results
    } else {
      books.value = [...books.value, ...results]
    }
    booksHasMore.value = Boolean(data?.next)
    if (page === 1) {
      observeLoadMoreTrigger()
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
    isLoadingMore.value = false
  }
}

async function loadMore() {
  if (!booksHasMore.value || isLoadingMore.value || isLoading.value) return
  booksPage.value++
  await fetchFromQuery(route.query, booksPage.value)
}

function stopInfiniteScroll() {
  if (loadMoreObserver) {
    loadMoreObserver.disconnect()
    loadMoreObserver = null
  }
}

async function observeLoadMoreTrigger() {
  await nextTick()
  stopInfiniteScroll()

  if (!loadMoreTrigger.value || !booksHasMore.value) return

  loadMoreObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        loadMore()
      }
    },
    { rootMargin: '360px 0px' },
  )
  loadMoreObserver.observe(loadMoreTrigger.value)
}

function pushQuery() {
  const query = {}
  if (searchInput.value.trim()) query.q = searchInput.value.trim()
  if (selectedGenreId.value !== null) query.genre = String(selectedGenreId.value)
  if (ordering.value !== 'latest') query.ordering = ordering.value
  router.push({ name: 'books', query })
}

function setOrdering(value) {
  ordering.value = value
  pushQuery()
}

function handleSearch() {
  pushQuery()
}

function clearSearch() {
  searchInput.value = ''
  pushQuery()
}

function selectGenre(genreId) {
  selectedGenreId.value = genreId
  pushQuery()
}

function updateBook(bookId, changes) {
  books.value = books.value.map((book) =>
    book.id === bookId || book.isbn === bookId ? { ...book, ...changes } : book,
  )
}

async function navigateToBook(book) {
  const bookKey = book.id ?? book.isbn
  navigatingBookKey.value = bookKey
  errorMessage.value = ''

  try {
    if (book.id) {
      router.push({ name: 'book-detail', params: { bookId: book.id } })
      return
    }

    const materialized = await materializeBook(book)
    updateBook(bookKey, materialized)
    router.push({ name: 'book-detail', params: { bookId: materialized.id } })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    navigatingBookKey.value = null
  }
}

async function handleWishlistToggle(book) {
  const actionKey = `wishlist-${book.id}`
  pendingActions.value[actionKey] = true
  errorMessage.value = ''
  try {
    const result = await toggleWishlist(book.id)
    updateBook(book.id, { is_wishlisted: result.is_wishlisted })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    pendingActions.value[actionKey] = false
  }
}

async function handleCollectionToggle(book) {
  const actionKey = `collection-${book.id}`
  pendingActions.value[actionKey] = true
  errorMessage.value = ''
  try {
    const result = await toggleCollection(book.id)
    updateBook(book.id, { is_collected: result.is_collected })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    pendingActions.value[actionKey] = false
  }
}

watch(
  () => route.query,
  (query) => {
    searchInput.value = query.q || ''
    selectedGenreId.value = query.genre ? Number(query.genre) : null
    ordering.value = query.ordering || 'latest'
    booksPage.value = 1
    fetchFromQuery(query, 1)
  },
  { immediate: true },
)

watch(booksHasMore, observeLoadMoreTrigger)

onMounted(() => {
  loadGenres()
  observeLoadMoreTrigger()
})

onBeforeUnmount(stopInfiniteScroll)
</script>

<template>
  <div class="home-page">
    <div class="home-inner">
      <!-- 헤더 -->
      <div class="home-header">
        <h1 class="home-title">둘러보기</h1>
        <div class="ordering-tabs">
          <button
            :class="['ordering-btn', { active: ordering === 'latest' }]"
            type="button"
            @click="setOrdering('latest')"
          >
            최신순
          </button>
          <button
            :class="['ordering-btn', { active: ordering === 'rating' }]"
            type="button"
            @click="setOrdering('rating')"
          >
            평점순
          </button>
        </div>
      </div>

      <!-- 장르 필터 -->
      <form class="book-search" @submit.prevent="handleSearch">
        <input
          v-model="searchInput"
          class="search-input"
          type="text"
          placeholder="책 제목 또는 작가를 검색하세요"
          aria-label="도서 검색"
        />
        <button
          v-if="searchInput"
          class="search-clear"
          type="button"
          aria-label="검색어 지우기"
          @click="clearSearch"
        >
          ×
        </button>
        <button class="search-submit" type="submit">검색</button>
      </form>

      <div class="genre-filter">
        <button
          :class="['genre-chip', { active: selectedGenreId === null }]"
          type="button"
          @click="selectGenre(null)"
        >
          전체
        </button>
        <button
          v-for="genre in genres"
          :key="genre.id"
          :class="['genre-chip', { active: selectedGenreId === genre.id }]"
          type="button"
          @click="selectGenre(genre.id)"
        >
          {{ genre.name }}
        </button>
      </div>

      <!-- 에러 -->
      <p v-if="errorMessage" class="home-error">{{ errorMessage }}</p>

      <!-- 로딩 스켈레톤 -->
      <div v-else-if="isLoading" class="book-grid">
        <div v-for="n in 12" :key="n" class="book-card skeleton">
          <div class="book-cover skeleton-cover"></div>
          <div class="skeleton-line long"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>

      <!-- 빈 상태 -->
      <div v-else-if="books.length === 0" class="home-empty">
        <template v-if="route.query.q">
          <p class="empty-title">검색 결과가 없어요.</p>
          <p class="empty-sub">다른 제목이나 작가명으로 검색해 보세요.</p>
        </template>
        <template v-else>
          <p class="empty-title">아직 등록된 책이 없어요.</p>
          <p class="empty-sub">검색으로 새로운 책을 찾아보세요.</p>
        </template>
      </div>

      <!-- 도서 그리드 + 더 보기 -->
      <div v-else class="book-grid">
        <div
          v-for="book in books"
          :key="book.id ?? book.isbn"
          class="book-card"
          role="link"
          tabindex="0"
          @click="navigateToBook(book)"
          @keydown.enter="navigateToBook(book)"
        >
          <div v-if="navigatingBookKey === (book.id ?? book.isbn)" class="book-loading-mask">
            여는 중...
          </div>
          <img
            v-if="book.cover_image"
            :src="book.cover_image"
            :alt="book.title"
            class="book-cover"
          />
          <div v-else class="book-cover book-cover-placeholder"></div>

          <div class="book-info">
            <p class="book-title">{{ book.title }}</p>
            <p class="book-author">{{ book.author }}</p>
            <p class="book-rating">
              <span class="rating-star">★</span>
              {{ book.average_rating ? Number(book.average_rating).toFixed(1) : '–' }}
            </p>
          </div>
        </div>
      </div>

      <!-- 더 보기 -->
      <div v-if="booksHasMore" ref="loadMoreTrigger" class="load-more-wrap" aria-live="polite">
        <span class="load-more-indicator">
          {{ isLoadingMore ? '불러오는 중...' : '아래로 스크롤하면 더 볼 수 있어요' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 48px 0 80px;
}

.home-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 32px;
}

/* 헤더 */
.home-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 28px;
  flex-wrap: wrap;
  gap: 14px;
}

.home-title {
  font-family: 'Newsreader', serif;
  font-size: 36px;
  font-weight: 400;
  margin: 0;
  letter-spacing: -0.5px;
}

.ordering-tabs {
  display: flex;
  gap: 6px;
}

.ordering-btn {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 7px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  color: #6b6253;
  cursor: pointer;
  transition: all 0.15s;
}

.ordering-btn:hover {
  border-color: #1e3a3a;
  color: #1e3a3a;
}

.ordering-btn.active {
  background: #1e3a3a;
  border-color: #1e3a3a;
  color: #f4eedf;
  font-weight: 700;
}

/* 장르 필터 */
.book-search {
  position: relative;
  display: flex;
  width: min(620px, 100%);
  margin-bottom: 22px;
}

.search-input {
  width: 100%;
  min-height: 48px;
  border: 1px solid rgba(40, 32, 20, 0.18);
  border-radius: 8px 0 0 8px;
  background: #fffdf8;
  padding: 0 44px 0 16px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #262019;
  outline: none;
}

.search-input:focus {
  border-color: #1e3a3a;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}

.search-input::placeholder {
  color: #b1a58f;
}

.search-input::-webkit-search-cancel-button,
.search-input::-webkit-search-decoration {
  display: none;
}

.search-clear {
  position: absolute;
  top: 50%;
  right: 86px;
  border: 0;
  background: transparent;
  color: #9c9079;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transform: translateY(-50%);
}

.search-submit {
  min-width: 78px;
  border: 1px solid #1e3a3a;
  border-radius: 0 8px 8px 0;
  background: #1e3a3a;
  color: #f4eedf;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.search-submit:hover {
  background: #152a2a;
}

.genre-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 36px;
}

.genre-chip {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 8px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  color: #6b6253;
  cursor: pointer;
  transition: all 0.15s;
}

.genre-chip:hover {
  border-color: #1e3a3a;
  color: #1e3a3a;
}

.genre-chip.active {
  background: #1e3a3a;
  border-color: #1e3a3a;
  color: #f4eedf;
  font-weight: 700;
}

/* 에러 */
.home-error {
  font-size: 14px;
  color: #b06a3c;
  padding: 14px 18px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 10px;
  border-left: 3px solid #b06a3c;
}

/* 빈 상태 */
.home-empty {
  text-align: center;
  padding: 80px 24px;
}

.empty-title {
  font-family: 'Newsreader', serif;
  font-size: 22px;
  color: #4a4337;
  margin: 0 0 10px;
}

.empty-sub {
  font-size: 14px;
  color: #9c9079;
  margin: 0;
}

/* 그리드 */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 28px 20px;
}

/* 카드 */
.book-card {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition: transform 0.18s;
  position: relative;
}

.book-card:hover {
  transform: translateY(-3px);
}

.book-cover {
  aspect-ratio: 2 / 3;
  width: 100%;
  border-radius: 7px;
  object-fit: cover;
  display: block;
  margin-bottom: 12px;
  box-shadow: 0 4px 14px -6px rgba(40, 32, 20, 0.28);
}

.book-cover-placeholder {
  background: repeating-linear-gradient(135deg, #e7dcc4 0 8px, #e0d3b6 8px 16px);
}

.book-loading-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgb(244 238 223 / 78%);
  color: #1e3a3a;
  font-size: 13px;
  font-weight: 700;
}

.book-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.book-title {
  font-family: 'Newsreader', serif;
  font-size: 15px;
  line-height: 1.4;
  color: #262019;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-author {
  font-size: 12.5px;
  color: #9c9079;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-rating {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 12px;
  color: #b08a3c;
  margin: 0;
}

.rating-star {
  margin-right: 2px;
}

/* 스켈레톤 */
@keyframes shimmer {
  0% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.5;
  }
}

.skeleton {
  animation: shimmer 1.6s ease-in-out infinite;
}

.skeleton-cover {
  background: linear-gradient(135deg, #e7dcc4, #e0d3b6);
}

.skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: #e7dcc4;
  margin-bottom: 6px;
}

.skeleton-line.long {
  width: 85%;
}
.skeleton-line.short {
  width: 55%;
}

/* 더 보기 */
.load-more-wrap {
  text-align: center;
  margin-top: 40px;
}

.load-more-indicator {
  color: #8f816c;
  font-size: 14px;
}
</style>
