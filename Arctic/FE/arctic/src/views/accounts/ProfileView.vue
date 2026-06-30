<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchProfile, toggleFollow } from '@/api/accounts'
import { isAuthenticated } from '@/api/client'
import { getBookCoverUrl } from '@/api/books'
import {
  createDraftComment,
  deleteDraftComment,
  fetchDraftComments,
  toggleDraftCommentLike,
  toggleDraftLike,
  updateDraft,
  updateDraftComment,
} from '@/api/ai'
import BookshelfModel from '@/components/BookshelfModel.vue'

const route = useRoute()
const router = useRouter()

const profile = ref(null)
const currentUser = ref(null)
const isLoading = ref(false)
const isFollowLoading = ref(false)
const errorMessage = ref('')
const activeTab = ref('reviews')
const isBookshelfVisible = ref(false)
const librarySection = ref(null)
const reviewLoadMoreTrigger = ref(null)
const visibleReviewCount = ref(10)
let reviewObserver = null
const MAX_SHELF_BOOKS = 30
const activeShelfCategory = ref(null)
const shelfSelections = ref({
  reviews: [],
  wishlist: [],
  collections: [],
})
const shelfSelectionDraft = ref([])
const shelfSelectionMessage = ref('')
const BOOKSHELF_BACKGROUNDS = [
  {
    id: 'background-1',
    label: '배경 1',
    image: '/image/bookshelf_background_1.png',
  },
  {
    id: 'background-2',
    label: '배경 2',
    image: '/image/bookshelf_background_2.png',
  },
]
const BOOKSHELF_PROPS = [
  { prefix: 'prop_bottom_potted_fern', label: '화분' },
  { prefix: 'prop_bottom_scroll_bundle', label: '두루마리' },
  { prefix: 'prop_bottom_small_globe', label: '지구본' },
  { prefix: 'prop_bottom_candle_set', label: '양초' },
  { prefix: 'prop_bottom_hourglass', label: '모래시계' },
  { prefix: 'prop_bottom_ink_quill', label: '잉크와 깃펜' },
  { prefix: 'prop_bottom_small_frame', label: '액자' },
  { prefix: 'prop_bottom_vase_branch', label: '꽃병' },
  { prefix: 'prop_bottom_lantern', label: '랜턴' },
  { prefix: 'prop_bottom_ceramic_bowl', label: '도자기 그릇' },
  { prefix: 'prop_bottom_round_clock', label: '시계' },
]
const bookshelfAppearance = ref({
  backgroundImage: BOOKSHELF_BACKGROUNDS[0].image,
  enabledProps: BOOKSHELF_PROPS.map((item) => item.prefix),
})

const profileUserId = computed(() => route.params.userId || null)
const isMyProfile = computed(() => (
  profileUserId.value === null
  || currentUser.value?.id === Number(profileUserId.value)
))
const profileBasePath = computed(() => (
  isMyProfile.value ? '/profile' : `/profile/${profileUserId.value}`
))
const preferredGenres = computed(() => profile.value?.preferred_genres || [])
const reviews = computed(() => profile.value?.reviews || [])
const visibleReviews = computed(() => reviews.value.slice(0, visibleReviewCount.value))
const hasMoreReviews = computed(() => visibleReviewCount.value < reviews.value.length)
const wishlists = computed(() => profile.value?.wishlists || [])
const collections = computed(() => profile.value?.collections || [])
const threads = computed(() => profile.value?.threads || [])
const profileDrafts = ref([])
const expandedCommentDraftId = ref(null)
const draftComments = ref({})
const commentDrafts = ref({})
const likeLoading = ref(null)
const commentLoading = ref(null)
const editingCommentId = ref(null)
const editCommentContent = ref('')
const selectedDraft = ref(null)

watch(profile, (newProfile) => {
  profileDrafts.value = newProfile?.drafts ? [...newProfile.drafts] : []
}, { immediate: true })
const profileInitial = computed(() => (
  profile.value?.username?.trim().charAt(0).toUpperCase() || 'A'
))

const BOOK_COLORS = [
  '#8B5E3C', // brown
  '#315477', // navy
  '#6B705C', // olive
  '#B56576', // rose
  '#7F5539', // walnut
  '#577590', // blue gray
  '#9C6644', // terracotta
  '#4A5759', // deep gray
]

function bookVariation(bookId, offset, range) {
  return (((Number(bookId) * 37 + offset) % range) + range) % range
}

function toBookshelfBook(book) {
  return {
    id: book.id,
    title: book.title,
    author: book.author,
    coverUrl: getBookCoverUrl(book.id),
    coverImage: book.cover_image,
    globalAverageRating: Number(book.global_average_rating ?? 0),
    globalReviewCount: Number(book.global_review_count ?? 0),
    globalWishlistCount: Number(book.global_wishlist_count ?? 0),
    globalCollectionCount: Number(book.global_collection_count ?? 0),
    pageCount: 160 + bookVariation(book.id, 53, 541),
    color: BOOK_COLORS[bookVariation(book.id, 11, BOOK_COLORS.length)],
  }
}

function reviewCoverSrc(book) {
  if (!book?.id) return ''
  return book.cover_image || getBookCoverUrl(book.id)
}

const reviewBooks = computed(() => (
  reviews.value.filter((item) => item.book).map((item) => toBookshelfBook(item.book))
))
const wishlistBooks = computed(() => (
  wishlists.value.filter((item) => item.book).map((item) => toBookshelfBook(item.book))
))
const collectionBooks = computed(() => (
  collections.value.filter((item) => item.book).map((item) => toBookshelfBook(item.book))
))

const shelfCategories = computed(() => ({
  reviews: { label: '리뷰', books: reviewBooks.value },
  wishlist: { label: '위시리스트', books: wishlistBooks.value },
  collections: { label: '컬렉션', books: collectionBooks.value },
}))

const activeShelf = computed(() => (
  activeShelfCategory.value ? shelfCategories.value[activeShelfCategory.value] : null
))

function selectedShelfBooks(category) {
  const selectedIds = new Set(shelfSelections.value[category] || [])
  return shelfCategories.value[category].books.filter((book) => selectedIds.has(book.id))
}

const displayedReviewBooks = computed(() => selectedShelfBooks('reviews'))
const displayedWishlistBooks = computed(() => selectedShelfBooks('wishlist'))
const displayedCollectionBooks = computed(() => selectedShelfBooks('collections'))

function shelfStorageKey() {
  return `arctic-bookshelf:${profile.value?.id || profileUserId.value || 'me'}`
}

function bookshelfAppearanceStorageKey() {
  return `arctic-bookshelf-appearance:${profile.value?.id || profileUserId.value || 'me'}`
}

