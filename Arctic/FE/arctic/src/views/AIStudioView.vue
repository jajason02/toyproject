<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { correctText, generateIdeas, saveDraft, suggestPlot } from '@/api/ai'

const router = useRouter()

const showStudio = ref(false)
const activeTab = ref('ideas')

const genre = ref('SF')
const keywords = ref('')
const plotIdea = ref('')
const correctionText = ref('')

const ideasResult = ref([])
const selectedIdeaIndex = ref(0)
const plotResult = ref(null)
const plotHistory = ref([]) // [{role, content}] — 챗봇 대화 누적
const plotFeedback = ref('')
const correctionResult = ref(null)

const isGenerating = ref(false)
const generatingAction = ref('')
const isSaving = ref(false)
const errorMessage = ref('')
const saveMessage = ref('')

// 제목 지정 저장 모달
const showSaveModal = ref(false)
const saveTitle = ref('')
const pendingDraftType = ref('')
const pendingDraftContent = ref(null)

const plotIdeaRows = computed(() => {
  const text = plotIdea.value || ''
  const visualLines = text
    .split('\n')
    .reduce((sum, line) => sum + Math.max(1, Math.ceil(line.length / 62)), 0)
  return Math.min(12, Math.max(3, visualLines))
})

const GENRES = ['소설', 'SF', '추리/스릴러', '에세이', '판타지', '로맨스', '역사', '공포']

const tabs = [
  { id: 'ideas', label: '아이디어 발상' },
  { id: 'plot', label: '플롯 제안' },
  { id: 'correction', label: '문장 교정' },
]

function switchTab(tabId) {
  activeTab.value = tabId
  errorMessage.value = ''
  saveMessage.value = ''
}

function formatIdeaText(text) {
  if (!text) return ''
  return text
    .replace(/\s*(제목|핵심 전제|주요 등장인물|시공간 배경|핵심 갈등 구조|주요 장면)\s*[:：]\s*/g, '\n$1:\n\t')
    .replace(/^\n/, '')
    .trim()
}

function formatPlotForPrompt(plot) {
  if (!plot) return ''
  return [
    `기 — 도입\n${plot.intro || ''}`,
    `승 — 전개\n${plot.development || ''}`,
    `전 — 전환\n${plot.turn || ''}`,
    `결 — 결말\n${plot.conclusion || ''}`,
  ].join('\n\n')
}

function buildPlotRevisionPrompt(currentPlot, request) {
  return [
    '초안 아이디어는 참고용입니다. 이미 반영된 수정사항과 충돌하면 반드시 현재 플롯을 우선하세요.',
    '',
    `[초안 아이디어]\n${plotIdea.value}`,
    '',
    `[현재 플롯]\n${formatPlotForPrompt(currentPlot)}`,
    '',
    `[이번 수정 요청]\n${request}`,
    '',
    '위 현재 플롯을 기준으로 이번 수정 요청만 반영해서 다시 작성하세요. 이름, 사건, 배경처럼 사용자가 바꾼 최신 설정은 유지하고 초안 설정으로 되돌리지 마세요.',
  ].join('\n')
}

async function handleGenerate() {
  isGenerating.value = true
  generatingAction.value = activeTab.value
  errorMessage.value = ''
  saveMessage.value = ''

  try {
    if (activeTab.value === 'ideas') {
      ideasResult.value = []
      selectedIdeaIndex.value = 0
      const res = await generateIdeas({ genre: genre.value, keywords: keywords.value })
      ideasResult.value = res.ideas || []
    } else if (activeTab.value === 'plot') {
      // 새 아이디어로 시작하면 history 초기화
      plotHistory.value = []
      plotResult.value = null
      const res = await suggestPlot({ idea: plotIdea.value, history: [] })
      plotResult.value = res
      // assistant 응답을 history에 추가
      plotHistory.value.push({ role: 'assistant', content: JSON.stringify(res) })
    } else {
      correctionResult.value = null
      const res = await correctText({ text: correctionText.value })
      correctionResult.value = { original: correctionText.value, ...res }
    }
  } catch (err) {
    errorMessage.value = err.message
  } finally {
    isGenerating.value = false
    generatingAction.value = ''
  }
}

