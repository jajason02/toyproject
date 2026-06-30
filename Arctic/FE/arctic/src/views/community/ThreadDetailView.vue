<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createComment,
  deleteComment,
  deleteThread,
  fetchThread,
  toggleCommentLike,
  toggleThreadLike,
  updateComment,
  updateThread,
} from '@/api/community'
import { isAuthenticated } from '@/api/client'

const route = useRoute()
const router = useRouter()

const thread = ref(null)
const commentContent = ref('')
const commentErrorMessage = ref('')
const isLoading = ref(false)
const isCommentSaving = ref(false)
const isThreadLikeLoading = ref(false)
const loadingCommentLikeId = ref(null)
const errorMessage = ref('')
const isLikeLoading = ref(false)

const isEditingThread = ref(false)
const editThreadTitle = ref('')
const editThreadContent = ref('')
const isThreadEditSaving = ref(false)

const editingCommentId = ref(null)
const editCommentContent = ref('')
const isCommentEditSaving = ref(false)

const isLoggedIn = computed(() => isAuthenticated())

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

async function loadThread() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    thread.value = await fetchThread(route.params.threadId)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

function goLogin() {
  router.push({
    name: 'login',
    query: { redirect: route.fullPath },
  })
}

async function handleLike() {
  if (!isLoggedIn.value) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  isLikeLoading.value = true
  try {
    const result = await toggleThreadLike(route.params.threadId)
    thread.value = { ...thread.value, is_liked: result.is_liked, like_count: result.like_count }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLikeLoading.value = false
  }
}

async function handleCommentSubmit() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }

  if (!commentContent.value.trim()) {
    commentErrorMessage.value = '댓글 내용을 입력해주세요.'
    return
  }

  isCommentSaving.value = true
  errorMessage.value = ''
  commentErrorMessage.value = ''

  try {
    await createComment(route.params.threadId, {
      content: commentContent.value.trim(),
    })
    commentContent.value = ''
    await loadThread()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isCommentSaving.value = false
  }
}

async function handleCommentLike(comment) {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }

  loadingCommentLikeId.value = comment.id
  errorMessage.value = ''

  try {
    const result = await toggleCommentLike(route.params.threadId, comment.id)
    comment.is_liked = result.is_liked
    comment.like_count = result.like_count
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loadingCommentLikeId.value = null
  }
}
async function handleCommentDelete(commentId) {
  if (!confirm('댓글을 삭제할까요?')) return
  try {
    await deleteComment(route.params.threadId, commentId)
    await loadThread()
  } catch (error) {
    errorMessage.value = error.message
  }
}

function startThreadEdit() {
  editThreadTitle.value = thread.value.title
  editThreadContent.value = thread.value.content
  isEditingThread.value = true
}

function cancelThreadEdit() {
  isEditingThread.value = false
}

async function handleThreadEditSave() {
  isThreadEditSaving.value = true
  try {
    await updateThread(route.params.threadId, {
      title: editThreadTitle.value,
      content: editThreadContent.value,
    })
    await loadThread()
    isEditingThread.value = false
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isThreadEditSaving.value = false
  }
}

