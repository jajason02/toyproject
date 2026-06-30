<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { isAuthenticated } from '@/api/client'

const router = useRouter()
const showLanding = ref(false)

onMounted(() => {
  if (isAuthenticated()) {
    router.replace({ name: 'books' })
    return
  }
  setTimeout(() => {
    showLanding.value = true
  }, 80)
})

const mockBooks = [
  {
    title: '데미안',
    author: '헤르만 헤세',
    rating: '4.6',
    cover: 'https://image.aladin.co.kr/product/9871/8/cover500/k042535550_2.jpg',
  },
  {
    title: '1984',
    author: '조지 오웰',
    rating: '4.8',
    cover: 'https://image.aladin.co.kr/product/24555/31/cover500/s642937439_1.jpg',
  },
  {
    title: '노르웨이의 숲',
    author: '무라카미 하루키',
    rating: '4.4',
    cover: 'https://image.aladin.co.kr/product/11561/49/cover500/8937434482_1.jpg',
  },
  {
    title: '코스모스',
    author: '칼 세이건',
    rating: '4.9',
    cover: 'https://image.aladin.co.kr/product/87/9/cover500/s922637499_3.jpg',
  },
  {
    title: '사피엔스',
    author: '유발 하라리',
    rating: '4.7',
    cover: 'https://image.aladin.co.kr/product/25686/5/cover500/8934991321_1.jpg',
  },
  {
    title: '토지',
    author: '박경리',
    rating: '4.5',
    cover: 'https://image.aladin.co.kr/product/31830/63/cover500/k442833125_1.jpg',
  },
]

const studioIdeas = [
  {
    num: '01',
    title: '마지막 우편배달부',
    desc: '통신이 끊긴 행성에서, 종이 편지만을 나르는 이의 마지막 배달 여정.',
  },
  {
    num: '02',
    title: '고요의 궤도',
    desc: '홀로 궤도를 도는 관측원이 수신한, 30년 전 자신의 목소리.',
  },
  {
    num: '03',
    title: '별빛 도서관',
    desc: '빛으로만 책을 쓰는 문명, 그 마지막 사서가 남긴 한 권.',
  },
]
</script>

