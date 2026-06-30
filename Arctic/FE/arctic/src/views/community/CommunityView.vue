<script setup>
/**
 * CommunityView.vue — Arctic 디자인 적용 완성본
 * 스레드 목록 + 작성 버튼 + 댓글 수/좋아요 표시
 */
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createComment, fetchThread, fetchThreads, toggleThreadLike } from '@/api/community'
import { searchUsers } from '@/api/accounts'

const router = useRouter()

const threads = ref([])
const currentPage = ref(1)
const totalCount = ref(0)
const pageSize = 10
const maxVisiblePages = 5
const isLoading = ref(false)
const errorMessage = ref('')
const threadSearchInput = ref('')
const threadSearchType = ref('everything')
const appliedThreadQuery = ref('')
const appliedThreadSearchType = ref('all')
const userSearchQuery = ref('')
const userSearchResults = ref([])
const userSearchLoading = ref(false)
const isUserOnlySearch = ref(false)
const activeCommentThreadId = ref(null)
const commentDrafts = ref({})
const commentErrors = ref({})
const savingCommentId = ref(null)
const likingThreadId = ref(null)

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize))
const visiblePages = computed(() => {
  const half = Math.floor(maxVisiblePages / 2)
  let groupStart = Math.max(currentPage.value - half, 1)
  let groupEnd = Math.min(groupStart + maxVisiblePages - 1, totalPages.value)

  groupStart = Math.max(groupEnd - maxVisiblePages + 1, 1)

  return Array.from(
    { length: Math.max(groupEnd - groupStart + 1, 0) },
    (_, index) => groupStart + index,
  )
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return '방금 전'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

async function loadThreads(page = 1) {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchThreads({
      page,
      query: appliedThreadQuery.value,
      searchBy: appliedThreadSearchType.value,
    })
    const items = Array.isArray(data) ? data : data.results ?? []

    threads.value = items.map((thread) => ({
      ...thread,
      is_liked: thread.is_liked ?? false,
      comments: thread.comments ?? [],
      is_detail_loaded: Boolean(thread.comments),
    }))
    currentPage.value = page
    totalCount.value = Array.isArray(data) ? items.length : data.count ?? 0
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

async function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  await loadThreads(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function handleSearch() {
  const q = threadSearchInput.value.trim()
  appliedThreadQuery.value = q

  if (threadSearchType.value === 'users') {
    isUserOnlySearch.value = true
    userSearchQuery.value = q
    threads.value = []
    totalCount.value = 0
    await handleUserSearch()
  } else if (threadSearchType.value === 'everything') {
    isUserOnlySearch.value = false
    userSearchQuery.value = q
    appliedThreadSearchType.value = 'all'
    await Promise.all([loadThreads(1), handleUserSearch()])
  } else {
    isUserOnlySearch.value = false
    userSearchResults.value = []
    appliedThreadSearchType.value = threadSearchType.value
    await loadThreads(1)
  }
}

async function clearThreadSearch() {
  threadSearchInput.value = ''
  appliedThreadQuery.value = ''
  appliedThreadSearchType.value = 'all'
  isUserOnlySearch.value = false
  userSearchQuery.value = ''
  userSearchResults.value = []
  await loadThreads(1)
}

function updateThread(threadId, patch) {
  threads.value = threads.value.map((thread) =>
    thread.id === threadId ? { ...thread, ...patch } : thread,
  )
}

async function handleLike(thread) {
  likingThreadId.value = thread.id

  try {
    const result = await toggleThreadLike(thread.id)
    updateThread(thread.id, {
      is_liked: result.is_liked,
      like_count: result.like_count,
    })
  } catch (error) {
    commentErrors.value = {
      ...commentErrors.value,
      [thread.id]: error.message,
    }
  } finally {
    likingThreadId.value = null
  }
}

async function toggleComments(thread) {
  const isOpening = activeCommentThreadId.value !== thread.id
  activeCommentThreadId.value = isOpening ? thread.id : null

  if (!isOpening || thread.is_detail_loaded) {
    return
  }

  try {
    const detail = await fetchThread(thread.id)
    updateThread(thread.id, {
      comments: detail.comments ?? [],
      is_liked: detail.is_liked ?? thread.is_liked,
      like_count: detail.like_count ?? thread.like_count,
      is_detail_loaded: true,
    })
  } catch (error) {
    commentErrors.value = {
      ...commentErrors.value,
      [thread.id]: error.message,
    }
  }
}

async function submitComment(thread) {
  const content = (commentDrafts.value[thread.id] || '').trim()
  if (!content) {
    return
  }

  savingCommentId.value = thread.id
  commentErrors.value = {
    ...commentErrors.value,
    [thread.id]: '',
  }

  try {
    const comment = await createComment(thread.id, { content })
    updateThread(thread.id, {
      comments: [...(thread.comments ?? []), comment],
      comment_count: (thread.comment_count ?? 0) + 1,
      is_detail_loaded: true,
    })
    commentDrafts.value = {
      ...commentDrafts.value,
      [thread.id]: '',
    }
  } catch (error) {
    commentErrors.value = {
      ...commentErrors.value,
      [thread.id]: error.message,
    }
  } finally {
    savingCommentId.value = null
  }
}

async function handleUserSearch() {
  const q = userSearchQuery.value.trim()
  if (q.length < 2) {
    userSearchResults.value = []
    return
  }
  userSearchLoading.value = true
  try {
    userSearchResults.value = await searchUsers(q)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    userSearchLoading.value = false
  }
}

onMounted(loadThreads)
</script>

<template>
  <div class="community-page">
    <div class="community-inner">
      <!-- 헤더 -->
      <div class="page-header">
        <div>
          <h1 class="page-title">커뮤니티</h1>
          <p class="page-sub">책에 대한 이야기를 나눠요.</p>
        </div>
        <RouterLink :to="{ name: 'thread-create' }" class="btn-create"> + 스레드 쓰기 </RouterLink>
      </div>

      <!-- 커뮤니티 검색 (게시글 + 사용자) -->
      <form class="thread-search-section" @submit.prevent="handleSearch">
        <select v-model="threadSearchType" class="thread-search-select" aria-label="검색 범위">
          <option value="everything">전체</option>
          <option value="all">제목+내용</option>
          <option value="title">제목</option>
          <option value="content">내용</option>
          <option value="users">사용자</option>
        </select>
        <input
          v-model="threadSearchInput"
          type="search"
          class="thread-search-input"
          placeholder="커뮤니티 글 / 사용자 검색"
        />
        <button type="submit" class="btn-thread-search">검색</button>
      </form>

      <p v-if="appliedThreadQuery" class="thread-search-summary">
        ‘{{ appliedThreadQuery }}’ 검색 결과 {{ totalCount }}개
      </p>

      <!-- 사용자 검색 결과 -->
      <div v-if="userSearchResults.length" class="user-search-results" style="margin-bottom: 20px;">
        <RouterLink
          v-for="user in userSearchResults"
          :key="user.id"
          :to="`/profile/${user.id}`"
          class="user-result-card"
        >
          <span class="user-result-avatar">
            <img v-if="user.profile_image" :src="user.profile_image" :alt="user.username" />
            <span v-else>{{ user.username?.[0]?.toUpperCase() }}</span>
          </span>
          <span class="user-result-name">{{ user.username }}</span>
        </RouterLink>
      </div>
      <p
        v-else-if="isUserOnlySearch && !userSearchLoading && appliedThreadQuery.length >= 2"
        class="user-search-empty"
      >
        검색 결과가 없어요.
      </p>

      <!-- 에러 -->
      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <template v-if="!isUserOnlySearch">
      <!-- 로딩 스켈레톤 -->
      <div v-if="isLoading" class="thread-list">
        <div v-for="n in 5" :key="n" class="thread-card skeleton">
          <div class="sk-line w60 mb10"></div>
          <div class="sk-line w90 mb8"></div>
          <div class="sk-line w40"></div>
        </div>
      </div>

      <!-- 빈 상태 -->
      <div v-else-if="threads.length === 0" class="empty-state">
        <p class="empty-title">
          {{ appliedThreadQuery ? '검색 결과가 없어요.' : '아직 스레드가 없어요.' }}
        </p>
        <p class="empty-sub">
          {{ appliedThreadQuery ? '다른 검색어로 다시 찾아보세요.' : '첫 번째 이야기를 시작해 보세요.' }}
        </p>
        <RouterLink v-if="!appliedThreadQuery" :to="{ name: 'thread-create' }" class="btn-create">
          스레드 쓰기
        </RouterLink>
      </div>

      <!-- 스레드 목록 -->
      <template v-else>
        <div class="thread-list">
          <div
            v-for="thread in threads"
            :key="thread.id"
            class="thread-card"
            role="link"
            tabindex="0"
            @click="router.push({ name: 'thread-detail', params: { threadId: thread.id } })"
            @keydown.enter="router.push({ name: 'thread-detail', params: { threadId: thread.id } })"
          >
          <!-- 상단: 작성자 + 날짜 -->
          <div class="thread-meta">
            <RouterLink :to="`/profile/${thread.user_id}`" class="thread-author-row" @click.stop>
              <span class="author-avatar">
                <img
                  v-if="thread.profile_image"
                  :src="thread.profile_image"
                  :alt="`${thread.username} profile`"
                />
                <span v-else>{{ thread.username?.[0]?.toUpperCase() }}</span>
              </span>
              <span class="author-name">{{ thread.username }}</span>
            </RouterLink>
            <span class="thread-date">{{ formatDate(thread.created_at) }}</span>
          </div>

          <!-- 제목 + 본문 미리보기 -->
          <h2 class="thread-title">{{ thread.title }}</h2>
          <p class="thread-preview">
            {{ thread.content?.slice(0, 120) }}{{ thread.content?.length > 120 ? '…' : '' }}
          </p>

          <!-- 하단: 좋아요 + 댓글 -->
          <div class="thread-footer">
            <span class="thread-stat">♡ {{ thread.like_count }}</span>
            <span class="thread-stat">💬 {{ thread.comment_count }}</span>
          </div>
          </div>
        </div>

        <nav v-if="totalPages > 1" class="pagination" aria-label="커뮤니티 페이지">
          <button
            type="button"
            class="page-button page-move"
            :disabled="currentPage === 1"
            @click="changePage(currentPage - 1)"
          >
            이전
          </button>
          <button
            v-for="page in visiblePages"
            :key="page"
            type="button"
            class="page-button"
            :class="{ active: page === currentPage }"
            :aria-current="page === currentPage ? 'page' : undefined"
            @click="changePage(page)"
          >
            {{ page }}
          </button>
          <button
            type="button"
            class="page-button page-move"
            :disabled="currentPage === totalPages"
            @click="changePage(currentPage + 1)"
          >
            다음
          </button>
        </nav>
      </template>
      </template>
    </div>
  </div>
</template>

<style scoped>
@keyframes shimmer {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

.community-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 52px 0 80px;
}

.community-inner {
  max-width: 780px;
  margin: 0 auto;
  padding: 0 32px;
}

/* 헤더 */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 40px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-family: 'Newsreader', serif;
  font-size: 36px;
  font-weight: 400;
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}

.page-sub {
  font-size: 14.5px;
  color: #9c9079;
  margin: 0;
}

.btn-create {
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 11px 24px;
  font-family: 'Gowun Batang', serif;
  font-size: 14.5px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.btn-create:hover {
  background: #152a2a;
}

/* 커뮤니티 글 검색 */
.thread-search-section {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr) auto auto;
  gap: 10px;
  margin-bottom: 12px;
}
.thread-search-select,
.thread-search-input {
  min-width: 0;
  border: 1px solid rgba(40, 32, 20, 0.18);
  border-radius: 10px;
  background: #fbf7ee;
  padding: 11px 14px;
  color: #262019;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
}
.thread-search-select:focus,
.thread-search-input:focus {
  outline: none;
  border-color: #c9a86a;
}
.btn-thread-search,
.btn-thread-clear {
  border-radius: 10px;
  padding: 10px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-thread-search {
  border: 1px solid #173b38;
  background: #173b38;
  color: #f4eedf;
}
.btn-thread-clear {
  border: 1px solid rgba(40, 32, 20, 0.18);
  background: transparent;
  color: #6e6454;
}
.thread-search-summary {
  margin: 0 0 24px;
  color: #8e816d;
  font-size: 13px;
}

/* 에러 */
.page-error {
  font-size: 14px;
  color: #b06a3c;
  padding: 14px 18px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 10px;
  border-left: 3px solid #b06a3c;
}

/* 빈 상태 */
.empty-state {
  text-align: center;
  padding: 80px 24px;
}
.empty-title {
  font-family: 'Newsreader', serif;
  font-size: 22px;
  color: #4a4337;
  margin: 0 0 8px;
}
.empty-sub {
  font-size: 14px;
  color: #9c9079;
  margin: 0 0 28px;
}

/* 스레드 목록 */
.thread-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.thread-card {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.1);
  border-radius: 14px;
  padding: 24px 28px;
  text-decoration: none;
  color: inherit;
  display: block;
  transition:
    box-shadow 0.15s,
    transform 0.12s;
}
.thread-card:hover {
  box-shadow: 0 6px 22px -8px rgba(40, 32, 20, 0.22);
  transform: translateY(-1px);
}

/* 메타 */
.thread-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.thread-author-row {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.15s;
}
.thread-author-row:hover {
  opacity: 0.75;
}
.author-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #1e3a3a;
  color: #f4eedf;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.author-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.author-name {
  font-size: 14px;
  font-weight: 700;
  color: #3a342a;
}
.thread-date {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11.5px;
  color: #b8ad9a;
}

/* 본문 */
.thread-title {
  font-family: 'Newsreader', serif;
  font-size: 20px;
  font-weight: 400;
  color: #262019;
  margin: 0 0 10px;
  line-height: 1.35;
}
.thread-preview {
  font-size: 14.5px;
  line-height: 1.8;
  color: #5c5444;
  margin: 0 0 16px;
  text-wrap: pretty;
}

/* 푸터 */
.thread-footer {
  display: flex;
  gap: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(40, 32, 20, 0.07);
}
.thread-stat {
  font-size: 13px;
  color: #9c9079;
}

/* 페이지네이션 */
.pagination {
  display: flex;
  justify-content: center;
  gap: 7px;
  margin-top: 34px;
}
.page-button {
  display: grid;
  min-width: 38px;
  height: 38px;
  place-items: center;
  border: 1px solid rgba(40, 32, 20, 0.16);
  border-radius: 9px;
  background: #fbf7ee;
  color: #5c5444;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 13px;
  cursor: pointer;
}
.page-button:hover:not(:disabled),
.page-button.active {
  border-color: #173b38;
  background: #173b38;
  color: #f4eedf;
}
.page-button:disabled {
  opacity: 0.35;
  cursor: default;
}
.page-move {
  padding-inline: 13px;
  font-family: 'Gowun Batang', serif;
}

/* 사용자 검색 */
.user-search-section { margin-bottom: 36px; }
.user-search-row { display: flex; gap: 10px; }
.user-search-input { flex: 1; border: 1px solid rgba(40, 32, 20, 0.18); border-radius: 10px; background: #fbf7ee; padding: 10px 16px; font-family: 'Gowun Batang', serif; font-size: 14px; color: #262019; }
.user-search-input:focus { outline: none; border-color: #c9a86a; }
.btn-user-search { border: 1px solid #173b38; border-radius: 10px; background: #173b38; padding: 10px 20px; color: #f4eedf; font-family: 'Gowun Batang', serif; font-size: 14px; cursor: pointer; white-space: nowrap; }
.btn-user-search:disabled { opacity: 0.6; cursor: default; }
.user-search-results { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.user-result-card { display: flex; align-items: center; gap: 9px; border: 1px solid rgba(40, 32, 20, 0.1); border-radius: 10px; background: #fbf7ee; padding: 10px 16px; text-decoration: none; color: inherit; transition: box-shadow 0.15s; }
.user-result-card:hover { box-shadow: 0 4px 12px -6px rgba(40, 32, 20, 0.2); }
.user-result-avatar { width: 34px; height: 34px; border-radius: 50%; background: #1e3a3a; color: #f4eedf; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; overflow: hidden; flex-shrink: 0; }
.user-result-avatar img { width: 100%; height: 100%; object-fit: cover; }
.user-result-name { font-size: 14px; font-weight: 700; color: #3a342a; }
.user-search-empty { margin-top: 12px; font-size: 13px; color: #9c9079; }

/* 스켈레톤 */
.skeleton {
  animation: shimmer 1.6s ease-in-out infinite;
}
.sk-line {
  height: 13px;
  border-radius: 6px;
  background: #e7dcc4;
}
.w40 {
  width: 40%;
}
.w60 {
  width: 60%;
}
.w90 {
  width: 90%;
}
.mb8 {
  margin-bottom: 8px;
}
.mb10 {
  margin-bottom: 10px;
}

@media (max-width: 640px) {
  .community-inner {
    padding: 0 18px;
  }
  .thread-search-section {
    grid-template-columns: 110px minmax(0, 1fr);
  }
  .btn-thread-clear,
  .btn-thread-search {
    width: 100%;
  }
  .page-move {
    padding-inline: 9px;
  }
}
</style>