async function handleThreadDelete() {
  if (!confirm('스레드를 삭제할까요?')) return
  try {
    await deleteThread(route.params.threadId)
    router.push({ name: 'community' })
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

async function handleCommentEditSave(comment) {
  isCommentEditSaving.value = true
  try {
    await updateComment(route.params.threadId, comment.id, { content: editCommentContent.value })
    await loadThread()
    editingCommentId.value = null
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isCommentEditSaving.value = false
  }
}

onMounted(loadThread)
</script>

<template>
  <div class="thread-detail-page">
    <div class="thread-detail-inner">
      <RouterLink :to="{ name: 'community' }" class="back-link">← 커뮤니티</RouterLink>

      <div v-if="isLoading" class="skeleton-wrap">
        <div class="sk-line w50 mb16"></div>
        <div class="sk-line w90 mb8"></div>
        <div class="sk-line w80"></div>
      </div>

      <p v-else-if="errorMessage && !thread" class="page-error">{{ errorMessage }}</p>

      <template v-else-if="thread">
        <!-- 스레드 본문 -->
        <article class="thread-article">
          <div class="thread-meta">
            <RouterLink :to="`/profile/${thread.user_id}`" class="author-link">
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

          <template v-if="isEditingThread">
            <input v-model="editThreadTitle" class="edit-thread-title" type="text" />
            <textarea v-model="editThreadContent" class="edit-thread-content" rows="6"></textarea>
            <div class="edit-thread-actions">
              <button class="btn-cancel" type="button" @click="cancelThreadEdit">취소</button>
              <button class="btn-save" type="button" :disabled="isThreadEditSaving" @click="handleThreadEditSave">
                {{ isThreadEditSaving ? '저장 중...' : '저장' }}
              </button>
            </div>
          </template>
          <template v-else>
            <h1 class="thread-title">{{ thread.title }}</h1>
            <p class="thread-content">{{ thread.content }}</p>
          </template>

          <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

          <div class="thread-footer">
            <button
              class="btn-like"
              :class="{ liked: thread.is_liked }"
              type="button"
              :disabled="isLikeLoading"
              @click="handleLike"
            >
              {{ thread.is_liked ? '♥' : '♡' }} {{ thread.like_count }}
            </button>
            <span class="comment-count">댓글 {{ thread.comments?.length ?? 0 }}</span>
            <div v-if="thread.is_mine && !isEditingThread" class="thread-mine-actions">
              <button class="btn-text-sm" type="button" @click="startThreadEdit">수정</button>
              <button class="btn-text-sm danger" type="button" @click="handleThreadDelete">삭제</button>
            </div>
          </div>
        </article>

        <!-- 댓글 목록 -->
        <section class="comments-section">
          <h2 class="comments-heading">댓글 {{ thread.comments?.length ?? 0 }}</h2>

          <p v-if="thread.comments?.length === 0" class="comments-empty">
            아직 댓글이 없어요. 첫 번째 댓글을 남겨보세요.
          </p>

          <div v-else class="comment-list">
            <div v-for="comment in thread.comments" :key="comment.id" class="comment-card">
              <div class="comment-header">
                <RouterLink :to="`/profile/${comment.user_id}`" class="comment-author-link">
                  <span class="comment-avatar">
                    <img
                      v-if="comment.profile_image"
                      :src="comment.profile_image"
                      :alt="`${comment.username} profile`"
                    />
                    <span v-else>{{ comment.username?.[0]?.toUpperCase() }}</span>
                  </span>
                  <span class="comment-username">{{ comment.username }}</span>
                </RouterLink>
                <div class="comment-right">
                  <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                  <template v-if="comment.is_mine && editingCommentId !== comment.id">
                    <button class="btn-text-sm" type="button" @click="startCommentEdit(comment)">수정</button>
                    <button class="btn-text-sm danger" type="button" @click="handleCommentDelete(comment.id)">삭제</button>
                  </template>
                </div>
              </div>
              <template v-if="editingCommentId === comment.id">
                <textarea v-model="editCommentContent" class="comment-textarea" rows="3"></textarea>
                <div class="edit-comment-actions">
                  <button class="btn-cancel" type="button" @click="cancelCommentEdit">취소</button>
                  <button class="btn-save" type="button" :disabled="isCommentEditSaving" @click="handleCommentEditSave(comment)">
                    {{ isCommentEditSaving ? '저장 중...' : '저장' }}
                  </button>
                </div>
              </template>
              <p v-else class="comment-content">{{ comment.content }}</p>
            </div>
          </div>

          <!-- 댓글 입력 -->
          <form v-if="isLoggedIn" class="comment-form" @submit.prevent="handleCommentSubmit">
            <textarea
              v-model="commentContent"
              class="comment-textarea"
              placeholder="댓글을 남겨보세요."
              rows="3"
            ></textarea>
            <button
              class="btn-comment-submit"
              type="submit"
              :disabled="isCommentSaving || !commentContent.trim()"
            >
              {{ isCommentSaving ? '등록 중...' : '댓글 등록' }}
            </button>
          </form>
          <button
            v-else
            class="btn-login-prompt"
            type="button"
            @click="router.push({ name: 'login' })"
          >
            로그인하고 댓글 쓰기 →
          </button>
        </section>
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

.thread-detail-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 52px 0 100px;
}

.thread-detail-inner {
  max-width: 780px;
  margin: 0 auto;
  padding: 0 32px;
}

.back-link {
  display: inline-block;
  font-size: 14px;
  color: #9c9079;
  text-decoration: none;
  margin-bottom: 28px;
  transition: color 0.15s;
}
.back-link:hover {
  color: #1e3a3a;
}

/* 스켈레톤 */
.skeleton-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: shimmer 1.6s ease-in-out infinite;
}
.sk-line {
  height: 14px;
  border-radius: 6px;
  background: #e7dcc4;
}
.w50 {
  width: 50%;
}
.w80 {
  width: 80%;
}
.w90 {
  width: 90%;
}
.mb8 {
  margin-bottom: 8px;
}
.mb16 {
  margin-bottom: 16px;
}

