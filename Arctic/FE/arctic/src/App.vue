<script setup>
/**
 * App.vue — Arctic 디자인 적용 완성본
 * 스크립트 로직은 기존과 완전히 동일합니다.
 */
import { onBeforeUnmount, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { logout } from '@/api/accounts'
import { clearTokens, isAuthenticated } from '@/api/client'

const router = useRouter()
const isLoggedIn = ref(isAuthenticated())

function refreshLoginState() {
  isLoggedIn.value = isAuthenticated()
}

async function handleLogout() {
  try {
    await logout({})
  } finally {
    clearTokens()
    refreshLoginState()
    router.push('/login')
  }
}

const removeRouterHook = router.afterEach(refreshLoginState)

onBeforeUnmount(() => {
  removeRouterHook()
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="header-inner">
        <RouterLink class="brand" :to="{ name: isLoggedIn ? 'books' : 'landing' }">Arctic</RouterLink>

        <nav class="nav-center">
          <RouterLink :to="{ name: 'books' }" class="nav-link">도서</RouterLink>
          <RouterLink :to="{ name: 'community' }" class="nav-link">커뮤니티</RouterLink>
          <RouterLink :to="{ name: 'studio' }" class="nav-link">AI 창작</RouterLink>
          <RouterLink :to="{ name: 'studio-drafts' }" class="nav-link">내 창작물</RouterLink>
          <RouterLink :to="{ name: 'recommendations' }" class="nav-link">
            추천
          </RouterLink>
        </nav>

        <div class="nav-right">
          <template v-if="isLoggedIn">
            <RouterLink :to="{ name: 'profile' }" class="nav-link">프로필</RouterLink>
            <button type="button" class="btn-logout" @click="handleLogout">로그아웃</button>
          </template>
          <template v-else>
            <RouterLink :to="{ name: 'login' }" class="nav-link">로그인</RouterLink>
            <RouterLink :to="{ name: 'signup' }" class="btn-signup">회원가입</RouterLink>
          </template>
        </div>
      </div>
    </header>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/* ── 전체 껍데기 ── */
.app-shell {
  min-height: 100vh;
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
}

/* ── 헤더 ── */
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: rgba(244, 238, 223, 0.82);
  border-bottom: 1px solid rgba(40, 32, 20, 0.07);
}

.header-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 32px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

/* ── 브랜드 ── */
.brand {
  font-family: 'Newsreader', serif;
  font-size: 22px;
  font-weight: 500;
  color: #262019;
  text-decoration: none;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}

/* ── 센터 내비 ── */
.nav-center {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-link {
  font-size: 14.5px;
  color: #4a4337;
  text-decoration: none;
  transition: color 0.15s;
  white-space: nowrap;
}

.nav-link:hover {
  color: #1e3a3a;
}

/* Vue Router 활성 링크 */
.nav-link.router-link-active {
  color: #1e3a3a;
  font-weight: 700;
}

/* 아직 준비 중인 메뉴 */
.nav-soon {
  color: #c2b8a4;
  cursor: default;
}

/* ── 오른쪽 영역 ── */
.nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}

.btn-logout {
  background: transparent;
  border: none;
  padding: 0;
  font-family: 'Gowun Batang', serif;
  font-size: 14.5px;
  color: #9c9079;
  cursor: pointer;
  transition: color 0.15s;
}

.btn-logout:hover {
  color: #b06a3c;
}

.btn-signup {
  background: #1e3a3a;
  color: #f4eedf;
  border-radius: 999px;
  padding: 9px 22px;
  font-family: 'Gowun Batang', serif;
  font-size: 14.5px;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.15s;
  white-space: nowrap;
}

.btn-signup:hover {
  background: #152a2a;
}

/* ── 메인 ── */
.app-main {
  min-height: calc(100vh - 64px);
}
</style>