<template>
  <Transition name="landing-fade">
    <div v-if="showLanding" class="landing">
    <!-- HERO -->
    <section class="hero">
      <div class="hero-glow"></div>
      <div class="hero-content">
        <p class="hero-label">READ · COLLECT · WRITE</p>
        <h1 class="hero-title">Arctic</h1>
        <div class="hero-divider"></div>
        <p class="hero-sub">나만의 서재를 관리하고,<br />나만의 이야기를 써 내려가세요.</p>
        <RouterLink :to="{ name: 'signup' }" class="btn-hero">시작하기 →</RouterLink>
      </div>
      <div class="hero-scroll">
        <span class="scroll-label">scroll</span>
        <span class="scroll-arrow">↓</span>
      </div>
    </section>

    <!-- 01 서재 -->
    <section class="feature-section bg-default">
      <div class="feature-inner">
        <div class="feature-text">
          <div class="feature-eyebrow"><span class="eyebrow-line"></span>서재</div>
          <h2 class="feature-heading">읽은 책이 쌓여,<br />나만의 서재가 됩니다.</h2>
          <p class="feature-desc">
            장르로 둘러보고, 별점과 한 줄 감상을 남기세요.<br />흩어진 독자들의 평점이 모여, 한 권의
            온도가 됩니다.
          </p>
          <ul class="feature-bullets">
            <li>별점·한 줄 리뷰로 책의 감상을 기록</li>
            <li>장르 필터와 평점·최신 정렬</li>
            <li>평균 평점 자동 집계</li>
          </ul>
          <RouterLink :to="{ name: 'books' }" class="feature-link">도서 둘러보기 →</RouterLink>
        </div>
        <div class="mockup-wrap">
          <div class="browser-chrome">
            <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
            <div class="address-bar">arctic.app/books</div>
          </div>
          <div class="mockup-body">
            <div class="mock-row between mb16">
              <span class="mock-serif lg">둘러보기</span>
              <span class="mock-mono sm muted">평점순 ▾</span>
            </div>
            <div class="chip-row mb20">
              <span class="chip active">전체</span>
              <span class="chip">소설</span><span class="chip">에세이</span>
              <span class="chip">인문</span><span class="chip">과학</span>
            </div>
            <div class="book-grid-mini">
              <div v-for="b in mockBooks" :key="b.title" class="mini-card">
                <img :src="b.cover" :alt="b.title" class="mini-cover" />
                <p class="mini-title">{{ b.title }}</p>
                <p class="mini-author">{{ b.author }}</p>
                <p class="mini-rating">★ {{ b.rating }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 02 감상 분석 -->
    <section class="feature-section bg-tint">
      <div class="feature-inner reverse">
        <div class="feature-text">
          <div class="feature-eyebrow"><span class="eyebrow-line"></span>감상 분석</div>
          <h2 class="feature-heading">수많은 감상을,<br />한 문장으로 읽다.</h2>
          <p class="feature-desc">
            한 책에 쌓인 모든 리뷰를 AI가 읽고, 긍정과 부정의 결, 함께 떠오른 키워드, 그리고 전체를
            관통하는 한 줄을 건넵니다.
          </p>
          <ul class="feature-bullets">
            <li>긍정·중립·부정 비율</li>
            <li>공통 키워드 5개 추출</li>
            <li>전체 반응 한 줄 요약</li>
          </ul>
        </div>
        <div class="mockup-wrap">
          <div class="browser-chrome">
            <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
            <div class="address-bar">arctic.app/books/데미안</div>
          </div>
          <div class="mockup-body">
            <div class="ai-panel">
              <div class="ai-panel-header"><span class="ai-dot"></span>AI 감상 분석</div>
              <div class="sentiment-bar">
                <div class="bar-pos" style="width: 68%"></div>
                <div class="bar-neu" style="width: 22%"></div>
                <div class="bar-neg" style="width: 10%"></div>
              </div>
              <div class="sentiment-legend">
                <span><i class="ldot pos"></i>긍정 68%</span>
                <span><i class="ldot neu"></i>중립 22%</span>
                <span><i class="ldot neg"></i>부정 10%</span>
              </div>
              <div class="kw-row">
                <span v-for="kw in ['성장', '자아', '고독', '상징', '내면']" :key="kw" class="kw"
                  ># {{ kw }}</span
                >
              </div>
              <p class="ai-quote">
                독자들은 성장과 자아의 발견에 깊이 공감하며, 상징으로 가득한 내면 묘사를 가장 큰
                울림으로 꼽았습니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 03 창작 스튜디오 -->
    <section class="feature-section bg-dark">
      <div class="feature-inner centered">
        <div class="feature-text center">
          <div class="feature-eyebrow light">
            <span class="eyebrow-line light"></span>창작 스튜디오
          </div>
          <h2 class="feature-heading light">당신의 첫 문장을,<br />함께 씁니다.</h2>
          <p class="feature-desc light">
            장르와 키워드만 건네면 이야기의 씨앗이 돋아납니다. 아이디어를 플롯으로, 문장을 더
            단단하게 — 대화하듯 다듬어 가세요.
          </p>
        </div>
        <div class="studio-cards">
          <div v-for="idea in studioIdeas" :key="idea.num" class="studio-card">
            <span class="idea-num">{{ idea.num }}</span>
            <p class="idea-title">{{ idea.title }}</p>
            <p class="idea-desc">{{ idea.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CLOSING CTA -->
    <footer class="landing-footer">
      <p class="closing-quote">이야기는, 한 권에서 시작됩니다.</p>
      <RouterLink :to="{ name: 'signup' }" class="btn-hero">Arctic 시작하기 →</RouterLink>
      <div class="footer-bottom">
        <span class="footer-brand">Arctic</span>
        <div class="footer-links">
          <RouterLink :to="{ name: 'books' }">도서</RouterLink>
          <RouterLink :to="{ name: 'community' }">커뮤니티</RouterLink>
        </div>
        <span class="footer-copy">© 2026 Arctic</span>
      </div>
    </footer>
  </div>
  </Transition>
</template>

<style scoped>
@keyframes landingFadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.landing-fade-enter-active {
  animation: landingFadeUp 0.65s ease both;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0) translateX(-50%);
  }
  50% {
    transform: translateY(8px) translateX(-50%);
  }
}

.landing {
  font-family: 'Gowun Batang', serif;
  color: #262019;
  overflow-x: hidden;
}

/* ── HERO ── */
.hero {
  min-height: 88vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background: radial-gradient(125% 85% at 50% -5%, #fbf6ea 0%, #f3ecda 58%, #ebe1cc 100%);
  position: relative;
  padding: 80px 24px 100px;
}

.hero-glow {
  position: absolute;
  width: 560px;
  height: 560px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(241, 224, 182, 0.5) 0%, transparent 68%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -60%);
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero-label {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 13px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #1e3a3a;
  margin: 0 0 26px;
}

.hero-title {
  font-family: 'Newsreader', serif;
  font-size: clamp(72px, 10vw, 118px);
  font-weight: 400;
  line-height: 0.92;
  letter-spacing: -1px;
  margin: 0;
}

.hero-divider {
  width: 52px;
  height: 1px;
  background: #1e3a3a;
  margin: 32px 0 26px;
}

.hero-sub {
  font-size: clamp(17px, 2vw, 21px);
  line-height: 1.9;
  color: #5c5444;
  margin: 0;
  text-wrap: pretty;
}

.btn-hero {
  margin-top: 44px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: #1e3a3a;
  color: #f4eedf;
  font-family: 'Gowun Batang', serif;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 17px 46px;
  border-radius: 999px;
  text-decoration: none;
  transition: background 0.15s;
}
.btn-hero:hover {
  background: #152a2a;
}

.hero-scroll {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  animation: float 2.6s ease-in-out infinite;
}
.scroll-label {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #9c9079;
}
.scroll-arrow {
  color: #9c9079;
  font-size: 17px;
}

/* ── FEATURE SECTIONS ── */
.feature-section {
  padding: 100px 32px;
}
.bg-default {
  background: #f4eedf;
}
.bg-tint {
  background: #efe7d3;
}
.bg-dark {
  background: radial-gradient(95% 75% at 50% 0%, #1c3b39 0%, #143230 52%, #0e2421 100%);
}

.feature-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  gap: 64px;
  align-items: center;
}
.feature-inner.reverse {
  flex-direction: row-reverse;
}
.feature-inner.centered {
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 48px;
}

.feature-text {
  flex: 1;
  max-width: 400px;
}
.feature-text.center {
  max-width: 600px;
}

.feature-eyebrow {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: 'Gowun Batang', serif;
  font-size: 17px;
  font-weight: 700;
  color: #1e3a3a;
  margin-bottom: 22px;
}
.feature-eyebrow.light {
  color: #c9a86a;
}

.eyebrow-line {
  display: inline-block;
  width: 24px;
  height: 1.5px;
  background: #1e3a3a;
  flex-shrink: 0;
}
.eyebrow-line.light {
  background: #c9a86a;
}

.feature-heading {
  font-size: clamp(28px, 3vw, 38px);
  line-height: 1.35;
  font-weight: 700;
  margin: 0 0 20px;
  letter-spacing: -0.5px;
}
.feature-heading.light {
  color: #f3ecdc;
}

.feature-desc {
  font-size: 16px;
  line-height: 1.9;
  color: #5c5444;
  margin: 0 0 24px;
  text-wrap: pretty;
}
.feature-desc.light {
  color: #c8bda6;
}

.feature-bullets {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.feature-bullets li {
  font-size: 14.5px;
  color: #4a4337;
  padding-left: 18px;
  position: relative;
}
.feature-bullets li::before {
  content: '—';
  position: absolute;
  left: 0;
  color: #1e3a3a;
}

.feature-link {
  font-size: 14.5px;
  font-weight: 700;
  color: #1e3a3a;
  text-decoration: none;
}
.feature-link:hover {
  text-decoration: underline;
}

/* ── MOCKUP ── */
.mockup-wrap {
  flex: 1.3;
  min-width: 0;
  border-radius: 13px;
  overflow: hidden;
  box-shadow: 0 30px 60px -20px rgba(40, 32, 20, 0.38);
  border: 1px solid rgba(40, 32, 20, 0.08);
}

.browser-chrome {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 11px 16px;
  background: #eae0cb;
  border-bottom: 1px solid rgba(40, 32, 20, 0.06);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.r {
  background: #cf9a86;
}
.dot.y {
  background: #d9c08a;
}
.dot.g {
  background: #a9bd9a;
}
.address-bar {
  margin-left: 12px;
  flex: 1;
  max-width: 260px;
  background: #f4eedf;
  border-radius: 6px;
  padding: 5px 12px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  color: #857a64;
}

.mockup-body {
  background: #fbf7ee;
  padding: 22px 22px 26px;
}

.mock-row {
  display: flex;
}
.between {
  justify-content: space-between;
}
.mb16 {
  margin-bottom: 16px;
}
.mb20 {
  margin-bottom: 20px;
}
.mock-serif {
  font-family: 'Newsreader', serif;
}
.lg {
  font-size: 20px;
}
.mock-mono {
  font-family: 'Spline Sans Mono', monospace;
}
.sm {
  font-size: 11px;
}
.muted {
  color: #9c9079;
  align-self: flex-end;
}

.chip-row {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.chip {
  border: 1px solid #d8ccb2;
  color: #6b6253;
  font-size: 12px;
  padding: 5px 13px;
  border-radius: 999px;
}
.chip.active {
  background: #1e3a3a;
  border-color: #1e3a3a;
  color: #f4eedf;
  font-weight: 700;
}

.book-grid-mini {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.mini-card {
  display: flex;
  flex-direction: column;
}
.mini-cover {
  width: 100%;
  aspect-ratio: 2/3;
  object-fit: cover;
  border-radius: 5px;
  margin-bottom: 7px;
  box-shadow: 0 3px 10px -4px rgba(40, 32, 20, 0.28);
}
.mini-title {
  font-family: 'Newsreader', serif;
  font-size: 13px;
  line-height: 1.3;
  margin: 0 0 3px;
}
.mini-author {
  font-size: 11px;
  color: #9c9079;
  margin: 0 0 3px;
}
.mini-rating {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  color: #b08a3c;
  margin: 0;
}

/* AI panel */
.ai-panel {
  background: #fffdf8;
  border: 1px solid #e7dcc4;
  border-radius: 11px;
  padding: 18px 20px;
}
.ai-panel-header {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #1e3a3a;
  margin-bottom: 14px;
}
.ai-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1e3a3a;
}
.sentiment-bar {
  height: 9px;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  margin-bottom: 9px;
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
  gap: 14px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 10.5px;
  color: #6b6253;
  margin-bottom: 14px;
}
.ldot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 4px;
}
.ldot.pos {
  background: #3f6b5f;
}
.ldot.neu {
  background: #c8b78d;
}
.ldot.neg {
  background: #b06a3c;
}
.kw-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.kw {
  background: #ede3cf;
  color: #4a4337;
  font-size: 12px;
  padding: 4px 11px;
  border-radius: 999px;
}
.ai-quote {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-size: 14px;
  line-height: 1.6;
  color: #3a342a;
  margin: 0;
  border-left: 2px solid #1e3a3a;
  padding-left: 12px;
}

/* Studio cards */
.studio-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 900px;
  width: 100%;
}
.studio-card {
  background: #fbf7ee;
  border-radius: 12px;
  padding: 22px;
  text-align: left;
}
.idea-num {
  font-family: 'Newsreader', serif;
  font-size: 15px;
  color: #1e3a3a;
  display: block;
  margin-bottom: 10px;
}
.idea-title {
  font-size: 15px;
  font-weight: 700;
  color: #262019;
  margin: 0 0 8px;
}
.idea-desc {
  font-size: 13px;
  line-height: 1.7;
  color: #6b6253;
  margin: 0;
}

/* ── FOOTER ── */
.landing-footer {
  background: #efe7d3;
  border-top: 1px solid rgba(40, 32, 20, 0.08);
  padding: 90px 32px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.closing-quote {
  font-family: 'Newsreader', serif;
  font-style: italic;
  font-size: clamp(24px, 3vw, 34px);
  line-height: 1.4;
  color: #3a342a;
  margin: 0 0 32px;
}

.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1100px;
  margin-top: 72px;
  padding-top: 28px;
  border-top: 1px solid rgba(40, 32, 20, 0.1);
  flex-wrap: wrap;
  gap: 14px;
}

.footer-brand {
  font-family: 'Newsreader', serif;
  font-size: 20px;
  color: #262019;
}

.footer-links {
  display: flex;
  gap: 24px;
}
.footer-links a {
  font-size: 13.5px;
  color: #6b6253;
  text-decoration: none;
}
.footer-links a:hover {
  color: #1e3a3a;
}

.footer-copy {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
  color: #9c9079;
}

/* 반응형 */
@media (max-width: 860px) {
  .feature-inner,
  .feature-inner.reverse {
    flex-direction: column;
  }
  .feature-text {
    max-width: 100%;
  }
  .studio-cards {
    grid-template-columns: 1fr;
  }
  .book-grid-mini {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