async function handlePlotFeedback() {
  if (!plotFeedback.value.trim() || !plotResult.value) return
  isGenerating.value = true
  generatingAction.value = 'plot-feedback'
  errorMessage.value = ''
  const userMsg = plotFeedback.value.trim()
  const currentPlot = { ...plotResult.value }
  plotFeedback.value = ''
  try {
    const revisionPrompt = buildPlotRevisionPrompt(currentPlot, userMsg)
    const res = await suggestPlot({ idea: revisionPrompt, history: [] })
    plotResult.value = res
    plotHistory.value = [
      ...plotHistory.value,
      { role: 'user', content: userMsg },
      { role: 'assistant', content: JSON.stringify(res) },
    ].slice(-8)
  } catch (err) {
    errorMessage.value = err.message
  } finally {
    isGenerating.value = false
    generatingAction.value = ''
  }
}

function openSaveModal(draftType, content) {
  pendingDraftType.value = draftType
  pendingDraftContent.value = content
  saveTitle.value = `${genre.value} 창작물`
  showSaveModal.value = true
}

async function confirmSave() {
  isSaving.value = true
  saveMessage.value = ''
  showSaveModal.value = false
  try {
    await saveDraft({
      title: saveTitle.value.trim() || `${genre.value} 창작물`,
      draft_type: pendingDraftType.value,
      genre: genre.value,
      keywords: keywords.value,
      content: pendingDraftContent.value,
    })
    saveMessage.value = '저장 완료!'
    setTimeout(() => { saveMessage.value = '' }, 2500)
  } catch (err) {
    errorMessage.value = err.message
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  setTimeout(() => {
    showStudio.value = true
  }, 800)
})
</script>

