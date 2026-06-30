<script setup>
/**
 * BookDetailView.vue — Arctic 디자인 적용 완성본
 *
 * [api/books.js에 추가 필요한 함수들]
 *   export function updateReview(reviewId, payload) {
 *     return apiRequest(`/books/reviews/${reviewId}/`, { method: 'PATCH', body: JSON.stringify(payload) })
 *   }
 *   export function deleteReview(reviewId) {
 *     return apiRequest(`/books/reviews/${reviewId}/`, { method: 'DELETE' })
 *   }
 *   export function toggleWishlist(bookId) {
 *     return apiRequest(`/books/${bookId}/wishlist/`, { method: 'POST' })
 *   }
 *
 * [신규] api/ai.js 생성 필요 — vue-output/api/ai.js 참고
 */
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { createReview, deleteReview, fetchBook, materializeBook, toggleCollection, toggleWishlist, updateReview } from '@/api/books'
import { analyzeReviews } from '@/api/ai'
import { isAuthenticated } from '@/api/client'

const route = useRoute()
const router = useRouter()

const book = ref(null)
const isLoading = ref(false)
const isTransient = ref(false)
const isDescExpanded = ref(false)
const errorMessage = ref('')

// 리뷰 작성
const reviewContent = ref('')
const reviewRating = ref(5)
const hoverRating = ref(0)
const isReviewSaving = ref(false)

// 리뷰 정렬
const reviewOrdering = ref('latest')

// 리뷰 수정
const editingReviewId = ref(null)
const editContent = ref('')
const editRating = ref(5)
const editHoverRating = ref(0)
const isEditSaving = ref(false)

// 위시리스트 / 컬렉션
const isWishlisted = ref(false)
const isWishlistLoading = ref(false)
const isCollected = ref(false)
const isCollectionLoading = ref(false)

// AI 감상 분석
const aiResult = ref(null)
const isAnalyzing = ref(false)

