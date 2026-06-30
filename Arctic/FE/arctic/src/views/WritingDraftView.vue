<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { correctText, deleteDraft, fetchDrafts, generateIdeas, saveDraft, suggestPlot, updateDraft } from '@/api/ai'

const drafts = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const filterType = ref('all')
const selectedDraft = ref(null)
const aiRequestText = ref('')
const aiResult = ref(null)
const aiResultType = ref('')
const isAiRequesting = ref(false)
const aiRequestError = ref('')
const aiResultSection = ref(null)
const pendingPlotTitle = ref('')
const saveMessage = ref('')

// 제목 수정
const editingTitleId = ref(null)
const editingTitle = ref('')

const TYPE_LABELS = { idea: '아이디어', plot: '플롯', correction: '교정' }
const TYPE_COLORS = { idea: '#c9a86a', plot: '#5d9e8c', correction: '#a86ac9' }

const FILTER_TABS = [
  { id: 'all', label: '전체' },
  { id: 'idea', label: '아이디어' },
  { id: 'plot', label: '플롯' },
  { id: 'correction', label: '교정' },
]

const filteredDrafts = computed(() => {
  if (filterType.value === 'all') return drafts.value
  return drafts.value.filter((d) => d.draft_type === filterType.value)
})

const aiResultPreview = computed(() => {
  if (!aiResult.value) return ''
  const resultType = aiResultType.value || selectedDraft.value?.draft_type
  if (resultType === 'idea') {
    return (aiResult.value.ideas || []).join('\n\n')
  }
  if (resultType === 'plot' || resultType === 'plot-from-idea') {
    return [
      `기 — 도입\n${aiResult.value.intro || ''}`,
      `승 — 전개\n${aiResult.value.development || ''}`,
      `전 — 전환\n${aiResult.value.turn || ''}`,
      `결 — 결말\n${aiResult.value.conclusion || ''}`,
    ].join('\n\n')
  }
  if (resultType === 'correction') {
    return [
      `교정문\n${aiResult.value.corrected || ''}`,
      aiResult.value.explanation ? `개선 포인트\n${aiResult.value.explanation}` : '',
    ].filter(Boolean).join('\n\n')
  }
  return ''
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

async function loadDrafts() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    drafts.value = await fetchDrafts()
  } catch (err) {
    errorMessage.value = err.message
  } finally {
    isLoading.value = false
  }
}

async function handleDelete(id) {
  if (!confirm('이 창작물을 삭제할까요?')) return
  try {
    await deleteDraft(id)
    drafts.value = drafts.value.filter((d) => d.id !== id)
    if (selectedDraft.value?.id === id) selectedDraft.value = null
  } catch (err) {
    errorMessage.value = err.message
  }
}

function startTitleEdit(draft) {
  editingTitleId.value = draft.id
  editingTitle.value = draft.title || ''
}

async function saveTitleEdit(id) {
  try {
    const updated = await updateDraft(id, { title: editingTitle.value.trim() })
    drafts.value = drafts.value.map((d) => (d.id === id ? { ...d, title: updated.title } : d))
    if (selectedDraft.value?.id === id) {
      selectedDraft.value = { ...selectedDraft.value, title: updated.title }
    }
  } catch (err) {
    errorMessage.value = err.message
  } finally {
    editingTitleId.value = null
  }
}

function formatIdeaText(text) {
  if (!text) return ''
  return text
    .replace(/\s*(제목|핵심 전제|주요 등장인물|시공간 배경|핵심 갈등 구조|주요 장면)\s*[:：]\s*/g, '\n$1:\n\t')
    .replace(/^\n/, '')
    .trim()
}

function openDraft(draft) {
  selectedDraft.value = draft
  aiRequestText.value = ''
  aiResult.value = null
  aiResultType.value = ''
  aiRequestError.value = ''
  pendingPlotTitle.value = ''
  saveMessage.value = ''
}

function showSaveToast() {
  saveMessage.value = '저장 완료!'
  setTimeout(() => {
    saveMessage.value = ''
  }, 1800)
}

function getDraftText(draft) {
  if (!draft) return ''
  if (draft.draft_type === 'idea') {
    return (draft.content.ideas || []).join('\n\n')
  }
  if (draft.draft_type === 'plot') {
    return [
      draft.content.intro,
      draft.content.development,
      draft.content.turn,
      draft.content.conclusion,
    ].filter(Boolean).join('\n\n')
  }
  return [draft.content.original, draft.content.corrected, draft.content.explanation]
    .filter(Boolean)
    .join('\n\n')
}