/* 본문 */
.thread-article {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.1);
  border-radius: 16px;
  padding: 36px 40px;
  margin-bottom: 32px;
}

.thread-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.author-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.15s;
}
.author-link:hover {
  opacity: 0.75;
}

.author-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #1e3a3a;
  color: #f4eedf;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.author-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-name {
  font-size: 15px;
  font-weight: 700;
  color: #262019;
}
.thread-date {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11.5px;
  color: #b8ad9a;
}

.thread-title {
  font-family: 'Newsreader', serif;
  font-size: 28px;
  font-weight: 400;
  color: #262019;
  margin: 0 0 20px;
  line-height: 1.35;
  letter-spacing: -0.3px;
}

.thread-content {
  font-size: 16px;
  line-height: 1.9;
  color: #4a4337;
  margin: 0 0 28px;
  white-space: pre-wrap;
  text-wrap: pretty;
}

.thread-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid rgba(40, 32, 20, 0.08);
}

.btn-like {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 8px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  color: #6b6253;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-like:hover {
  border-color: #b06a3c;
  color: #b06a3c;
}
.btn-like.liked {
  background: rgba(176, 106, 60, 0.08);
  border-color: #b06a3c;
  color: #b06a3c;
  font-weight: 700;
}
.btn-like:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.comment-count {
  font-size: 14px;
  color: #9c9079;
}

/* 댓글 */
.comments-section {
}

.comments-heading {
  font-family: 'Newsreader', serif;
  font-size: 20px;
  font-weight: 400;
  margin: 0 0 20px;
  color: #262019;
}

.comments-empty {
  font-size: 14px;
  color: #9c9079;
  font-style: italic;
  margin: 0 0 24px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.comment-card {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.08);
  border-radius: 12px;
  padding: 18px 22px;
}

.comment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.comment-author-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.15s;
}
.comment-author-link:hover {
  opacity: 0.75;
}

.comment-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1e3a3a;
  color: #f4eedf;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.comment-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.comment-username {
  font-size: 13px;
  font-weight: 700;
  color: #262019;
}

.comment-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.comment-date {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  color: #b8ad9a;
}

.btn-delete-comment {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 12px;
  color: #b8ad9a;
  cursor: pointer;
  transition: color 0.15s;
}
.btn-delete-comment:hover {
  color: #b06a3c;
}

.comment-content {
  font-size: 14.5px;
  line-height: 1.8;
  color: #4a4337;
  margin: 0;
  white-space: pre-wrap;
}

/* 댓글 입력 */
.comment-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-textarea {
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
  background: #fbf7ee;
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
.comment-textarea:focus {
  border-color: #1e3a3a;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}
.comment-textarea::placeholder {
  color: #c2b8a4;
}

.btn-comment-submit {
  align-self: flex-end;
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 11px 26px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-comment-submit:hover {
  background: #152a2a;
}
.btn-comment-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-login-prompt {
  width: 100%;
  background: transparent;
  border: 1.5px dashed rgba(30, 58, 58, 0.3);
  border-radius: 10px;
  padding: 18px;
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

/* 스레드 수정 */
.edit-thread-title {
  display: block;
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.18);
  border-radius: 8px;
  background: #fffdf8;
  padding: 10px 14px;
  font-family: 'Newsreader', serif;
  font-size: 22px;
  color: #262019;
  outline: none;
  margin-bottom: 12px;
  box-sizing: border-box;
}
.edit-thread-content {
  display: block;
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.18);
  border-radius: 8px;
  background: #fffdf8;
  padding: 12px 14px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #262019;
  outline: none;
  resize: vertical;
  margin-bottom: 12px;
  box-sizing: border-box;
}
.edit-thread-actions,
.edit-comment-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 8px;
}
.thread-mine-actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}
.btn-text-sm {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: #9c9079;
  cursor: pointer;
  transition: color 0.15s;
}
.btn-text-sm:hover { color: #4a4337; }
.btn-text-sm.danger:hover { color: #b06a3c; }
.btn-cancel {
  background: transparent;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 7px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: #6b6253;
  cursor: pointer;
}
.btn-save {
  background: #1e3a3a;
  border: none;
  border-radius: 999px;
  padding: 7px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  font-weight: 700;
  color: #f4eedf;
  cursor: pointer;
}
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }

/* 에러 */
.page-error {
  font-size: 14px;
  color: #b06a3c;
  padding: 14px 18px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 10px;
  border-left: 3px solid #b06a3c;
  margin-bottom: 20px;
}
</style>
