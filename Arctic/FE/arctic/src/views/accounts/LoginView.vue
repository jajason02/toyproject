<script setup>
/**
 * LoginView.vue — Arctic 디자인 적용 완성본
 *
 * [설치 필요] index.html <head>에 폰트 추가:
 * <link rel="preconnect" href="https://fonts.googleapis.com">
 * <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
 * <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/api/accounts'

const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    await login({
      email: email.value,
      password: password.value,
    })
    router.push(route.query.redirect || { name: 'books' })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <RouterLink class="login-brand" to="/">Arctic</RouterLink>
      <div class="login-divider"></div>

      <h1 class="login-heading">다시 만나서 반가워요.</h1>
      <p class="login-sub">서재에서 기다리고 있었어요.</p>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-field">
          <label class="form-label" for="email">이메일</label>
          <input
            id="email"
            v-model="email"
            class="form-input"
            type="email"
            placeholder="name@email.com"
            autocomplete="email"
          />
        </div>

        <div class="form-field">
          <label class="form-label" for="password">비밀번호</label>
          <input
            id="password"
            v-model="password"
            class="form-input"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
          />
        </div>

        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

        <button class="btn-primary" type="submit" :disabled="isLoading">
          {{ isLoading ? '로그인 중...' : '로그인' }}
        </button>
      </form>

      <p class="login-switch">
        처음이신가요?
        <RouterLink to="/signup">회원가입</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.08);
  border-radius: 16px;
  padding: 44px 48px;
  box-shadow: 0 8px 32px -12px rgba(40, 32, 20, 0.16);
}

.login-brand {
  font-family: 'Newsreader', serif;
  font-size: 21px;
  font-weight: 500;
  color: #262019;
  text-decoration: none;
  display: block;
  margin-bottom: 20px;
}

.login-divider {
  height: 1px;
  background: rgba(40, 32, 20, 0.08);
  margin-bottom: 28px;
}

.login-heading {
  font-size: 26px;
  font-weight: 700;
  color: #262019;
  margin: 0 0 8px;
  line-height: 1.4;
}

.login-sub {
  font-size: 14px;
  color: #9c9079;
  margin: 0 0 28px;
  line-height: 1.6;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.form-label {
  font-size: 13px;
  font-weight: 700;
  color: #6b6253;
  letter-spacing: 0.3px;
}

.form-input {
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 9px;
  padding: 13px 16px;
  background: #fffdf8;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #262019;
  outline: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #1e3a3a;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}

.form-input::placeholder {
  color: #c2b8a4;
}

.form-error {
  font-size: 13px;
  color: #b06a3c;
  margin: 0;
  padding: 11px 14px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 8px;
  border-left: 3px solid #b06a3c;
}

.btn-primary {
  width: 100%;
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 16px;
  font-family: 'Gowun Batang', serif;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}

.btn-primary:hover {
  background: #152a2a;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-switch {
  text-align: center;
  font-size: 14px;
  color: #9c9079;
  margin: 22px 0 0;
}

.login-switch a {
  color: #1e3a3a;
  font-weight: 700;
  text-decoration: none;
  margin-left: 6px;
}

.login-switch a:hover {
  text-decoration: underline;
}
</style>