async function requestAiRevision() {
  if (!selectedDraft.value || !aiRequestText.value.trim()) return

  isAiRequesting.value = true
  aiRequestError.value = ''
  aiResult.value = null

  const draft = selectedDraft.value
  aiResultType.value = draft.draft_type
  const request = aiRequestText.value.trim()
  const currentText = getDraftText(draft)

  try {
    if (draft.draft_type === 'idea') {
      aiResult.value = await generateIdeas({
        genre: draft.genre || '소설',
        keywords: `${draft.keywords || ''}\n현재 아이디어:\n${currentText}\n수정 요청:\n${request}`,
      })
    } else if (draft.draft_type === 'plot') {
      aiResult.value = await suggestPlot({
        idea: `현재 플롯:\n${currentText}\n\n수정 요청:\n${request}`,
        history: [],
      })
    } else {
      aiResult.value = {
        original: draft.content.original || currentText,
        ...(await correctText({
          text: `현재 문장:\n${currentText}\n\n수정 요청:\n${request}`,
        })),
      }
    }
  } catch (err) {
    aiRequestError.value = err.message
  } finally {
    isAiRequesting.value = false
  }
}

async function makePlotFromIdea(ideaText, ideaIndex) {
  if (!selectedDraft.value || selectedDraft.value.draft_type !== 'idea') return

  isAiRequesting.value = true
  aiRequestError.value = ''
  aiResult.value = null
  aiResultType.value = 'plot-from-idea'
  pendingPlotTitle.value = `${selectedDraft.value.title || '아이디어'} ${String(ideaIndex + 1).padStart(2, '0')} 플롯`

  try {
    aiResult.value = await suggestPlot({
      idea: ideaText,
      history: [],
    })
    await nextTick()
    aiResultSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (err) {
    aiRequestError.value = err.message
  } finally {
    isAiRequesting.value = false
  }
}

async function saveAiResult() {
  if (!selectedDraft.value || !aiResult.value) return
  try {
    if (aiResultType.value === 'plot-from-idea') {
      const created = await saveDraft({
        title: pendingPlotTitle.value || `${selectedDraft.value.title || '아이디어'} 플롯`,
        draft_type: 'plot',
        genre: selectedDraft.value.genre,
        keywords: selectedDraft.value.keywords,
        content: aiResult.value,
      })
      drafts.value = [created, ...drafts.value]
      filterType.value = 'plot'
      selectedDraft.value = created
      aiResult.value = null
      aiResultType.value = ''
      pendingPlotTitle.value = ''
      showSaveToast()
      return
    }

    const content = selectedDraft.value.draft_type === 'correction'
      ? {
          original: selectedDraft.value.content.original || getDraftText(selectedDraft.value),
          corrected: aiResult.value.corrected,
          explanation: aiResult.value.explanation,
        }
      : aiResult.value
    const updated = await updateDraft(selectedDraft.value.id, { content })
    drafts.value = drafts.value.map((d) => (d.id === updated.id ? updated : d))
    selectedDraft.value = updated
    aiResult.value = null
    aiResultType.value = ''
    aiRequestText.value = ''
    showSaveToast()
  } catch (err) {
    aiRequestError.value = err.message
  }
}

onMounted(loadDrafts)
</script>

<template>
  <div class="drafts-page">
    <!-- 배경 오버레이 -->
    <div class="bg-overlay"></div>

    <div class="drafts-inner">
      <!-- 헤더 -->
      <div class="drafts-header">
        <RouterLink :to="{ name: 'studio' }" class="back-link">← 창작 스튜디오</RouterLink>
        <h1 class="drafts-title">내 창작물</h1>
        <p class="drafts-sub">저장한 아이디어, 플롯, 교정 결과를 모아봤어요.</p>
      </div>

      <!-- 필터 탭 -->
      <div class="filter-tabs">
        <button
          v-for="tab in FILTER_TABS"
          :key="tab.id"
          :class="['filter-tab', { active: filterType === tab.id }]"
          type="button"
          @click="filterType = tab.id"
        >
          {{ tab.label }}
          <span class="tab-count">
            {{
              tab.id === 'all'
                ? drafts.length
                : drafts.filter((d) => d.draft_type === tab.id).length
            }}
          </span>
        </button>
      </div>

      <!-- 로딩 -->
      <div v-if="isLoading" class="skeleton-grid">
        <div v-for="n in 4" :key="n" class="skeleton-card"></div>
      </div>

      <!-- 에러 -->
      <p v-else-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 빈 상태 -->
      <div v-else-if="filteredDrafts.length === 0" class="empty-state">
        <p class="empty-text">아직 저장된 창작물이 없어요.</p>
        <RouterLink :to="{ name: 'studio' }" class="btn-go-studio">창작 스튜디오로 →</RouterLink>
      </div>

      <!-- 카드 그리드 -->
      <div v-else class="drafts-grid">
        <div
          v-for="draft in filteredDrafts"
          :key="draft.id"
          class="draft-card"
          @click="openDraft(draft)"
        >
          <div class="draft-card-top">
            <span
              class="type-badge"
              :style="{
                background: TYPE_COLORS[draft.draft_type] + '22',
                color: TYPE_COLORS[draft.draft_type],
              }"
              >{{ TYPE_LABELS[draft.draft_type] }}</span
            >
            <span class="draft-date">{{ formatDate(draft.created_at) }}</span>
          </div>

          <div class="draft-title-row">
            <template v-if="editingTitleId === draft.id">
              <div class="title-edit-form" @click.stop>
                <input
                  v-model="editingTitle"
                  class="title-edit-input"
                  type="text"
                  @keyup.enter="saveTitleEdit(draft.id)"
                  @keyup.esc="editingTitleId = null"
                />
                <button class="btn-title-save" type="button" @click="saveTitleEdit(draft.id)">확인</button>
              </div>
            </template>
            <h3 v-else class="draft-title">
              {{ draft.title || '제목 없음' }}
            </h3>
          </div>

          <div class="draft-tags">
            <span v-if="draft.genre" class="draft-tag">{{ draft.genre }}</span>
            <span v-if="draft.keywords" class="draft-tag"
              >{{ draft.keywords.slice(0, 20) }}{{ draft.keywords.length > 20 ? '…' : '' }}</span
            >
          </div>

          <div class="draft-card-actions" @click.stop>
            <button class="btn-edit-title" type="button" @click="startTitleEdit(draft)">제목 수정</button>
            <button class="btn-delete" type="button" @click="handleDelete(draft.id)">삭제</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 상세 모달 -->
    <Transition name="modal-fade">
      <div v-if="selectedDraft" class="modal-backdrop" @click.self="selectedDraft = null">
        <div class="modal-card">
          <div class="modal-header">
            <div style="flex: 1; min-width: 0;">
              <span
                class="type-badge"
                :style="{
                  background: TYPE_COLORS[selectedDraft.draft_type] + '22',
                  color: TYPE_COLORS[selectedDraft.draft_type],
                }"
                >{{ TYPE_LABELS[selectedDraft.draft_type] }}</span
              >
              <template v-if="editingTitleId === selectedDraft.id">
                <div class="modal-title-edit-row">
                  <input
                    v-model="editingTitle"
                    class="title-edit-input"
                    type="text"
                    @keyup.enter="saveTitleEdit(selectedDraft.id)"
                    @keyup.esc="editingTitleId = null"
                  />
                  <button class="btn-title-save" type="button" @click="saveTitleEdit(selectedDraft.id)">확인</button>
                </div>
              </template>
              <template v-else>
                <h2 class="modal-title">
                  {{ selectedDraft.title || '제목 없음' }}
                </h2>
              </template>
            </div>
            <button class="modal-close" type="button" @click="selectedDraft = null">✕</button>
          </div>

          <div class="modal-meta">
            <span v-if="selectedDraft.genre" class="draft-tag">{{ selectedDraft.genre }}</span>
            <span v-if="selectedDraft.keywords" class="draft-tag">{{
              selectedDraft.keywords
            }}</span>
            <span class="draft-date">{{ formatDate(selectedDraft.created_at) }}</span>
          </div>

          <!-- 아이디어 -->
          <div v-if="selectedDraft.draft_type === 'idea'" class="modal-body">
            <div v-for="(idea, i) in selectedDraft.content.ideas" :key="i" class="modal-idea">
              <span class="result-num">{{ String(i + 1).padStart(2, '0') }}</span>
              <p class="modal-text idea-detail-text">{{ formatIdeaText(idea) }}</p>
              <button
                class="btn-use-idea"
                type="button"
                :disabled="isAiRequesting"
                @click="makePlotFromIdea(idea, i)"
              >
                {{ isAiRequesting ? '플롯 만드는 중...' : '이 아이디어로 플롯 만들기 →' }}
              </button>
            </div>
          </div>

          <!-- 플롯 -->
          <div v-else-if="selectedDraft.draft_type === 'plot'" class="modal-body">
            <div
              v-for="(label, key) in {
                intro: '기 — 도입',
                development: '승 — 전개',
                turn: '전 — 전환',
                conclusion: '결 — 결말',
              }"
              :key="key"
              class="modal-plot-section"
            >
              <span class="plot-label">{{ label }}</span>
              <p class="modal-text">{{ selectedDraft.content[key] }}</p>
            </div>
          </div>

          <!-- 교정 -->
          <div v-else-if="selectedDraft.draft_type === 'correction'" class="modal-body">
            <div class="correction-pair">
              <div class="correction-panel before">
                <span class="panel-label">원문</span>
                <p class="modal-text">{{ selectedDraft.content.original }}</p>
              </div>
              <div class="correction-panel after">
                <span class="panel-label">교정문</span>
                <p class="modal-text">{{ selectedDraft.content.corrected }}</p>
              </div>
            </div>
            <div v-if="selectedDraft.content.explanation" class="explanation-box">
              <span class="panel-label">개선 포인트</span>
              <p class="modal-text">{{ selectedDraft.content.explanation }}</p>
            </div>
          </div>

          <section class="ai-revision-box">
            <span class="panel-label">AI 수정 요청</span>
            <textarea
              v-model="aiRequestText"
              class="ai-revision-input"
              rows="3"
              placeholder="예: 더 어둡고 긴장감 있게 바꿔줘 / 결말을 반전으로 바꿔줘"
            ></textarea>
            <div class="ai-revision-actions">
              <button
                class="btn-ai-request"
                type="button"
                :disabled="isAiRequesting || !aiRequestText.trim()"
                @click="requestAiRevision"
              >
                {{ isAiRequesting ? '요청 중...' : 'AI에게 요청' }}
              </button>
              <button
                v-if="aiResult"
                class="btn-ai-save"
                type="button"
                @click="saveAiResult"
              >
                {{ aiResultType === 'plot-from-idea' ? '플롯으로 저장' : '이 결과로 저장' }}
              </button>
            </div>
            <p v-if="aiRequestError" class="ai-revision-error">{{ aiRequestError }}</p>
            <div v-if="aiResult" ref="aiResultSection" class="ai-revision-result">
              <span class="panel-label">요청 결과</span>
              <p class="modal-text">{{ aiResultPreview }}</p>
            </div>
          </section>
        </div>
      </div>
    </Transition>

    <Transition name="save-toast">
      <p v-if="saveMessage" class="draft-save-toast">{{ saveMessage }}</p>
    </Transition>
  </div>