<template>
  <div class="studio-page">
    <!-- 시네마틱 책장 배경 -->
    <div class="bookshelf-bg"></div>

    <!-- 스튜디오 카드 -->
    <Transition name="studio-fade">
      <div v-if="showStudio" class="studio-overlay">
        <div class="studio-card">
          <div class="studio-header">
            <div class="studio-badge">
              <span class="badge-dot"></span>
              창작 스튜디오
            </div>
            <h1 class="studio-title">당신의 첫 문장을,<br />함께 씁니다.</h1>
          </div>

          <!-- 탭 -->
          <div class="studio-tabs">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              :class="['studio-tab', { active: activeTab === tab.id }]"
              type="button"
              @click="switchTab(tab.id)"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- ── 아이디어 발상 ── -->
          <div v-if="activeTab === 'ideas'" class="tab-body">
            <div class="input-row">
              <label class="input-label">장르</label>
              <div class="genre-chips">
                <button
                  v-for="g in GENRES"
                  :key="g"
                  :class="['g-chip', { active: genre === g }]"
                  type="button"
                  @click="genre = g"
                >
                  {{ g }}
                </button>
              </div>
            </div>
            <div class="input-row">
              <label class="input-label">키워드</label>
              <input
                v-model="keywords"
                class="studio-input"
                type="text"
                placeholder="예: 고독 · 우주 · 편지"
              />
            </div>
            <button
              class="btn-generate"
              type="button"
              :disabled="isGenerating || !keywords.trim()"
              @click="handleGenerate"
            >
              <span v-if="generatingAction === 'ideas'" class="loading-spinner"></span>
              {{ generatingAction === 'ideas' ? '생성 중...' : '아이디어 생성' }}
            </button>

            <div v-if="ideasResult.length > 0" class="results-section">
              <div class="results-header">
                <span class="results-label">아이디어</span>
                <div class="idea-nav">
                  <button
                    v-for="(_, i) in ideasResult"
                    :key="i"
                    :class="['idea-nav-btn', { active: selectedIdeaIndex === i }]"
                    type="button"
                    @click="selectedIdeaIndex = i"
                  >
                    {{ String(i + 1).padStart(2, '0') }}
                  </button>
                </div>
                <button
                  class="btn-save-result"
                  type="button"
                  :disabled="isSaving"
                  @click="openSaveModal('idea', { ideas: ideasResult })"
                >
                  {{ isSaving ? '저장 중...' : '저장' }}
                </button>
              </div>
              <div class="idea-card">
                <span class="result-num">{{ String(selectedIdeaIndex + 1).padStart(2, '0') }}</span>
                <p class="idea-text">{{ formatIdeaText(ideasResult[selectedIdeaIndex]) }}</p>
                <button
                  class="btn-use-idea"
                  type="button"
                  @click="plotIdea = ideasResult[selectedIdeaIndex]; activeTab = 'plot'"
                >
                  이 아이디어로 플롯 만들기 →
                </button>
              </div>
            </div>
          </div>

          <!-- ── 플롯 제안 ── -->
          <div v-if="activeTab === 'plot'" class="tab-body">
            <div class="input-row">
              <label class="input-label">아이디어</label>
              <textarea
                v-model="plotIdea"
                class="studio-textarea plot-idea-textarea"
                placeholder="이야기의 씨앗이 되는 아이디어를 적어주세요."
                :rows="plotIdeaRows"
              ></textarea>
            </div>
            <button
              class="btn-generate"
              type="button"
              :disabled="isGenerating || !plotIdea.trim()"
              @click="handleGenerate"
            >
              <span v-if="generatingAction === 'plot'" class="loading-spinner"></span>
              {{ generatingAction === 'plot' ? '생성 중...' : '플롯 제안 받기' }}
            </button>

            <div v-if="plotResult" class="results-section">
              <div class="results-header">
                <span class="results-label">기승전결 플롯</span>
                <button
                  class="btn-save-result"
                  type="button"
                  :disabled="isSaving"
                  @click="openSaveModal('plot', plotResult)"
                >
                  {{ isSaving ? '저장 중...' : '저장' }}
                </button>
              </div>
              <div class="plot-sections">
                <div class="plot-section">
                  <span class="plot-label">기 — 도입</span>
                  <p class="plot-text">{{ plotResult.intro }}</p>
                </div>
                <div class="plot-section">
                  <span class="plot-label">승 — 전개</span>
                  <p class="plot-text">{{ plotResult.development }}</p>
                </div>
                <div class="plot-section">
                  <span class="plot-label">전 — 전환</span>
                  <p class="plot-text">{{ plotResult.turn }}</p>
                </div>
                <div class="plot-section">
                  <span class="plot-label">결 — 결말</span>
                  <p class="plot-text">{{ plotResult.conclusion }}</p>
                </div>
              </div>

              <!-- 챗봇 피드백 -->
              <div class="plot-feedback-area">
                <span class="plot-label" style="margin-bottom: 8px;">수정 요청</span>
                <textarea
                  v-model="plotFeedback"
                  class="studio-textarea"
                  placeholder="수정하고 싶은 부분을 알려주세요. 예: 결말을 더 반전 있게 바꿔줘"
                  rows="2"
                ></textarea>
                <button
                  class="btn-feedback"
                  type="button"
                  :disabled="isGenerating || !plotFeedback.trim()"
                  @click="handlePlotFeedback"
                >
                  <span v-if="generatingAction === 'plot-feedback'" class="loading-spinner"></span>
                  {{ generatingAction === 'plot-feedback' ? '수정 중...' : '플롯 수정 요청' }}
                </button>
              </div>
            </div>
          </div>

          <!-- ── 문장 교정 ── -->
          <div v-if="activeTab === 'correction'" class="tab-body">
            <div class="input-row">
              <label class="input-label">교정할 문장</label>
              <textarea
                v-model="correctionText"
                class="studio-textarea"
                placeholder="다듬고 싶은 문장이나 단락을 붙여넣어 주세요."
                rows="5"
              ></textarea>
            </div>
            <button
              class="btn-generate"
              type="button"
              :disabled="isGenerating || !correctionText.trim()"
              @click="handleGenerate"
            >
              <span v-if="generatingAction === 'correction'" class="loading-spinner"></span>
              {{ generatingAction === 'correction' ? '교정 중...' : '문장 교정하기' }}
            </button>

            <div v-if="correctionResult" class="results-section">
              <div class="results-header">
                <span class="results-label">교정 결과</span>
                <button
                  class="btn-save-result"
                  type="button"
                  :disabled="isSaving"
                  @click="openSaveModal('correction', correctionResult)"
                >
                  {{ isSaving ? '저장 중...' : '저장' }}
                </button>
              </div>
              <div class="correction-panels">
                <div class="correction-panel before">
                  <span class="panel-label">원문</span>
                  <p class="panel-text">{{ correctionResult.original }}</p>
                </div>
                <div class="correction-panel after">
                  <span class="panel-label">교정문</span>
                  <p class="panel-text">{{ correctionResult.corrected }}</p>
                </div>
              </div>
              <div v-if="correctionResult.explanation" class="explanation-box">
                <span class="explanation-label">개선 포인트</span>
                <p class="explanation-text">{{ correctionResult.explanation }}</p>
              </div>
            </div>
          </div>

          <!-- 에러 -->
          <p v-if="errorMessage" class="studio-error">{{ errorMessage }}</p>

          <!-- 푸터 -->
          <div class="studio-footer">
            <RouterLink :to="{ name: 'studio-drafts' }" class="link-drafts"
              >내 창작물 보기</RouterLink
            >
            <button class="btn-leave" type="button" @click="router.push({ name: 'books' })">
              ↑ 책장 나가기
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <Transition name="save-toast">
      <p v-if="saveMessage" class="studio-save-toast">{{ saveMessage }}</p>
    </Transition>

    <!-- 제목 지정 저장 모달 -->
    <Transition name="modal-fade">
      <div v-if="showSaveModal" class="save-modal-backdrop" @click.self="showSaveModal = false">
        <div class="save-modal">
          <p class="save-modal-label">창작물 제목</p>
          <input
            v-model="saveTitle"
            class="save-modal-input"
            type="text"
            placeholder="제목을 입력하세요"
            @keyup.enter="confirmSave"
          />
          <div class="save-modal-actions">
            <button class="btn-modal-cancel" type="button" @click="showSaveModal = false">취소</button>
            <button class="btn-modal-confirm" type="button" @click="confirmSave">저장</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@keyframes cinematicIntro {
  0% {
    opacity: 0;
    transform: scale(1.08);
    filter: blur(8px);
  }
  100% {
    opacity: 1;
    transform: scale(1);
    filter: blur(0);
  }
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── 페이지 ── */
.studio-page {
  min-height: 100vh;
  background: #1a150f;
  font-family: 'Gowun Batang', serif;
  position: relative;
  overflow: hidden;
}

/* ── 책장 배경 ── */
.bookshelf-bg {
  position: absolute;
  inset: 0;
  background: url('/bookshelf-bg.png') center center / cover no-repeat;
  animation: cinematicIntro 1.8s ease forwards;
}
.bookshelf-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(10, 6, 2, 0.55);
}