function initializeBookshelfAppearance() {
  if (!profile.value) return

  let storedAppearance = {}
  try {
    storedAppearance = JSON.parse(
      localStorage.getItem(bookshelfAppearanceStorageKey()) || '{}',
    )
  } catch {
    storedAppearance = {}
  }

  const validBackgrounds = new Set(BOOKSHELF_BACKGROUNDS.map((item) => item.image))
  const validProps = new Set(BOOKSHELF_PROPS.map((item) => item.prefix))

  bookshelfAppearance.value = {
    backgroundImage: validBackgrounds.has(storedAppearance.backgroundImage)
      ? storedAppearance.backgroundImage
      : BOOKSHELF_BACKGROUNDS[0].image,
    enabledProps: Array.isArray(storedAppearance.enabledProps)
      ? storedAppearance.enabledProps.filter((prefix) => validProps.has(prefix))
      : BOOKSHELF_PROPS.map((item) => item.prefix),
  }
}

function saveBookshelfAppearance() {
  localStorage.setItem(
    bookshelfAppearanceStorageKey(),
    JSON.stringify(bookshelfAppearance.value),
  )
}

function selectBookshelfBackground(image) {
  if (!isMyProfile.value) return
  bookshelfAppearance.value = {
    ...bookshelfAppearance.value,
    backgroundImage: image,
  }
  saveBookshelfAppearance()
}

function isBookshelfPropEnabled(prefix) {
  return bookshelfAppearance.value.enabledProps.includes(prefix)
}

function toggleBookshelfProp(prefix) {
  if (!isMyProfile.value) return

  const enabledProps = isBookshelfPropEnabled(prefix)
    ? bookshelfAppearance.value.enabledProps.filter((item) => item !== prefix)
    : [...bookshelfAppearance.value.enabledProps, prefix]

  bookshelfAppearance.value = {
    ...bookshelfAppearance.value,
    enabledProps,
  }
  saveBookshelfAppearance()
}

function initializeShelfSelections() {
  if (!profile.value) return

  let storedSelections = {}
  try {
    storedSelections = JSON.parse(localStorage.getItem(shelfStorageKey()) || '{}')
  } catch {
    storedSelections = {}
  }

  const nextSelections = {}
  Object.entries(shelfCategories.value).forEach(([category, value]) => {
    const availableIds = new Set(value.books.map((book) => book.id))
    const selectedIds = Array.isArray(storedSelections[category])
      ? storedSelections[category]
      : value.books.slice(0, MAX_SHELF_BOOKS).map((book) => book.id)

    nextSelections[category] = selectedIds
      .filter((bookId) => availableIds.has(bookId))
      .slice(0, MAX_SHELF_BOOKS)
  })
  shelfSelections.value = nextSelections
}

function openShelfSelector(category) {
  activeShelfCategory.value = category
  shelfSelectionDraft.value = [...(shelfSelections.value[category] || [])]
  shelfSelectionMessage.value = ''
}

function closeShelfSelector() {
  activeShelfCategory.value = null
  shelfSelectionDraft.value = []
  shelfSelectionMessage.value = ''
}

function isShelfBookSelected(bookId) {
  return shelfSelectionDraft.value.includes(bookId)
}

function toggleShelfBook(bookId) {
  if (!isMyProfile.value) return

  if (isShelfBookSelected(bookId)) {
    shelfSelectionDraft.value = shelfSelectionDraft.value.filter((id) => id !== bookId)
    shelfSelectionMessage.value = ''
    return
  }

  if (shelfSelectionDraft.value.length >= MAX_SHELF_BOOKS) {
    shelfSelectionMessage.value = '한 층에는 최대 30권까지 수납할 수 있어요.'
    return
  }

  shelfSelectionDraft.value = [...shelfSelectionDraft.value, bookId]
  shelfSelectionMessage.value = ''
}

function saveShelfSelection() {
  if (!activeShelfCategory.value || !isMyProfile.value) return

  shelfSelections.value = {
    ...shelfSelections.value,
    [activeShelfCategory.value]: [...shelfSelectionDraft.value],
  }
  localStorage.setItem(shelfStorageKey(), JSON.stringify(shelfSelections.value))
  closeShelfSelector()
}

watch(profile, (newProfile) => {
  if (newProfile) {
    initializeShelfSelections()
    initializeBookshelfAppearance()
  }
})

const tabs = computed(() => [
  { id: 'reviews', label: '리뷰', count: reviews.value.length },
  { id: 'wishlist', label: '위시리스트', count: wishlists.value.length },
  { id: 'collections', label: '컬렉션', count: collections.value.length },
  { id: 'threads', label: '게시글', count: threads.value.length },
  { id: 'creations', label: '창작물', count: profileDrafts.value.length },
])

function loadMoreReviews() {
  if (!hasMoreReviews.value) return
  visibleReviewCount.value = Math.min(visibleReviewCount.value + 10, reviews.value.length)
}

function stopReviewObserver() {
  if (!reviewObserver) return
  reviewObserver.disconnect()
  reviewObserver = null
}

async function observeReviewLoadMore() {
  await nextTick()
  stopReviewObserver()
  if (activeTab.value !== 'reviews' || !hasMoreReviews.value || !reviewLoadMoreTrigger.value) return
  reviewObserver = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      loadMoreReviews()
      observeReviewLoadMore()
    }
  }, { rootMargin: '280px 0px' })
  reviewObserver.observe(reviewLoadMoreTrigger.value)
}