</template>

<style scoped>
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes shimmer {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.6;
  }
}

/* ── 페이지 ── */
.drafts-page {
  min-height: 100vh;
  background: #1a150f;
  font-family: 'Gowun Batang', serif;
  color: #f3ecdc;
  position: relative;
}

.bg-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(80% 70% at 50% 30%, #2e2418 0%, #1a150f 100%);
}

.drafts-inner {
  position: relative;
  z-index: 1;
  max-width: 1080px;
  margin: 0 auto;
  padding: 52px 32px 100px;
  animation: fadeUp 0.6s ease both;
}

/* 헤더 */
.drafts-header {
  margin-bottom: 36px;
}

.back-link {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(201, 168, 106, 0.5);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 20px;
  transition: color 0.15s;
}
.back-link:hover {
  color: #c9a86a;
}

.drafts-title {
  font-family: 'Newsreader', serif;
  font-size: 36px;
  font-weight: 300;
  color: #f3ecdc;
  margin: 0 0 8px;
}
.drafts-sub {
  font-size: 14px;
  color: rgba(243, 236, 220, 0.5);
  margin: 0;
}

/* 필터 탭 */
.filter-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}

.filter-tab {
  background: transparent;
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 999px;
  padding: 11px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 16px;
  color: rgba(243, 236, 220, 0.5);
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 7px;
}
.filter-tab:hover {
  border-color: rgba(201, 168, 106, 0.45);
  color: rgba(243, 236, 220, 0.8);
}
.filter-tab.active {
  background: #c9a86a;
  border-color: #c9a86a;
  color: #1a150f;
  font-weight: 700;
}