/* ── 오버레이 ── */
.studio-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 32px 24px;
  overflow-y: auto;
}

.studio-card {
  width: 100%;
  max-width: 780px;
  background: rgba(26, 18, 10, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 18px;
  padding: 36px 40px;
  box-shadow: 0 0 60px rgba(201, 168, 106, 0.1);
  animation: fadeUp 0.65s ease both 0.8s;
  opacity: 0;
  margin: 0;
}

/* ── 헤더 ── */
.studio-header {
  margin-bottom: 24px;
}

.studio-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  color: #c9a86a;
  margin-bottom: 12px;
}
.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c9a86a;
}

.studio-title {
  font-family: 'Gowun Batang', serif;
  font-size: 30px;
  font-weight: 300;
  color: #f3ecdc;
  margin: 0;
  line-height: 1.25;
}

/* ── 탭 ── */
.studio-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid rgba(201, 168, 106, 0.15);
  margin-bottom: 24px;
}

.studio-tab {
  padding: 10px 20px;
  margin-bottom: -1px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-family: 'Gowun Batang', serif;
  font-size: 14.5px;
  color: rgba(243, 236, 220, 0.4);
  cursor: pointer;
  transition: color 0.15s;
}
.studio-tab:hover {
  color: rgba(243, 236, 220, 0.7);
}
.studio-tab.active {
  color: #f3ecdc;
  font-weight: 700;
  border-bottom-color: #c9a86a;
}