const isLoggedIn = computed(() => isAuthenticated())
const canAnalyze = computed(() => (book.value?.reviews?.length ?? 0) >= 3)
const sortedReviews = computed(() => {
  const reviews = [...(book.value?.reviews || [])]
  if (reviewOrdering.value === 'rating') {
    return reviews.sort((a, b) =>
      b.rating !== a.rating ? b.rating - a.rating : new Date(b.created_at) - new Date(a.created_at),
    )
  }
  return reviews.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

async function loadBook() {
  const transient = window.history.state?.transientBook
  if (transient) {
    book.value = { ...transient, reviews: [] }
    isTransient.value = true
    isWishlisted.value = transient.is_wishlisted ?? false
    isCollected.value = transient.is_collected ?? false
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  try {
    book.value = await fetchBook(route.params.bookId)
    isWishlisted.value = book.value?.is_wishlisted ?? false
    isCollected.value = book.value?.is_collected ?? false
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

async function ensurePersisted() {
  if (!isTransient.value) return
  const materialized = await materializeBook(book.value)
  book.value = materialized
  isWishlisted.value = materialized.is_wishlisted ?? false
  isCollected.value = materialized.is_collected ?? false
  isTransient.value = false
}

async function handleReviewSubmit() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  isReviewSaving.value = true
  errorMessage.value = ''
  try {
    await ensurePersisted()
    await createReview(book.value.id, {
      content: reviewContent.value,
      rating: Number(reviewRating.value),
    })
    reviewContent.value = ''
    reviewRating.value = 5
    await loadBook()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isReviewSaving.value = false
  }
}

function startEdit(review) {
  editingReviewId.value = review.id
  editContent.value = review.content
  editRating.value = review.rating
}

function cancelEdit() {
  editingReviewId.value = null
}

async function handleEditSave(review) {
  isEditSaving.value = true
  try {
    await updateReview(book.value.id, review.id, { content: editContent.value, rating: editRating.value })
    await loadBook()
    editingReviewId.value = null
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isEditSaving.value = false
  }
}

async function handleReviewDelete(reviewId) {
  if (!confirm('리뷰를 삭제할까요?')) return
  try {
    await deleteReview(book.value.id, reviewId)
    await loadBook()
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function handleWishlistToggle() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  isWishlistLoading.value = true
  try {
    await ensurePersisted()
    const result = await toggleWishlist(book.value.id)
    isWishlisted.value = result.is_wishlisted
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isWishlistLoading.value = false
  }
}

async function handleCollectionToggle() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  isCollectionLoading.value = true
  errorMessage.value = ''
  try {
    await ensurePersisted()
    const result = await toggleCollection(book.value.id)
    isCollected.value = result.is_collected
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isCollectionLoading.value = false
  }
}

async function handleAnalyzeReviews() {
  isAnalyzing.value = true
  aiResult.value = null
  try {
    const result = await analyzeReviews(route.params.bookId)
    const positive = Math.round(result.positive_ratio * 100)
    const negative = Math.round(result.negative_ratio * 100)
    aiResult.value = {
      positive,
      negative,
      neutral: 100 - positive - negative,
      keywords: result.keywords,
      summary: result.summary,
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isAnalyzing.value = false
  }
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

onMounted(loadBook)
</script>

<template>
  <div class="detail-page">
    <div class="detail-inner">
      <!-- 로딩 -->
      <div v-if="isLoading" class="skeleton-wrap">
        <div class="sk-cover"></div>
        <div class="sk-info">
          <div class="sk-line w70"></div>
          <div class="sk-line w40"></div>
          <div class="sk-line w90"></div>
          <div class="sk-line w60"></div>
        </div>
      </div>

      <!-- 에러 -->
      <p v-else-if="errorMessage && !book" class="page-error">{{ errorMessage }}</p>

      <!-- 메인 콘텐츠 -->
      <div v-else-if="book">
        <!-- ── 책 헤더 ── -->
        <div class="book-header">
          <!-- 표지 -->
          <div class="cover-wrap">
            <img
              v-if="book.cover_image"
              :src="book.cover_image"
              :alt="book.title"
              class="book-cover"
            />
            <div v-else class="book-cover cover-placeholder"></div>
          </div>

          <!-- 책 정보 -->
          <div class="book-info">
            <div class="book-meta-top">
              <span v-for="genre in book.genres || []" :key="genre.id" class="genre-tag">{{
                genre.name
              }}</span>
            </div>

            <h1 class="book-title">{{ book.title }}</h1>

            <div class="action-btns">
              <button
                class="wishlist-text-btn"
                :class="{ active: isWishlisted }"
                :disabled="isWishlistLoading"
                type="button"
                @click="handleWishlistToggle"
              >
                {{ isWishlisted ? '♥ 위시리스트 제거' : '♡ 위시리스트' }}
              </button>
              <button
                class="collection-text-btn"
                :class="{ active: isCollected }"
                :disabled="isCollectionLoading"
                type="button"
                @click="handleCollectionToggle"
              >
                {{ isCollected ? '■ 책장에서 제거' : '□ 내 책장에 추가' }}
              </button>
            </div>
            <p class="book-author">{{ book.author }}</p>
            <p class="book-publisher">
              {{ book.publisher }} · {{ book.published_date?.slice(0, 4) }}
            </p>

            <div class="rating-row">
              <span class="rating-stars">
                <span
                  v-for="n in 5"
                  :key="n"
                  class="star"
                  :class="{ filled: n <= Math.round(book.average_rating || 0) }"
                  >★</span
                >
              </span>
              <span class="rating-value">{{
                book.average_rating ? Number(book.average_rating).toFixed(1) : '–'
              }}</span>
              <span class="rating-count">· 리뷰 {{ book.reviews?.length ?? 0 }}개</span>
            </div>

            <div v-if="book.description" class="desc-wrap">
              <p class="book-desc" :class="{ expanded: isDescExpanded }">{{ book.description }}</p>
              <button class="desc-toggle" type="button" @click="isDescExpanded = !isDescExpanded">
                {{ isDescExpanded ? '접기' : '더 보기' }}
              </button>
            </div>

            <!-- AI 감상 분석 -->
            <div class="ai-section">
              <button
                class="btn-ai"
                type="button"
                :disabled="!canAnalyze || isAnalyzing"
                :title="!canAnalyze ? '리뷰가 3개 이상이어야 분석할 수 있어요' : ''"
                @click="handleAnalyzeReviews"
              >
                <span class="ai-dot"></span>
                {{ isAnalyzing ? '분석 중...' : 'AI 감상 분석' }}
              </button>
              <span v-if="!canAnalyze" class="ai-hint">리뷰 3개 이상 필요</span>
            </div>

            <!-- AI 결과 -->
            <div v-if="aiResult" class="ai-result">
              <div class="ai-result-header">
                <span class="ai-dot"></span>
                <span>AI 감상 분석 결과</span>
              </div>
              <div class="sentiment-bar-wrap">
                <div class="sentiment-bar">
                  <div class="bar-pos" :style="{ width: aiResult.positive + '%' }"></div>
                  <div class="bar-neu" :style="{ width: aiResult.neutral + '%' }"></div>
                  <div class="bar-neg" :style="{ width: aiResult.negative + '%' }"></div>
                </div>
                <div class="sentiment-legend">
                  <span><i class="dot pos"></i> 긍정 {{ aiResult.positive }}%</span>
                  <span><i class="dot neu"></i> 중립 {{ aiResult.neutral }}%</span>
                  <span><i class="dot neg"></i> 부정 {{ aiResult.negative }}%</span>
                </div>
              </div>
              <div class="keyword-row">
                <span v-for="kw in aiResult.keywords" :key="kw" class="kw-chip"># {{ kw }}</span>
              </div>
              <p class="ai-summary">{{ aiResult.summary }}</p>
            </div>
          </div>
        </div>

        <!-- 전체 에러 -->
        <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

        <!-- ── 리뷰 쓰기 ── -->
        <section class="review-write-section">
          <h2 class="section-heading">리뷰 쓰기</h2>

          <form v-if="isLoggedIn" class="review-form" @submit.prevent="handleReviewSubmit">
            <div class="star-input-wrap">
              <span class="form-label">별점</span>
              <div class="star-input">
                <button
                  v-for="n in 5"
                  :key="n"
                  type="button"
                  class="star-btn"
                  :class="{ filled: n <= (hoverRating || reviewRating) }"
                  @mouseenter="hoverRating = n"
                  @mouseleave="hoverRating = 0"
                  @click="reviewRating = n"
                >
                  ★
                </button>
              </div>
              <span class="star-label">{{ reviewRating }}점</span>
            </div>

            <div class="form-field">
              <label class="form-label" for="review-content">감상</label>
              <textarea
                id="review-content"
                v-model="reviewContent"
                class="review-textarea"
                placeholder="이 책에 대한 감상을 자유롭게 써 주세요."
                rows="4"
              ></textarea>
            </div>

            <button
              class="btn-submit"
              type="submit"
              :disabled="isReviewSaving || !reviewContent.trim()"
            >
              {{ isReviewSaving ? '저장 중...' : '리뷰 등록' }}
            </button>
          </form>

          <button v-else class="btn-login-prompt" type="button" @click="goLogin">
            로그인하고 리뷰 쓰기 →
          </button>
        </section>

        <!-- ── 독자 리뷰 ── -->
        <section class="reviews-section">
          <div class="reviews-header">
            <h2 class="section-heading">
              독자 리뷰 <span class="review-count">{{ sortedReviews.length }}</span>
            </h2>
            <div class="ordering-tabs">
              <button
                :class="['ordering-btn', { active: reviewOrdering === 'latest' }]"
                type="button"
                @click="reviewOrdering = 'latest'"
              >
                최신순
              </button>
              <button
                :class="['ordering-btn', { active: reviewOrdering === 'rating' }]"
                type="button"
                @click="reviewOrdering = 'rating'"
              >
                평점순
              </button>
            </div>
          </div>

          <p v-if="sortedReviews.length === 0" class="reviews-empty">
            아직 리뷰가 없어요. 첫 번째 감상을 남겨보세요.
          </p>

          <div v-else class="review-list">
            <div v-for="review in sortedReviews" :key="review.id" class="review-card">
              <!-- 수정 모드 -->
              <template v-if="editingReviewId === review.id">
                <div class="edit-star-row">
                  <button
                    v-for="n in 5"
                    :key="n"
                    type="button"
                    class="star-btn"
                    :class="{ filled: n <= (editHoverRating || editRating) }"
                    @mouseenter="editHoverRating = n"
                    @mouseleave="editHoverRating = 0"
                    @click="editRating = n"
                  >
                    ★
                  </button>
                </div>
                <textarea v-model="editContent" class="review-textarea" rows="3"></textarea>
                <div class="edit-actions">
                  <button class="btn-cancel" type="button" @click="cancelEdit">취소</button>
                  <button
                    class="btn-save"
                    type="button"
                    :disabled="isEditSaving"
                    @click="handleEditSave(review)"
                  >
                    {{ isEditSaving ? '저장 중...' : '저장' }}
                  </button>
                </div>
              </template>

              <!-- 일반 모드 -->
              <template v-else>
                <div class="review-card-header">
                  <RouterLink :to="`/profile/${review.user_id}`" class="reviewer-info">
                    <span class="reviewer-avatar">
                      <img
                        v-if="review.profile_image"
                        :src="review.profile_image"
                        :alt="`${review.username} profile`"
                      />
                      <span v-else>{{ review.username?.[0]?.toUpperCase() }}</span>
                    </span>
                    <div>
                      <span class="reviewer-name">{{ review.username }}</span>
                      <span class="review-date">{{ formatDate(review.created_at) }}</span>
                    </div>
                  </RouterLink>
                  <div class="review-card-right">
                    <div class="review-stars">
                      <span
                        v-for="n in 5"
                        :key="n"
                        class="star sm"
                        :class="{ filled: n <= review.rating }"
                        >★</span
                      >
                    </div>
                    <div v-if="review.is_mine" class="review-actions">
                      <button class="btn-text-sm" type="button" @click="startEdit(review)">
                        수정
                      </button>
                      <button
                        class="btn-text-sm danger"
                        type="button"
                        @click="handleReviewDelete(review.id)"
                      >
                        삭제
                      </button>
                    </div>
                  </div>
                </div>

                <p class="review-content">{{ review.content }}</p>
              </template>
            </div>
          </div>
        </section>
      </div>
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

.detail-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 52px 0 100px;
}

.detail-inner {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 32px;
}

/* 로딩 스켈레톤 */
.skeleton-wrap {
  display: flex;
  gap: 48px;
  animation: shimmer 1.6s ease-in-out infinite;
}
.sk-cover {
  width: 200px;
  min-height: 300px;
  border-radius: 10px;
  background: #e7dcc4;
  flex-shrink: 0;
}
.sk-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 10px;
}
.sk-line {
  height: 14px;
  border-radius: 6px;
  background: #e7dcc4;
}
.sk-line.w40 {
  width: 40%;
}
.sk-line.w60 {
  width: 60%;
}
.sk-line.w70 {
  width: 70%;
  height: 22px;
}
.sk-line.w90 {
  width: 90%;
}

/* ── 책 헤더 ── */
.book-header {
  display: flex;
  gap: 52px;
  align-items: flex-start;
  margin-bottom: 60px;
}

.cover-wrap {
  position: relative;
  flex-shrink: 0;
}

.book-cover {
  width: 200px;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  object-fit: cover;
  display: block;
  box-shadow: 0 12px 36px -10px rgba(40, 32, 20, 0.36);
}

.cover-placeholder {
  background: repeating-linear-gradient(135deg, #e7dcc4 0 8px, #e0d3b6 8px 16px);
}

/* 책 정보 */
.book-info {
  flex: 1;
  min-width: 0;
}

.book-meta-top {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.genre-tag {
  font-size: 12px;
  color: #1e3a3a;
  background: rgba(30, 58, 58, 0.08);
  border-radius: 999px;
  padding: 4px 12px;
}

.book-title {
  font-family: 'Newsreader', serif;
  font-size: 32px;
  font-weight: 400;
  line-height: 1.25;
  margin: 0 0 10px;
  letter-spacing: -0.5px;
}

.book-author {
  font-size: 17px;
  color: #4a4337;
  margin: 0 0 6px;
}

.book-publisher {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 12px;
  color: #9c9079;
  margin: 0 0 18px;
  letter-spacing: 0.5px;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.rating-stars {
  display: flex;
  gap: 2px;
}

.star {
  font-size: 18px;
  color: #d8ccb2;
  transition: color 0.1s;
}
.star.filled {
  color: #b08a3c;
}
.star.sm {
  font-size: 14px;
}

.rating-value {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 18px;
  font-weight: 500;
  color: #b08a3c;
}

.rating-count {
  font-size: 13px;
  color: #9c9079;
}

/* 액션 버튼 묶음 */
.action-btns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

/* 위시리스트 텍스트 버튼 */
.wishlist-text-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  border: 1.5px solid rgba(40, 32, 20, 0.2);
  border-radius: 999px;
  padding: 9px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 700;
  color: #6b6253;
  cursor: pointer;
  transition: all 0.15s;
}
.wishlist-text-btn:hover {
  border-color: #b06a3c;
  color: #b06a3c;
}
.wishlist-text-btn.active {
  background: rgba(176, 106, 60, 0.08);
  border-color: #b06a3c;
  color: #b06a3c;
}
.wishlist-text-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.collection-text-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  border: 1.5px solid rgba(40, 32, 20, 0.2);
  border-radius: 999px;
  padding: 9px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 700;
  color: #6b6253;
  cursor: pointer;
  transition: all 0.15s;
}
.collection-text-btn:hover {
  border-color: #1e3a3a;
  color: #1e3a3a;
}
.collection-text-btn.active {
  background: rgba(30, 58, 58, 0.08);
  border-color: #1e3a3a;
  color: #1e3a3a;
}
.collection-text-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 설명 */
.desc-wrap {
  margin-bottom: 24px;
}

.book-desc {
  font-size: 15px;
  line-height: 1.85;
  color: #5c5444;
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-desc.expanded {
  -webkit-line-clamp: unset;
  overflow: visible;
}

.desc-toggle {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: #1e3a3a;
  cursor: pointer;
  font-weight: 700;
}

/* AI 버튼 */
.ai-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.btn-ai {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fbf7ee;
  border: 1px solid rgba(30, 58, 58, 0.25);
  border-radius: 999px;
  padding: 10px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  color: #1e3a3a;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-ai:hover:not(:disabled) {
  background: rgba(30, 58, 58, 0.06);
}
.btn-ai:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ai-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #1e3a3a;
  flex-shrink: 0;
}

.ai-hint {
  font-size: 12px;
  color: #b8ad9a;
}

/* AI 결과 */
.ai-result {
  background: #fffdf8;
  border: 1px solid #e7dcc4;
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 8px;
}

.ai-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #1e3a3a;
  margin-bottom: 16px;
}

.sentiment-bar-wrap {
  margin-bottom: 16px;
}

.sentiment-bar {
  height: 10px;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  margin-bottom: 10px;
}

.bar-pos {
  background: #3f6b5f;
}
.bar-neu {
  background: #c8b78d;
}
.bar-neg {
  background: #b06a3c;
}

.sentiment-legend {
  display: flex;
  gap: 18px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  color: #6b6253;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 5px;
}
.dot.pos {
  background: #3f6b5f;
}
.dot.neu {
  background: #c8b78d;
}
.dot.neg {
  background: #b06a3c;
}

.keyword-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.kw-chip {
  background: #ede3cf;
  color: #4a4337;
  font-size: 13px;
  padding: 5px 13px;
  border-radius: 999px;
}

.ai-summary {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-size: 16px;
  line-height: 1.7;
  color: #3a342a;
  margin: 0;
  border-left: 2px solid #1e3a3a;
  padding-left: 14px;
}

/* ── 리뷰 쓰기 ── */
.review-write-section {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.08);
  border-radius: 14px;
  padding: 32px 36px;
  margin-bottom: 48px;
}

.section-heading {
  font-family: 'Newsreader', serif;
  font-size: 22px;
  font-weight: 400;
  margin: 0 0 24px;
  color: #262019;
}

.review-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.star-input-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
}

.form-label {
  font-size: 13px;
  font-weight: 700;
  color: #6b6253;
  letter-spacing: 0.3px;
}

.star-input {
  display: flex;
  gap: 4px;
}

.star-btn {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 26px;
  color: #d8ccb2;
  cursor: pointer;
  transition:
    color 0.1s,
    transform 0.1s;
  line-height: 1;
}

.star-btn.filled {
  color: #b08a3c;
}
.star-btn:hover {
  transform: scale(1.15);
}

.star-label {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 13px;
  color: #b08a3c;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.review-textarea {
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
  background: #fffdf8;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #262019;
  outline: none;
  resize: vertical;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
  box-sizing: border-box;
}

.review-textarea:focus {
  border-color: #1e3a3a;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}

.review-textarea::placeholder {
  color: #c2b8a4;
}

.btn-submit {
  align-self: flex-end;
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 12px 30px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-submit:hover {
  background: #152a2a;
}
.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-login-prompt {
  width: 100%;
  background: transparent;
  border: 1.5px dashed rgba(30, 58, 58, 0.3);
  border-radius: 10px;
  padding: 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #1e3a3a;
  cursor: pointer;
  transition: background 0.15s;
  font-weight: 700;
}

.btn-login-prompt:hover {
  background: rgba(30, 58, 58, 0.04);
}

/* ── 리뷰 목록 ── */
.reviews-section {
}

.reviews-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.review-count {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 15px;
  color: #9c9079;
  margin-left: 8px;
}

.ordering-tabs {
  display: flex;
  gap: 6px;
}

.ordering-btn {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 7px 16px;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
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

.reviews-empty {
  text-align: center;
  font-size: 15px;
  color: #9c9079;
  padding: 48px 0;
  font-style: italic;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-card {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.08);
  border-radius: 14px;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.reviewer-info {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.15s;
}
.reviewer-info:hover {
  opacity: 0.75;
}

.reviewer-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #1e3a3a;
  color: #f4eedf;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

.reviewer-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.reviewer-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #262019;
}
.review-date {
  display: block;
  font-size: 12px;
  color: #9c9079;
  margin-top: 2px;
}

.review-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.review-stars {
  display: flex;
  gap: 2px;
}
.review-actions {
  display: flex;
  gap: 8px;
}

.btn-text-sm {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 12px;
  color: #9c9079;
  cursor: pointer;
  transition: color 0.15s;
}

.btn-text-sm:hover {
  color: #4a4337;
}
.btn-text-sm.danger:hover {
  color: #b06a3c;
}

.review-content {
  font-size: 15px;
  line-height: 1.85;
  color: #4a4337;
  margin: 0;
}

.review-card-footer {
  display: flex;
  align-items: center;
  padding-top: 4px;
  border-top: 1px solid rgba(40, 32, 20, 0.07);
}

.btn-like {
  background: transparent;
  border: none;
  padding: 4px 0;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: #9c9079;
  cursor: pointer;
  transition: color 0.15s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn-like:hover {
  color: #b06a3c;
}
.btn-like.liked {
  color: #b06a3c;
  font-weight: 700;
}
.btn-like:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 수정 모드 */
.edit-star-row {
  display: flex;
  gap: 4px;
}
.edit-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 8px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  color: #6b6253;
  cursor: pointer;
}

.btn-save {
  background: #1e3a3a;
  border: none;
  border-radius: 999px;
  padding: 8px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  color: #f4eedf;
  cursor: pointer;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 에러 */
.page-error {
  font-size: 14px;
  color: #b06a3c;
  padding: 14px 18px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 10px;
  border-left: 3px solid #b06a3c;
  margin-bottom: 24px;
}
</style>