.tab-count {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  padding: 1px 7px;
}
.filter-tab.active .tab-count {
  background: rgba(26, 21, 15, 0.2);
}

/* 카드 그리드 */
.drafts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.draft-card {
  background: rgba(201, 168, 106, 0.06);
  border: 1px solid rgba(201, 168, 106, 0.14);
  border-radius: 14px;
  padding: 22px 20px;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.draft-card:hover {
  background: rgba(201, 168, 106, 0.1);
  border-color: rgba(201, 168, 106, 0.3);
  transform: translateY(-2px);
}

.draft-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.type-badge {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  border-radius: 999px;
  padding: 3px 10px;
  font-weight: 700;
}

.draft-date {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 10.5px;
  color: rgba(243, 236, 220, 0.3);
}

.draft-title {
  font-family: 'Newsreader', serif;
  font-size: 17px;
  font-weight: 400;
  color: #f3ecdc;
  margin: 0;
  line-height: 1.35;
}

.draft-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.draft-tag {
  font-size: 11.5px;
  color: rgba(243, 236, 220, 0.45);
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
  padding: 2px 9px;
}

.draft-card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

.btn-edit-title {
  background: transparent;
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 999px;
  padding: 4px 12px;
  font-family: 'Gowun Batang', serif;
  font-size: 11.5px;
  color: rgba(201, 168, 106, 0.5);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-edit-title:hover {
  border-color: rgba(201, 168, 106, 0.5);
  color: #c9a86a;
}

.btn-delete {
  background: transparent;
  border: 1px solid rgba(229, 115, 115, 0.35);
  border-radius: 999px;
  padding: 4px 12px;
  font-family: 'Gowun Batang', serif;
  font-size: 11.5px;
  color: rgba(229, 115, 115, 0.6);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-delete:hover {
  background: rgba(229, 115, 115, 0.12);
  border-color: #e57373;
  color: #e57373;
}

.draft-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.title-edit-form,
.modal-title-edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.modal-title-edit-row {
  margin-top: 8px;
  flex-wrap: wrap;
}

.title-edit-input {
  flex: 1;
  min-width: 0;
  background: rgba(201, 168, 106, 0.1);
  border: 1px solid rgba(201, 168, 106, 0.3);
  border-radius: 6px;
  padding: 6px 10px;
  font-family: 'Newsreader', serif;
  font-size: 15px;
  color: #f3ecdc;
  outline: none;
}

.btn-title-save {
  flex-shrink: 0;
  background: rgba(201, 168, 106, 0.2);
  border: 1px solid rgba(201, 168, 106, 0.35);
  border-radius: 999px;
  padding: 4px 12px;
  font-family: 'Gowun Batang', serif;
  font-size: 11.5px;
  color: #c9a86a;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.btn-title-save:hover {
  background: rgba(201, 168, 106, 0.3);
}

/* 스켈레톤 */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.skeleton-card {
  height: 140px;
  border-radius: 14px;
  background: rgba(201, 168, 106, 0.08);
  animation: shimmer 1.6s ease-in-out infinite;
}

/* 빈 상태 */
.empty-state {
  text-align: center;
  padding: 80px 24px;
}
.empty-text {
  font-size: 15px;
  color: rgba(243, 236, 220, 0.4);
  margin: 0 0 24px;
  font-style: italic;
}
.btn-go-studio {
  background: #c9a86a;
  color: #1a150f;
  text-decoration: none;
  border-radius: 999px;
  padding: 11px 26px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  transition: background 0.15s;
}
.btn-go-studio:hover {
  background: #e0bc7a;
}

/* 에러 */
.page-error {
  font-size: 14px;
  color: #e57373;
  padding: 12px 16px;
  background: rgba(229, 115, 115, 0.1);
  border-radius: 10px;
  border-left: 2px solid #e57373;
}

/* ── 모달 ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(10, 7, 4, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
}

.modal-card {
  width: 100%;
  max-width: 700px;
  max-height: 85vh;
  background: #221a10;
  border: 1px solid rgba(201, 168, 106, 0.25);
  border-radius: 18px;
  padding: 32px 36px;
  overflow-y: auto;
  animation: fadeUp 0.3s ease both;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
}

.modal-title {
  font-family: 'Newsreader', serif;
  font-size: 24px;
  font-weight: 400;
  color: #f3ecdc;
  margin: 8px 0 0;
}

.modal-close {
  background: transparent;
  border: none;
  padding: 4px 8px;
  font-size: 16px;
  color: rgba(243, 236, 220, 0.4);
  cursor: pointer;
  transition: color 0.15s;
  flex-shrink: 0;
}
.modal-close:hover {
  color: #f3ecdc;
}

.modal-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(201, 168, 106, 0.1);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.modal-idea {
}

.btn-use-idea {
  align-self: flex-start;
  border: 1px solid rgba(201, 168, 106, 0.35);
  border-radius: 999px;
  background: transparent;
  padding: 9px 18px;
  color: #c9a86a;
  font: inherit;
  font-size: 13.5px;
  cursor: pointer;
}

.btn-use-idea:hover:not(:disabled) {
  background: rgba(201, 168, 106, 0.1);
}

.btn-use-idea:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.result-num {
  font-family: 'Newsreader', serif;
  font-size: 13px;
  color: #c9a86a;
  display: block;
  margin-bottom: 6px;
}

.modal-text {
  font-size: 14.5px;
  line-height: 1.85;
  color: rgba(243, 236, 220, 0.85);
  margin: 0;
  white-space: pre-wrap;
  tab-size: 2;
}

.modal-plot-section {
  border-left: 2px solid rgba(201, 168, 106, 0.3);
  padding-left: 16px;
}

.plot-label {
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  letter-spacing: 0;
  font-weight: 700;
  color: #c9a86a;
  display: block;
  margin-bottom: 6px;
}

.correction-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

@media (max-width: 560px) {
  .correction-pair {
    grid-template-columns: 1fr;
  }
}

.correction-panel {
  border-radius: 10px;
  padding: 14px 16px;
}
.correction-panel.before {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.correction-panel.after {
  background: rgba(201, 168, 106, 0.07);
  border: 1px solid rgba(201, 168, 106, 0.2);
}

.panel-label {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 2px;
  text-transform: uppercase;
  display: block;
  margin-bottom: 6px;
  color: rgba(243, 236, 220, 0.4);
}
.correction-panel.after .panel-label {
  color: #c9a86a;
}

.explanation-box {
  background: rgba(201, 168, 106, 0.05);
  border: 1px solid rgba(201, 168, 106, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
}

.ai-revision-box {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(201, 168, 106, 0.14);
}

.ai-revision-input {
  width: 100%;
  box-sizing: border-box;
  background: rgba(201, 168, 106, 0.07);
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 10px;
  padding: 11px 14px;
  color: #f3ecdc;
  font: inherit;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
}

.ai-revision-input:focus {
  border-color: rgba(201, 168, 106, 0.5);
}

.ai-revision-input::placeholder {
  color: rgba(243, 236, 220, 0.32);
}

.ai-revision-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.btn-ai-request,
.btn-ai-save {
  border: 1px solid rgba(201, 168, 106, 0.35);
  border-radius: 999px;
  padding: 8px 18px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.btn-ai-request {
  background: #c9a86a;
  color: #1a150f;
  font-weight: 700;
}

.btn-ai-request:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-ai-save {
  background: transparent;
  color: #c9a86a;
}

.ai-revision-error {
  margin: 10px 0 0;
  color: #e57373;
  font-size: 13px;
}

.ai-revision-result {
  margin-top: 16px;
  border-radius: 10px;
  background: rgba(201, 168, 106, 0.05);
  border: 1px solid rgba(201, 168, 106, 0.15);
  padding: 14px 16px;
}

/* 트랜지션 */
.draft-save-toast {
  position: fixed;
  left: 50%;
  top: 50%;
  z-index: 130;
  transform: translate(-50%, -50%);
  margin: 0;
  padding: 15px 24px;
  border: 1px solid rgba(201, 168, 106, 0.42);
  border-radius: 999px;
  background: rgba(26, 21, 15, 0.92);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.34);
  color: #e0bc7a;
  font-family: 'Gowun Batang', serif;
  font-size: 16px;
  font-weight: 700;
  pointer-events: none;
}

.save-toast-enter-active,
.save-toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.save-toast-enter-from,
.save-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -44%);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition:
    opacity 0.25s,
    transform 0.25s;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: scale(0.97);
}
</style>