/* ── 탭 바디 ── */
.tab-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.input-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.7);
}

.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.g-chip {
  background: transparent;
  color: rgba(243, 236, 220, 0.6);
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 999px;
  padding: 7px 16px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.g-chip:hover {
  border-color: rgba(201, 168, 106, 0.5);
  color: #f3ecdc;
}
.g-chip.active {
  background: #c9a86a;
  border-color: #c9a86a;
  color: #1a150f;
  font-weight: 700;
}

.studio-input,
.studio-textarea {
  width: 100%;
  background: rgba(201, 168, 106, 0.07);
  border: 1px solid rgba(201, 168, 106, 0.18);
  border-radius: 10px;
  padding: 12px 16px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #f3ecdc;
  outline: none;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.studio-input:focus,
.studio-textarea:focus {
  border-color: rgba(201, 168, 106, 0.5);
}
.studio-input::placeholder,
.studio-textarea::placeholder {
  color: rgba(243, 236, 220, 0.3);
}

.plot-idea-textarea {
  min-height: 92px;
  max-height: 360px;
  overflow-y: auto;
}

.btn-generate {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #c9a86a;
  color: #1a150f;
  border: none;
  border-radius: 999px;
  padding: 12px 28px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}
.loading-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}
.btn-generate:hover:not(:disabled) {
  background: #e0bc7a;
}
.btn-generate:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── 결과 공통 ── */
.results-section {
  margin-top: 8px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.results-label {
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.6);
}
.btn-save-result {
  background: transparent;
  border: 1px solid rgba(201, 168, 106, 0.35);
  border-radius: 999px;
  padding: 6px 18px;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: #c9a86a;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-save-result:hover:not(:disabled) {
  background: rgba(201, 168, 106, 0.1);
}
.btn-save-result:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 아이디어 네비게이션 */
.idea-nav {
  display: flex;
  gap: 6px;
}
.idea-nav-btn {
  background: transparent;
  border: 1px solid rgba(201, 168, 106, 0.25);
  border-radius: 999px;
  padding: 4px 12px;
  font-family: 'Gowun Batang', serif;
  font-size: 12px;
  color: rgba(201, 168, 106, 0.5);
  cursor: pointer;
  transition: all 0.15s;
}
.idea-nav-btn:hover {
  border-color: rgba(201, 168, 106, 0.6);
  color: #c9a86a;
}
.idea-nav-btn.active {
  background: rgba(201, 168, 106, 0.15);
  border-color: #c9a86a;
  color: #c9a86a;
  font-weight: 700;
}

/* 아이디어 카드 */
.idea-card {
  border: 1px solid rgba(201, 168, 106, 0.14);
  border-radius: 12px;
  padding: 18px 20px;
  background: rgba(201, 168, 106, 0.04);
}

.result-num {
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  font-weight: 700;
  color: #c9a86a;
  display: block;
  margin-bottom: 8px;
}

.idea-text {
  font-size: 14.5px;
  line-height: 1.85;
  color: rgba(243, 236, 220, 0.85);
  margin: 0 0 14px;
  white-space: pre-wrap;
  tab-size: 2;
}

.btn-use-idea {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 13px;
  color: rgba(201, 168, 106, 0.6);
  cursor: pointer;
  transition: color 0.15s;
}
.btn-use-idea:hover {
  color: #c9a86a;
}

/* 플롯 결과 */
.plot-sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.plot-section {
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

.plot-text {
  font-size: 14.5px;
  line-height: 1.85;
  color: rgba(243, 236, 220, 0.85);
  margin: 0;
  white-space: pre-wrap;
}

/* 교정 결과 */
.correction-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

@media (max-width: 600px) {
  .correction-panels {
    grid-template-columns: 1fr;
  }
}

.correction-panel {
  border-radius: 10px;
  padding: 16px 18px;
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
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  display: block;
  margin-bottom: 8px;
  color: rgba(243, 236, 220, 0.4);
}
.correction-panel.after .panel-label {
  color: #c9a86a;
}

.panel-text {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(243, 236, 220, 0.8);
  margin: 0;
  white-space: pre-wrap;
}

.explanation-box {
  background: rgba(201, 168, 106, 0.05);
  border: 1px solid rgba(201, 168, 106, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
}
.explanation-label {
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.6);
  display: block;
  margin-bottom: 6px;
}
.explanation-text {
  font-size: 13.5px;
  line-height: 1.8;
  color: rgba(243, 236, 220, 0.7);
  margin: 0;
}

/* 에러 / 저장 완료 */
.studio-error {
  font-size: 13px;
  color: #e57373;
  padding: 10px 14px;
  background: rgba(229, 115, 115, 0.1);
  border-radius: 8px;
  border-left: 2px solid #e57373;
  margin-top: 12px;
}
.studio-save-toast {
  position: fixed;
  left: 50%;
  top: 50%;
  z-index: 80;
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

/* ── 푸터 ── */
.studio-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid rgba(201, 168, 106, 0.1);
}

.link-drafts {
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.5);
  text-decoration: none;
  transition: color 0.2s;
}
.link-drafts:hover {
  color: rgba(201, 168, 106, 0.9);
}

.btn-leave {
  background: transparent;
  border: none;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.4);
  cursor: pointer;
  transition: color 0.2s;
}
.btn-leave:hover {
  color: rgba(201, 168, 106, 0.9);
}