async function toggleBookshelf() {
  isBookshelfVisible.value = !isBookshelfVisible.value
  if (!isBookshelfVisible.value) return
  await nextTick()
  librarySection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function loadProfile() {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  try {
    currentUser.value = await fetchProfile()
    profile.value = await fetchProfile(profileUserId.value)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

async function handleFollowToggle() {
  if (!profileUserId.value) return
  isFollowLoading.value = true
  try {
    const result = await toggleFollow(profileUserId.value)
    profile.value = {
      ...profile.value,
      is_following: result.is_following,
      follower_count: result.follower_count,
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isFollowLoading.value = false
  }
}

async function handleDraftLike(draft) {
  if (isMyProfile.value) return
  likeLoading.value = draft.id
  try {
    const result = await toggleDraftLike(draft.id)
    const idx = profileDrafts.value.findIndex((d) => d.id === draft.id)
    if (idx !== -1) {
      profileDrafts.value[idx] = { ...profileDrafts.value[idx], is_liked: result.is_liked, like_count: result.like_count }
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    likeLoading.value = null
  }
}

function openDraftDetail(draft) {
  selectedDraft.value = draft
}

function closeDraftDetail() {
  selectedDraft.value = null
}

async function handleDraftCommentLike(draft, comment) {
  try {
    const result = await toggleDraftCommentLike(comment.id)
    draftComments.value = {
      ...draftComments.value,
      [draft.id]: (draftComments.value[draft.id] || []).map((item) =>
        item.id === comment.id
          ? { ...item, is_liked: result.is_liked, like_count: result.like_count }
          : item
      ),
    }
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function toggleComments(draft) {
  if (expandedCommentDraftId.value === draft.id) {
    expandedCommentDraftId.value = null
    return
  }
  expandedCommentDraftId.value = draft.id
  if (draftComments.value[draft.id]) return
  try {
    draftComments.value = { ...draftComments.value, [draft.id]: await fetchDraftComments(draft.id) }
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function submitDraftComment(draft) {
  const content = (commentDrafts.value[draft.id] || '').trim()
  if (!content) return
  commentLoading.value = draft.id
  try {
    const comment = await createDraftComment(draft.id, content)
    draftComments.value = {
      ...draftComments.value,
      [draft.id]: [...(draftComments.value[draft.id] || []), comment],
    }
    commentDrafts.value = { ...commentDrafts.value, [draft.id]: '' }
    const idx = profileDrafts.value.findIndex((d) => d.id === draft.id)
    if (idx !== -1) {
      profileDrafts.value[idx] = { ...profileDrafts.value[idx], comment_count: (profileDrafts.value[idx].comment_count || 0) + 1 }
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    commentLoading.value = null
  }
}

async function handleDeleteComment(draft, commentId) {
  try {
    await deleteDraftComment(commentId)
    draftComments.value = {
      ...draftComments.value,
      [draft.id]: (draftComments.value[draft.id] || []).filter((c) => c.id !== commentId),
    }
    const idx = profileDrafts.value.findIndex((d) => d.id === draft.id)
    if (idx !== -1) {
      profileDrafts.value[idx] = { ...profileDrafts.value[idx], comment_count: Math.max(0, (profileDrafts.value[idx].comment_count || 1) - 1) }
    }
  } catch (error) {
    errorMessage.value = error.message
  }
}

function startCommentEdit(comment) {
  editingCommentId.value = comment.id
  editCommentContent.value = comment.content
}

function cancelCommentEdit() {
  editingCommentId.value = null
}

async function handleEditComment(draft, comment) {
  try {
    const updated = await updateDraftComment(comment.id, editCommentContent.value)
    draftComments.value = {
      ...draftComments.value,
      [draft.id]: (draftComments.value[draft.id] || []).map((c) =>
        c.id === comment.id ? { ...c, content: updated.content } : c
      ),
    }
    editingCommentId.value = null
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function toggleDraftPublic(draft) {
  try {
    await updateDraft(draft.id, { is_public: !draft.is_public })
    const idx = profileDrafts.value.findIndex((d) => d.id === draft.id)
    if (idx !== -1) profileDrafts.value[idx] = { ...profileDrafts.value[idx], is_public: !draft.is_public }
  } catch (error) {
    errorMessage.value = error.message
  }
}

onMounted(loadProfile)
onBeforeUnmount(stopReviewObserver)
watch(profileUserId, () => {
  activeTab.value = 'reviews'
  isBookshelfVisible.value = false
  visibleReviewCount.value = 10
  stopReviewObserver()
  closeShelfSelector()
  loadProfile()
})

watch([activeTab, reviews, visibleReviewCount], () => {
  if (activeTab.value !== 'reviews') {
    stopReviewObserver()
    return
  }
  observeReviewLoadMore()
}, { immediate: true })

watch(reviews, () => {
  visibleReviewCount.value = 10
})
</script>

<template>
  <main class="profile-page">
    <div v-if="isLoading" class="profile-header-skeleton" />
    <p v-else-if="errorMessage && !profile" class="page-error-full">{{ errorMessage }}</p>

    <template v-else-if="profile">
      <header class="profile-header">
        <div class="profile-header-inner">
          <img
            v-if="profile.profile_image"
            :src="profile.profile_image"
            :alt="profile.username"
            class="avatar"
          />
          <div v-else class="avatar avatar-fallback">{{ profileInitial }}</div>

          <div class="profile-info">
            <p class="profile-eyebrow">READER PROFILE</p>
            <h1 class="profile-username">{{ profile.username }}</h1>
            <p class="profile-bio">{{ profile.bio || '아직 소개가 없어요.' }}</p>
            <div class="genre-row">
              <span v-for="genre in preferredGenres" :key="genre.id" class="genre-tag">
                {{ genre.name }}
              </span>
            </div>
          </div>

          <div class="profile-actions">
            <RouterLink v-if="isMyProfile" to="/profile/edit" class="btn-outline">
              프로필 수정
            </RouterLink>
            <button
              v-else
              type="button"
              class="btn-follow"
              :class="{ following: profile.is_following }"
              :disabled="isFollowLoading"
              @click="handleFollowToggle"
            >
              {{ profile.is_following ? '팔로우 취소' : '팔로우' }}
            </button>
          </div>
        </div>
      </header>

      <nav class="stats-bar" aria-label="프로필 통계">
        <div class="stats-inner">
          <RouterLink :to="`${profileBasePath}/follows?tab=followers`" class="stat-item">
            <strong>{{ profile.follower_count }}</strong><span>팔로워</span>
          </RouterLink>
          <RouterLink :to="`${profileBasePath}/follows?tab=following`" class="stat-item">
            <strong>{{ profile.following_count }}</strong><span>팔로잉</span>
          </RouterLink>
          <div class="stat-item"><strong>{{ profile.review_count }}</strong><span>리뷰</span></div>
          <div class="stat-item"><strong>{{ profile.thread_count }}</strong><span>게시글</span></div>
          <div class="stat-item"><strong>{{ profile.wishlist_count }}</strong><span>위시리스트</span></div>
          <div class="stat-item"><strong>{{ profile.collection_count }}</strong><span>컬렉션</span></div>
        </div>
      </nav>

      <section v-if="isBookshelfVisible" ref="librarySection" class="library-section">
          <div class="library-inner">
            <div>
              <p class="section-eyebrow">PERSONAL LIBRARY</p>
              <h2>나의 책장</h2>
              <p>리뷰, 위시리스트, 컬렉션에 담긴 책을 한눈에 볼 수 있어요.</p>
            </div>
            <button type="button" class="library-close" @click="isBookshelfVisible = false">
              닫기
            </button>
            <div v-if="isMyProfile" class="bookshelf-customizer">
              <div class="bookshelf-setting-group">
                <div class="bookshelf-setting-heading">
                  <strong>책장 배경</strong>
                  <span>원하는 분위기를 선택하세요.</span>
                </div>
                <div class="bookshelf-background-options">
                  <button
                    v-for="background in BOOKSHELF_BACKGROUNDS"
                    :key="background.id"
                    type="button"
                    class="bookshelf-background-option"
                    :class="{
                      selected: bookshelfAppearance.backgroundImage === background.image,
                    }"
                    @click="selectBookshelfBackground(background.image)"
                  >
                    <img :src="background.image" :alt="background.label" />
                    <span>{{ background.label }}</span>
                  </button>
                </div>
              </div>

              <div class="bookshelf-setting-group">
                <div class="bookshelf-setting-heading">
                  <strong>아래 선반 소품</strong>
                  <span>보여줄 소품을 자유롭게 켜고 끌 수 있어요.</span>
                </div>
                <div class="bookshelf-prop-options">
                  <button
                    v-for="item in BOOKSHELF_PROPS"
                    :key="item.prefix"
                    type="button"
                    class="bookshelf-prop-option"
                    :class="{ active: isBookshelfPropEnabled(item.prefix) }"
                    :aria-pressed="isBookshelfPropEnabled(item.prefix)"
                    @click="toggleBookshelfProp(item.prefix)"
                  >
                    <span class="bookshelf-prop-indicator" />
                    {{ item.label }}
                  </button>
                </div>
              </div>
            </div>
            <div class="bookshelf-wrap">
              <BookshelfModel
                :review-books="displayedReviewBooks"
                :wishlist-books="displayedWishlistBooks"
                :collection-books="displayedCollectionBooks"
                :review-total="reviewBooks.length"
                :wishlist-total="wishlistBooks.length"
                :collection-total="collectionBooks.length"
                :background-image="bookshelfAppearance.backgroundImage"
                :enabled-props="bookshelfAppearance.enabledProps"
                @open-shelf="openShelfSelector"
              />
            </div>
          </div>
      </section>

      <Transition name="modal-fade">
        <div
          v-if="activeShelf"
          class="shelf-modal-backdrop"
          @click.self="closeShelfSelector"
        >
          <section class="shelf-modal" role="dialog" aria-modal="true">
            <header class="shelf-modal-header">
              <div>
                <p class="section-eyebrow">BOOKSHELF STORAGE</p>
                <h2>{{ activeShelf.label }}</h2>
                <p v-if="isMyProfile">책장에 꽂을 책을 최대 30권까지 선택하세요.</p>
                <p v-else>저장된 모든 책을 확인할 수 있어요.</p>
              </div>
              <button type="button" class="shelf-modal-close" @click="closeShelfSelector">
                닫기
              </button>
            </header>

            <div v-if="isMyProfile" class="shelf-selection-status">
              <span><strong>{{ shelfSelectionDraft.length }}</strong>/{{ MAX_SHELF_BOOKS }}권 선택</span>
              <span v-if="shelfSelectionMessage" class="shelf-selection-warning">
                {{ shelfSelectionMessage }}
              </span>
            </div>

            <div v-if="activeShelf.books.length" class="shelf-book-grid">
              <button
                v-for="book in activeShelf.books"
                :key="book.id"
                type="button"
                class="shelf-book-option"
                :class="{ selected: isShelfBookSelected(book.id), readonly: !isMyProfile }"
                @click="toggleShelfBook(book.id)"
              >
                <span class="shelf-cover-wrap">
                  <img :src="book.coverImage || book.coverUrl" :alt="book.title" />
                  <span v-if="isMyProfile" class="shelf-book-check">
                    {{ isShelfBookSelected(book.id) ? '✓' : '' }}
                  </span>
                </span>
                <strong>{{ book.title }}</strong>
                <small>{{ book.author }}</small>
              </button>
            </div>
            <p v-else class="empty-msg">저장된 책이 없습니다.</p>

            <footer v-if="isMyProfile" class="shelf-modal-footer">
              <button type="button" class="shelf-cancel-button" @click="closeShelfSelector">
                취소
              </button>
              <button type="button" class="shelf-save-button" @click="saveShelfSelection">
                선택한 책 수납하기
              </button>
            </footer>
          </section>
        </div>
      </Transition>

      <section class="content-area">
        <div class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="tab-btn"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            {{ tab.label }} <span>{{ tab.count }}</span>
          </button>
          <button
            type="button"
            class="tab-btn tab-library-btn"
            :class="{ active: isBookshelfVisible }"
            @click="toggleBookshelf"
          >
            나의 책장
          </button>
        </div>

        <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

        <div v-if="activeTab === 'reviews'" class="tab-content">
          <p v-if="reviews.length === 0" class="empty-msg">아직 작성한 리뷰가 없어요.</p>
          <div v-else class="review-list">
            <article v-for="review in visibleReviews" :key="review.id" class="review-card">
              <div class="review-book-info">
                <div class="review-cover-frame">
                  <img
                    v-if="review.book"
                    :src="reviewCoverSrc(review.book)"
                    :alt="review.book.title"
                    class="review-cover"
                    loading="lazy"
                    @error="$event.currentTarget.style.display = 'none'"
                  />
                </div>
                <div>
                  <RouterLink
                    :to="{ name: 'book-detail', params: { bookId: review.book?.id } }"
                    class="item-title"
                  >
                    {{ review.book?.title }}
                  </RouterLink>
                  <p class="item-subtitle">{{ review.book?.author }}</p>
                </div>
              </div>
              <div class="review-body">
                <p class="rating">{{ '★'.repeat(review.rating) }}<span>{{ '★'.repeat(5 - review.rating) }}</span></p>
                <p>{{ review.content }}</p>
              </div>
            </article>
          </div>
          <div v-if="hasMoreReviews" ref="reviewLoadMoreTrigger" class="review-load-more" aria-live="polite">
            리뷰 더 불러오는 중...
          </div>
        </div>

        <div v-if="activeTab === 'wishlist' || activeTab === 'collections'" class="tab-content">
          <template v-if="(activeTab === 'wishlist' ? wishlists : collections).length">
            <div class="book-grid">
              <RouterLink
                v-for="item in activeTab === 'wishlist' ? wishlists : collections"
                :key="item.id"
                :to="{ name: 'book-detail', params: { bookId: item.book?.id } }"
                class="book-card"
              >
                <img v-if="item.book?.cover_image" :src="item.book.cover_image" :alt="item.book.title" />
                <div v-else class="cover-placeholder" />
                <strong>{{ item.book?.title }}</strong>
                <span>{{ item.book?.author }}</span>
              </RouterLink>
            </div>
          </template>
          <p v-else class="empty-msg">
            {{ activeTab === 'wishlist' ? '위시리스트가 비어 있어요.' : '컬렉션이 비어 있어요.' }}
          </p>
        </div>

        <div v-if="activeTab === 'threads'" class="tab-content">
          <p v-if="threads.length === 0" class="empty-msg">아직 작성한 게시글이 없어요.</p>
          <div v-else class="thread-list">
            <RouterLink
              v-for="thread in threads"
              :key="thread.id"
              :to="{ name: 'thread-detail', params: { threadId: thread.id } }"
              class="thread-card"
            >
              <h3>{{ thread.title }}</h3>
              <p>{{ thread.content?.slice(0, 100) }}</p>
            </RouterLink>
          </div>
        </div>

        <div v-if="activeTab === 'creations'" class="tab-content">
          <p v-if="profileDrafts.length === 0" class="empty-msg">
            {{ isMyProfile ? '아직 저장한 창작물이 없어요.' : '공개된 창작물이 없어요.' }}
          </p>
          <div v-else class="creation-list">
            <article
              v-for="draft in profileDrafts"
              :key="draft.id"
              class="creation-card"
              role="button"
              tabindex="0"
              @click="openDraftDetail(draft)"
              @keydown.enter="openDraftDetail(draft)"
            >
              <div class="creation-card-header">
                <span class="creation-type-badge">{{ draft.draft_type === 'idea' ? '아이디어' : draft.draft_type === 'plot' ? '플롯' : '교정' }}</span>
                <span v-if="isMyProfile" class="creation-visibility" :class="{ public: draft.is_public }">
                  {{ draft.is_public ? '공개' : '비공개' }}
                </span>
              </div>
              <h3 class="creation-title">{{ draft.title || '제목 없음' }}</h3>
              <p v-if="draft.genre" class="creation-meta">{{ draft.genre }}<template v-if="draft.keywords"> · {{ draft.keywords }}</template></p>

              <div class="creation-card-footer">
                <button
                  v-if="!isMyProfile"
                  type="button"
                  class="btn-creation-like"
                  :class="{ liked: draft.is_liked }"
                  :disabled="likeLoading === draft.id"
                  @click.stop="handleDraftLike(draft)"
                >
                  {{ draft.is_liked ? '♥' : '♡' }} {{ draft.like_count || 0 }}
                </button>
                <span v-else class="creation-like-count">♡ {{ draft.like_count || 0 }}</span>
                <button type="button" class="btn-creation-comment" @click.stop="toggleComments(draft)">
                  댓글 {{ draft.comment_count || 0 }}
                </button>
                <button
                  v-if="isMyProfile"
                  type="button"
                  class="btn-toggle-public"
                  :class="{ public: draft.is_public }"
                  @click.stop="toggleDraftPublic(draft)"
                >
                  {{ draft.is_public ? '비공개로 전환' : '공개로 전환' }}
                </button>
              </div>

              <div v-if="expandedCommentDraftId === draft.id" class="creation-comments" @click.stop>
                <p v-if="!draftComments[draft.id]?.length" class="empty-comments">첫 댓글을 남겨보세요.</p>
                <div v-for="comment in draftComments[draft.id]" :key="comment.id" class="comment-row">
                  <RouterLink :to="`/profile/${comment.user_id}`" class="comment-author">
                    {{ comment.username }}
                  </RouterLink>
                  <template v-if="editingCommentId === comment.id">
                    <input
                      v-model="editCommentContent"
                      class="comment-input comment-edit-input"
                      @keyup.enter="handleEditComment(draft, comment)"
                    />
                    <button type="button" class="btn-comment-submit" @click="handleEditComment(draft, comment)">저장</button>
                    <button type="button" class="btn-comment-delete" @click="cancelCommentEdit">취소</button>
                  </template>
                  <template v-else>
                    <span class="comment-content">{{ comment.content }}</span>
                    <button
                      type="button"
                      class="btn-comment-like"
                      :class="{ liked: comment.is_liked }"
                      @click="handleDraftCommentLike(draft, comment)"
                    >
                      {{ comment.is_liked ? '♥' : '♡' }} {{ comment.like_count || 0 }}
                    </button>
                    <template v-if="currentUser?.id === comment.user_id">
                      <button type="button" class="btn-comment-delete" @click="startCommentEdit(comment)">수정</button>
                      <button type="button" class="btn-comment-delete" @click="handleDeleteComment(draft, comment.id)">삭제</button>
                    </template>
                  </template>
                </div>
                <div class="comment-form">
                  <input
                    v-model="commentDrafts[draft.id]"
                    class="comment-input"
                    placeholder="댓글 작성..."
                    @keyup.enter="submitDraftComment(draft)"
                  />
                  <button
                    type="button"
                    class="btn-comment-submit"
                    :disabled="commentLoading === draft.id"
                    @click="submitDraftComment(draft)"
                  >등록</button>
                </div>
              </div>
            </article>
          </div>
        </div>
      </section>

      <Transition name="modal-fade">
        <div v-if="selectedDraft" class="creation-modal-backdrop" @click.self="closeDraftDetail">
          <article class="creation-modal">
            <header class="creation-modal-header">
              <div>
                <span class="creation-type-badge">
                  {{ selectedDraft.draft_type === 'idea' ? '아이디어' : selectedDraft.draft_type === 'plot' ? '플롯' : '교정' }}
                </span>
                <h2 class="creation-modal-title">{{ selectedDraft.title || '제목 없음' }}</h2>
                <p v-if="selectedDraft.genre" class="creation-meta">
                  {{ selectedDraft.genre }}<template v-if="selectedDraft.keywords"> · {{ selectedDraft.keywords }}</template>
                </p>
              </div>
              <button type="button" class="creation-modal-close" @click="closeDraftDetail">닫기</button>
            </header>

            <div v-if="selectedDraft.draft_type === 'idea'" class="creation-modal-body">
              <div v-for="(idea, index) in selectedDraft.content.ideas" :key="index" class="creation-modal-section">
                <span class="modal-section-label">{{ String(index + 1).padStart(2, '0') }}</span>
                <p>{{ idea }}</p>
              </div>
            </div>

            <div v-else-if="selectedDraft.draft_type === 'plot'" class="creation-modal-body">
              <div
                v-for="(label, key) in {
                  intro: '기 — 도입',
                  development: '승 — 전개',
                  turn: '전 — 전환',
                  conclusion: '결 — 결말',
                }"
                :key="key"
                class="creation-modal-section"
              >
                <span class="modal-section-label">{{ label }}</span>
                <p>{{ selectedDraft.content[key] }}</p>
              </div>
            </div>

            <div v-else-if="selectedDraft.draft_type === 'correction'" class="creation-modal-body">
              <div class="creation-modal-section">
                <span class="modal-section-label">원문</span>
                <p>{{ selectedDraft.content.original }}</p>
              </div>
              <div class="creation-modal-section">
                <span class="modal-section-label">교정문</span>
                <p>{{ selectedDraft.content.corrected }}</p>
              </div>
              <div v-if="selectedDraft.content.explanation" class="creation-modal-section">
                <span class="modal-section-label">개선 포인트</span>
                <p>{{ selectedDraft.content.explanation }}</p>
              </div>
            </div>
          </article>
        </div>
      </Transition>
    </template>
  </main>
</template>

<style scoped>
.profile-page { min-height: calc(100vh - 64px); background: #f4eedf; color: #262019; }
.profile-header { background: #173b38; padding: 52px 32px 60px; }
.profile-header-inner { max-width: 1080px; margin: auto; display: flex; align-items: center; gap: 30px; }
.avatar { width: 100px; height: 100px; flex: none; border-radius: 50%; object-fit: cover; border: 3px solid rgb(244 238 223 / 24%); }
.avatar-fallback { display: grid; place-items: center; background: rgb(244 238 223 / 14%); color: #f4eedf; font-family: serif; font-size: 38px; }
.profile-info { min-width: 0; flex: 1; }
.profile-eyebrow, .section-eyebrow { margin: 0; font-size: 11px; font-weight: 700; color: #b9aa91; }
.profile-username { margin: 7px 0; color: #fffaf0; font-family: serif; font-size: 34px; font-weight: 400; }
.profile-bio { margin: 0 0 15px; color: rgb(244 238 223 / 70%); line-height: 1.7; }
.genre-row { display: flex; flex-wrap: wrap; gap: 7px; }
.genre-tag { border: 1px solid rgb(244 238 223 / 22%); border-radius: 999px; padding: 4px 12px; color: rgb(244 238 223 / 82%); font-size: 12px; }
.profile-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 9px; }
.btn-outline, .btn-follow { min-height: 42px; border-radius: 999px; padding: 0 20px; font: inherit; font-size: 13px; cursor: pointer; }
.btn-outline, .btn-follow.following { border: 1px solid rgb(244 238 223 / 34%); background: transparent; color: #f4eedf; text-decoration: none; display: inline-flex; align-items: center; }
.btn-follow { border: 1px solid #f4eedf; background: #f4eedf; color: #173b38; font-weight: 700; }
.stats-bar { border-bottom: 1px solid rgb(38 32 25 / 10%); background: #fffaf0; }
.stats-inner { max-width: 1080px; margin: auto; display: grid; grid-template-columns: repeat(6, 1fr); }
.stat-item { display: flex; flex-direction: column; align-items: center; padding: 18px 10px; border-right: 1px solid rgb(38 32 25 / 8%); color: inherit; text-decoration: none; }
.stat-item:last-child { border-right: 0; }
.stat-item strong { font-family: serif; font-size: 23px; font-weight: 400; }
.stat-item span { margin-top: 3px; color: #958873; font-size: 12px; }
.library-section { border-bottom: 1px solid #cfc2ad; background: #e8decc; padding: 45px 24px 60px; }
.library-inner { position: relative; max-width: 1080px; margin: auto; }
.library-inner h2 { margin: 7px 0; font-family: serif; font-size: 34px; font-weight: 400; }
.library-inner > div > p:last-child { color: #786b58; font-size: 14px; }
.library-close { position: absolute; top: 0; right: 0; border: 0; background: transparent; color: #655846; cursor: pointer; }
.bookshelf-customizer { display: grid; grid-template-columns: minmax(220px, .8fr) minmax(0, 1.7fr); gap: 18px; margin-top: 26px; }
.bookshelf-setting-group { border: 1px solid rgb(77 61 42 / 14%); border-radius: 10px; background: rgb(255 250 240 / 58%); padding: 18px; }
.bookshelf-setting-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.bookshelf-setting-heading strong { color: #3c3328; font-family: serif; font-size: 17px; font-weight: 600; }
.bookshelf-setting-heading span { color: #93836c; font-size: 11px; }
.bookshelf-background-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.bookshelf-background-option { overflow: hidden; border: 2px solid transparent; border-radius: 8px; background: #fffaf0; padding: 4px 4px 7px; color: #716655; font: inherit; font-size: 11px; cursor: pointer; transition: border-color .18s ease, transform .18s ease; }
.bookshelf-background-option:hover { transform: translateY(-1px); }
.bookshelf-background-option.selected { border-color: #173b38; color: #173b38; font-weight: 700; }
.bookshelf-background-option img { display: block; width: 100%; aspect-ratio: 4 / 3; margin-bottom: 6px; border-radius: 4px; object-fit: cover; }
.bookshelf-prop-options { display: flex; flex-wrap: wrap; gap: 8px; }
.bookshelf-prop-option { display: inline-flex; min-height: 34px; align-items: center; gap: 7px; border: 1px solid #cbbda7; border-radius: 999px; background: transparent; padding: 0 12px; color: #756955; font: inherit; font-size: 12px; cursor: pointer; transition: border-color .15s ease, background .15s ease, color .15s ease; }
.bookshelf-prop-option.active { border-color: #526c62; background: #e1e9e2; color: #173b38; font-weight: 700; }
.bookshelf-prop-indicator { width: 7px; height: 7px; border-radius: 50%; background: #c1b39d; box-shadow: 0 0 0 2px rgb(193 179 157 / 20%); }
.bookshelf-prop-option.active .bookshelf-prop-indicator { background: #2f6656; box-shadow: 0 0 0 2px rgb(47 102 86 / 18%); }
.bookshelf-wrap { width: min(980px, 100%); aspect-ratio: 6 / 7; margin: 28px auto 0; }
.shelf-modal-backdrop { position: fixed; inset: 0; z-index: 110; display: grid; place-items: center; padding: 28px; background: rgb(23 18 12 / 72%); backdrop-filter: blur(8px); }
.shelf-modal { display: flex; width: min(980px, 100%); max-height: 88vh; flex-direction: column; overflow: hidden; border: 1px solid rgb(38 32 25 / 14%); border-radius: 12px; background: #fbf7ee; box-shadow: 0 24px 70px -30px #17120c; }
.shelf-modal-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; border-bottom: 1px solid rgb(38 32 25 / 10%); padding: 24px 28px 20px; }
.shelf-modal-header h2 { margin: 7px 0 4px; font-family: serif; font-size: 28px; font-weight: 400; }
.shelf-modal-header p:last-child { margin: 0; color: #786b58; font-size: 13px; }
.shelf-modal-close { border: 1px solid rgb(38 32 25 / 14%); border-radius: 999px; background: transparent; padding: 7px 14px; color: #716655; font: inherit; font-size: 13px; cursor: pointer; }
.shelf-selection-status { display: flex; min-height: 42px; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid rgb(38 32 25 / 8%); background: #f4eedf; padding: 9px 28px; color: #716655; font-size: 13px; }
.shelf-selection-status strong { color: #173b38; font-size: 17px; }
.shelf-selection-warning { color: #a65432; }
.shelf-book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(125px, 1fr)); gap: 22px 16px; overflow-y: auto; padding: 24px 28px 30px; }
.shelf-book-option { min-width: 0; border: 0; background: transparent; padding: 0; color: #262019; text-align: left; cursor: pointer; }
.shelf-book-option.readonly { cursor: default; }
.shelf-cover-wrap { position: relative; display: block; overflow: hidden; aspect-ratio: 2 / 3; margin-bottom: 10px; border: 3px solid transparent; border-radius: 7px; background: #ddd1b9; transition: border-color 0.15s, transform 0.15s; }
.shelf-book-option:not(.readonly):hover .shelf-cover-wrap { transform: translateY(-2px); }
.shelf-book-option.selected .shelf-cover-wrap { border-color: #173b38; }
.shelf-cover-wrap img { width: 100%; height: 100%; object-fit: cover; }
.shelf-book-check { position: absolute; top: 7px; right: 7px; display: grid; width: 24px; height: 24px; place-items: center; border: 1px solid rgb(23 59 56 / 55%); border-radius: 50%; background: rgb(255 250 240 / 90%); color: #173b38; font-size: 14px; font-weight: 800; }
.shelf-book-option.selected .shelf-book-check { background: #173b38; color: #fffaf0; }
.shelf-book-option strong, .shelf-book-option small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.shelf-book-option strong { font-family: serif; font-size: 14px; font-weight: 500; }
.shelf-book-option small { margin-top: 4px; color: #958873; font-size: 11px; }
.shelf-modal-footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid rgb(38 32 25 / 10%); background: #fffaf0; padding: 16px 28px; }
.shelf-cancel-button, .shelf-save-button { min-height: 40px; border-radius: 999px; padding: 0 18px; font: inherit; font-size: 13px; cursor: pointer; }
.shelf-cancel-button { border: 1px solid rgb(38 32 25 / 18%); background: transparent; color: #716655; }
.shelf-save-button { border: 1px solid #173b38; background: #173b38; color: #f4eedf; font-weight: 700; }
.content-area { max-width: 1080px; margin: auto; padding: 0 32px 80px; }
.tab-bar { display: flex; overflow-x: auto; border-bottom: 1px solid rgb(38 32 25 / 12%); }
.tab-btn { flex: none; border: 0; border-bottom: 2px solid transparent; background: transparent; padding: 18px 22px; color: #938671; font: inherit; cursor: pointer; }
.tab-btn span { margin-left: 5px; font-size: 11px; }
.tab-btn.active { border-bottom-color: #173b38; color: #173b38; font-weight: 700; }
.tab-library-btn { margin-left: auto; color: #6c5f4c; }
.tab-library-btn.active { background: rgb(23 59 56 / 7%); }
.tab-content { padding-top: 32px; }
.empty-msg { padding: 65px 0; text-align: center; color: #958873; }
.review-list, .thread-list { display: grid; gap: 14px; }
.review-card { display: grid; grid-template-columns: minmax(190px, 240px) 1fr; gap: 22px; border: 1px solid rgb(38 32 25 / 10%); border-radius: 8px; background: #fbf7ee; padding: 22px; }
.review-book-info { display: flex; gap: 13px; min-width: 0; }
.review-cover-frame { width: 58px; height: 87px; flex: 0 0 58px; overflow: hidden; border-radius: 5px; background: linear-gradient(135deg, #ded2bc, #c8b99f); box-shadow: 0 5px 14px -10px #33291f; }
.review-cover { display: block; width: 100%; height: 100%; object-fit: cover; }
.item-title { color: #262019; font-family: serif; font-size: 17px; text-decoration: none; }
.item-subtitle { margin-top: 5px; color: #958873; font-size: 12px; }
.review-body { border-left: 1px solid rgb(38 32 25 / 10%); padding-left: 22px; color: #51483c; line-height: 1.75; }
.rating { margin: 0 0 9px; color: #aa8034; letter-spacing: 2px; }
.rating span { color: #d7cbb4; }
.review-load-more { padding: 24px 0 4px; text-align: center; color: #958873; font-size: 13px; }
.book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(145px, 1fr)); gap: 26px 18px; }
.book-card { color: inherit; text-decoration: none; }
.book-card img, .cover-placeholder { width: 100%; aspect-ratio: 2 / 3; margin-bottom: 10px; border-radius: 5px; background: #ddd1b9; object-fit: cover; box-shadow: 0 6px 16px -10px #33291f; }
.book-card strong, .book-card span { display: block; }
.book-card strong { font-family: serif; font-size: 15px; font-weight: 400; }
.book-card span { margin-top: 4px; color: #958873; font-size: 12px; }
.thread-card { display: block; border: 1px solid rgb(38 32 25 / 10%); border-radius: 8px; background: #fbf7ee; padding: 21px 24px; color: inherit; text-decoration: none; }
.thread-card h3 { margin: 0 0 8px; font-family: serif; font-size: 20px; font-weight: 400; }
.thread-card p { margin: 0; color: #716655; line-height: 1.7; }
.page-error { border-left: 3px solid #b06a3c; background: rgb(176 106 60 / 8%); padding: 14px 18px; color: #9b5631; }
.page-error-full { padding: 80px; text-align: center; color: #b06a3c; }
.profile-header-skeleton { height: 220px; background: #ded2bc; animation: pulse 1.5s infinite; }
.creation-list { display: grid; gap: 14px; }
.creation-card { border: 1px solid rgb(38 32 25 / 10%); border-radius: 8px; background: #fbf7ee; padding: 20px 24px; cursor: pointer; transition: box-shadow 0.15s, transform 0.12s; }
.creation-card:hover { box-shadow: 0 6px 18px -10px rgb(38 32 25 / 35%); transform: translateY(-1px); }
.creation-card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.creation-type-badge { border: 1px solid #c9a86a; border-radius: 4px; padding: 2px 8px; color: #8a6b30; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; }
.creation-visibility { font-size: 11px; color: #958873; }
.creation-visibility.public { color: #2a6040; }
.creation-title { margin: 0 0 6px; font-family: 'Newsreader', serif; font-size: 18px; font-weight: 400; color: #262019; }
.creation-meta { margin: 0 0 14px; color: #716655; font-size: 13px; }
.btn-toggle-public { border: 1px solid #958873; border-radius: 999px; background: transparent; padding: 4px 14px; color: #716655; font: inherit; font-size: 12px; cursor: pointer; }
.btn-toggle-public.public { border-color: #2a6040; color: #2a6040; }
.creation-card-footer { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
.btn-creation-like { border: 1px solid #c9a86a; border-radius: 999px; background: transparent; padding: 4px 12px; color: #8a6b30; font: inherit; font-size: 12px; cursor: pointer; }
.btn-creation-like.liked { background: #c9a86a; color: #fff; }
.creation-like-count { font-size: 12px; color: #958873; }
.btn-creation-comment { border: 1px solid #b8ad9a; border-radius: 999px; background: transparent; padding: 4px 12px; color: #716655; font: inherit; font-size: 12px; cursor: pointer; }
.creation-comments { border-top: 1px solid rgb(38 32 25 / 10%); margin-top: 14px; padding-top: 14px; }
.empty-comments { font-size: 13px; color: #b8ad9a; margin: 0 0 10px; }
.comment-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 9px; font-size: 13px; }
.comment-author { color: #173b38; font-weight: 700; text-decoration: none; flex-shrink: 0; }
.comment-author:hover { text-decoration: underline; }
.comment-content { color: #4a4337; flex: 1; line-height: 1.6; }
.btn-comment-delete { border: 0; background: transparent; color: #b06a3c; font-size: 11px; cursor: pointer; flex-shrink: 0; }
.btn-comment-like { border: 0; background: transparent; color: #958873; font-size: 11px; cursor: pointer; flex-shrink: 0; }
.btn-comment-like.liked { color: #b06a3c; font-weight: 700; }
.comment-form { display: flex; gap: 8px; margin-top: 10px; }
.comment-input { flex: 1; border: 1px solid rgb(38 32 25 / 15%); border-radius: 8px; background: #fffaf0; padding: 7px 12px; font: inherit; font-size: 13px; color: #262019; }
.btn-comment-submit { border: 0; border-radius: 8px; background: #173b38; padding: 7px 16px; color: #f4eedf; font: inherit; font-size: 13px; cursor: pointer; }
.creation-modal-backdrop { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 28px; background: rgb(23 18 12 / 72%); backdrop-filter: blur(8px); }
.creation-modal { width: min(760px, 100%); max-height: 86vh; overflow-y: auto; border: 1px solid rgb(38 32 25 / 14%); border-radius: 10px; background: #fbf7ee; padding: 28px 32px; box-shadow: 0 20px 60px -28px #17120c; }
.creation-modal-header { display: flex; justify-content: space-between; gap: 18px; border-bottom: 1px solid rgb(38 32 25 / 10%); padding-bottom: 18px; margin-bottom: 22px; }
.creation-modal-title { margin: 10px 0 6px; font-family: 'Newsreader', serif; font-size: 28px; font-weight: 400; line-height: 1.25; color: #262019; }
.creation-modal-close { align-self: flex-start; border: 1px solid rgb(38 32 25 / 14%); border-radius: 999px; background: transparent; padding: 7px 14px; color: #716655; font: inherit; font-size: 13px; cursor: pointer; }
.creation-modal-body { display: grid; gap: 18px; }
.creation-modal-section { border-left: 2px solid #c9a86a; padding-left: 16px; }
.modal-section-label { display: block; margin-bottom: 6px; color: #8a6b30; font-size: 12px; font-weight: 700; }
.creation-modal-section p { margin: 0; color: #4a4337; line-height: 1.85; white-space: pre-wrap; }
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.18s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
@keyframes pulse { 50% { opacity: .55; } }
@media (max-width: 960px) {
  .profile-header { padding-inline: 26px; }
  .profile-header-inner { gap: 22px; }
  .bookshelf-customizer { grid-template-columns: 1fr; }
  .bookshelf-background-options { grid-template-columns: repeat(2, minmax(0, 210px)); }
  .library-section { padding-inline: 20px; }
  .bookshelf-wrap { width: min(840px, 100%); }
}

@media (max-width: 720px) {
  .profile-header { padding: 38px 22px; }
  .profile-header-inner { align-items: flex-start; flex-direction: column; }
  .avatar { width: 82px; height: 82px; }
  .profile-username { font-size: 30px; }
  .profile-actions { justify-content: flex-start; }
  .stats-inner { grid-template-columns: repeat(3, 1fr); }
  .stat-item { border-bottom: 1px solid rgb(38 32 25 / 8%); }
  .library-section { padding: 32px 14px 42px; }
  .library-inner h2 { font-size: 29px; }
  .bookshelf-setting-group { padding: 15px; }
  .bookshelf-background-options { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bookshelf-prop-options { gap: 7px; }
  .bookshelf-prop-option { min-height: 32px; padding-inline: 10px; font-size: 11px; }
  .bookshelf-wrap { margin-top: 20px; }
  .content-area { padding-inline: 20px; }
  .review-card { grid-template-columns: 1fr; }
  .review-body { border-left: 0; border-top: 1px solid rgb(38 32 25 / 10%); padding: 18px 0 0; }
  .shelf-modal-backdrop { padding: 12px; }
  .shelf-modal { max-height: 92vh; }
  .shelf-modal-header, .shelf-book-grid { padding-inline: 18px; }
  .shelf-selection-status { align-items: flex-start; flex-direction: column; padding-inline: 18px; }
  .shelf-book-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px 10px; }
  .shelf-modal-footer { padding-inline: 18px; }
  .bookshelf-setting-heading { align-items: flex-start; flex-direction: column; gap: 4px; }
}

@media (max-width: 480px) {
  .profile-header { padding: 30px 18px 34px; }
  .profile-header-inner { gap: 18px; }
  .profile-bio { font-size: 14px; }
  .stat-item { padding: 14px 6px; }
  .stat-item strong { font-size: 20px; }
  .stat-item span { font-size: 10px; }
  .bookshelf-customizer { gap: 12px; margin-top: 20px; }
  .bookshelf-setting-heading span { line-height: 1.5; }
  .bookshelf-prop-option { flex: 1 1 calc(50% - 7px); justify-content: flex-start; }
  .shelf-book-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .shelf-modal-footer { display: grid; grid-template-columns: 1fr 1.5fr; }
  .shelf-cancel-button, .shelf-save-button { width: 100%; padding-inline: 10px; }
}
</style>