/* 플롯 피드백 */
.plot-feedback-area {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid rgba(201, 168, 106, 0.1);
  padding-top: 16px;
}
.btn-feedback {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 1px solid rgba(201, 168, 106, 0.35);
  border-radius: 999px;
  padding: 8px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  color: #c9a86a;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-feedback:hover:not(:disabled) {
  background: rgba(201, 168, 106, 0.1);
}
.btn-feedback:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 저장 모달 */
.save-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(10, 7, 4, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.save-modal {
  background: #221a10;
  border: 1px solid rgba(201, 168, 106, 0.3);
  border-radius: 14px;
  padding: 28px 32px;
  width: 100%;
  max-width: 400px;
  animation: fadeUp 0.25s ease both;
}
.save-modal-label {
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  letter-spacing: 0;
  font-weight: 700;
  color: rgba(201, 168, 106, 0.6);
  margin: 0 0 10px;
}
.save-modal-input {
  width: 100%;
  background: rgba(201, 168, 106, 0.07);
  border: 1px solid rgba(201, 168, 106, 0.2);
  border-radius: 8px;
  padding: 11px 14px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #f3ecdc;
  outline: none;
  box-sizing: border-box;
  margin-bottom: 18px;
  transition: border-color 0.15s;
}
.save-modal-input:focus {
  border-color: rgba(201, 168, 106, 0.5);
}
.save-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.btn-modal-cancel {
  background: transparent;
  border: 1px solid rgba(243, 236, 220, 0.15);
  border-radius: 999px;
  padding: 8px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  color: rgba(243, 236, 220, 0.5);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-modal-cancel:hover {
  border-color: rgba(243, 236, 220, 0.3);
  color: rgba(243, 236, 220, 0.8);
}
.btn-modal-confirm {
  background: #c9a86a;
  border: none;
  border-radius: 999px;
  padding: 8px 24px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  font-weight: 700;
  color: #1a150f;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-modal-confirm:hover {
  background: #e0bc7a;
}

/* modal 트랜지션 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* 트랜지션 */
.studio-fade-enter-active {
  animation: fadeUp 0.65s ease both;
}
.studio-fade-leave-active {
  transition:
    opacity 0.3s,
    transform 0.3s;
}
.studio-fade-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
