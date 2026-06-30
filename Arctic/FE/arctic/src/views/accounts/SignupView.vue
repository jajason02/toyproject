<script setup>
/**
 * SignupView.vue — Arctic 디자인 적용 완성본 (2단계 UI)
 *
 * [설치 필요] index.html <head>에 폰트 추가:
 * <link rel="preconnect" href="https://fonts.googleapis.com">
 * <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
 * <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Gowun+Batang:wght@400;700&display=swap" rel="stylesheet">
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { checkEmailAvailability, signup } from '@/api/accounts'
import { fetchGenres } from '@/api/books'

const router = useRouter()

const currentStep = ref(1)
const username = ref('')
const email = ref('')
const password = ref('')
const passwordConfirmation = ref('')
const genres = ref([])
const selectedGenreIds = ref([])
const isLoading = ref(false)
const isCheckingEmail = ref(false)
const isGenreLoading = ref(false)
const errorMessage = ref('')

async function loadGenres() {
  isGenreLoading.value = true
  try {
    genres.value = await fetchGenres()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isGenreLoading.value = false
  }
}

function toggleGenre(id) {
  const idx = selectedGenreIds.value.indexOf(id)
  if (idx === -1) {
    selectedGenreIds.value.push(id)
  } else {
    selectedGenreIds.value.splice(idx, 1)
  }
}

function validateBasicInfo() {
  errorMessage.value = ''
  username.value = username.value.trim()
  email.value = email.value.trim()

  if (!username.value) {
    errorMessage.value = '닉네임을 입력해 주세요.'
    return false
  }
  if (username.value.length > 20) {
    errorMessage.value = '닉네임은 20자 이하로 입력해 주세요.'
    return false
  }
  if (!email.value) {
    errorMessage.value = '이메일을 입력해 주세요.'
    return false
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    errorMessage.value = '올바른 이메일 형식으로 입력해 주세요.'
    return false
  }
  if (!password.value) {
    errorMessage.value = '비밀번호를 입력해 주세요.'
    return false
  }
  if (password.value.length < 8) {
    errorMessage.value = '비밀번호는 최소 8자 이상이어야 합니다.'
    return false
  }
  if (/^\d+$/.test(password.value)) {
    errorMessage.value = '숫자로만 이루어진 비밀번호는 사용할 수 없습니다.'
    return false
  }
  if (!passwordConfirmation.value) {
    errorMessage.value = '비밀번호 확인을 입력해 주세요.'
    return false
  }
  if (password.value !== passwordConfirmation.value) {
    errorMessage.value = '비밀번호가 일치하지 않습니다.'
    return false
  }
  return true
}

async function goToGenreStep() {
  if (!validateBasicInfo()) return

  const checkedEmail = email.value
  isCheckingEmail.value = true
  try {
    const result = await checkEmailAvailability(checkedEmail)
    if (email.value !== checkedEmail) {
      return
    }
    if (!result.available) {
      errorMessage.value = result.message || '이미 사용 중인 이메일입니다.'
      return
    }
    errorMessage.value = ''
    currentStep.value = 2
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isCheckingEmail.value = false
  }
}

function goToBasicStep() {
  errorMessage.value = ''
  currentStep.value = 1
}

async function handleSignup() {
  if (!validateBasicInfo()) {
    currentStep.value = 1
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    await signup({
      username: username.value,
      email: email.value,
      password: password.value,
      preferred_genres: selectedGenreIds.value,
    })
    router.push('/login')
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

onMounted(loadGenres)
</script>

<template>
  <div class="signup-page">
    <div class="signup-card">
      <RouterLink class="signup-brand" to="/">Arctic</RouterLink>
      <div class="signup-divider"></div>

      <!-- 단계 표시 -->
      <div class="step-indicator">
        <span :class="['step-label', { active: currentStep === 1 }]">01 기본 정보</span>
        <span class="step-arrow">→</span>
        <span :class="['step-label', { active: currentStep === 2 }]">02 관심 장르</span>
      </div>

      <form @submit.prevent="handleSignup">
        <!-- 1단계: 기본 정보 -->
        <div v-if="currentStep === 1">
          <h1 class="signup-heading">나를 소개해 주세요.</h1>
          <p class="signup-sub">함께 서재를 만들어 갈 당신을 기다렸어요.</p>

          <div class="form-fields">
            <div class="form-field">
              <label class="form-label" for="username">닉네임</label>
              <input
                id="username"
                v-model="username"
                class="form-input"
                type="text"
                placeholder="서재 주인의 이름"
                autocomplete="username"
                maxlength="20"
                required
              />
            </div>

            <div class="form-field">
              <label class="form-label" for="email">이메일</label>
              <input
                id="email"
                v-model="email"
                class="form-input"
                type="email"
                placeholder="name@email.com"
                autocomplete="email"
                required
              />
            </div>

            <div class="form-field">
              <label class="form-label" for="password">비밀번호</label>
              <input
                id="password"
                v-model="password"
                class="form-input"
                type="password"
                placeholder="8자 이상"
                autocomplete="new-password"
                minlength="8"
                required
              />
            </div>

            <div class="form-field">
              <label class="form-label" for="password-confirmation">비밀번호 확인</label>
              <input
                id="password-confirmation"
                v-model="passwordConfirmation"
                class="form-input"
                type="password"
                placeholder="한 번 더 입력해 주세요"
                autocomplete="new-password"
                required
              />
            </div>

            <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

            <button
              type="button"
              class="btn-primary"
              :disabled="isCheckingEmail"
              @click="goToGenreStep"
            >
              {{ isCheckingEmail ? '이메일 확인 중...' : '다음' }}
              <span v-if="!isCheckingEmail" style="font-family: serif">→</span>
            </button>
          </div>
        </div>

        <!-- 2단계: 관심 장르 -->
        <div v-if="currentStep === 2">
          <h1 class="signup-heading">어떤 책을 좋아하세요?</h1>
          <p class="signup-sub">관심 장르를 골라주세요. 언제든 바꿀 수 있어요.</p>

          <p v-if="isGenreLoading" class="genre-loading">장르를 불러오는 중...</p>

          <div v-else class="genre-grid">
            <button
              v-for="genre in genres"
              :key="genre.id"
              type="button"
              :class="['genre-chip', { selected: selectedGenreIds.includes(genre.id) }]"
              @click="toggleGenre(genre.id)"
            >
              {{ genre.name }}
            </button>
          </div>

          <p class="genre-count">{{ selectedGenreIds.length }}개 선택됨</p>

          <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

          <div class="step-nav">
            <button type="button" class="btn-secondary" @click="goToBasicStep">
              <span style="font-family: serif">←</span> 이전
            </button>
            <button type="submit" class="btn-primary" :disabled="isLoading">
              {{ isLoading ? '가입 중...' : '가입 완료' }}
            </button>
          </div>
        </div>
      </form>

      <p class="signup-switch">
        이미 계정이 있으신가요?
        <RouterLink to="/login">로그인</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.signup-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
}

.signup-card {
  width: 100%;
  max-width: 480px;
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.08);
  border-radius: 16px;
  padding: 44px 48px;
  box-shadow: 0 8px 32px -12px rgba(40, 32, 20, 0.16);
}

.signup-brand {
  font-family: 'Newsreader', serif;
  font-size: 21px;
  font-weight: 500;
  color: #262019;
  text-decoration: none;
  display: block;
  margin-bottom: 20px;
}

.signup-divider {
  height: 1px;
  background: rgba(40, 32, 20, 0.08);
  margin-bottom: 24px;
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 26px;
}

.step-label {
  font-size: 13px;
  font-weight: 700;
  color: #b8ad9a;
  transition: color 0.2s;
}

.step-label.active {
  color: #1e3a3a;
}

.step-arrow {
  font-size: 13px;
  color: #c2b8a4;
}

.signup-heading {
  font-size: 26px;
  font-weight: 700;
  color: #262019;
  margin: 0 0 8px;
  line-height: 1.4;
}

.signup-sub {
  font-size: 14px;
  color: #9c9079;
  margin: 0 0 24px;
  line-height: 1.6;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.genre-loading {
  font-size: 14px;
  color: #9c9079;
  text-align: center;
  padding: 20px 0;
}

.genre-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.genre-chip {
  background: transparent;
  color: #4a4337;
  border: 1.5px solid #d3c9b0;
  border-radius: 999px;
  padding: 10px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.15s;
}

.genre-chip:hover {
  border-color: #1e3a3a;
  color: #1e3a3a;
}

.genre-chip.selected {
  background: #1e3a3a;
  color: #f4eedf;
  border-color: #1e3a3a;
  font-weight: 700;
}

.genre-count {
  font-size: 13px;
  color: #b8ad9a;
  text-align: center;
  margin: 0 0 20px;
}

.btn-primary {
  flex: 2;
  width: 100%;
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 15px;
  font-family: 'Gowun Batang', serif;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 6px;
}

.btn-primary:hover {
  background: #152a2a;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  flex: 1;
  background: transparent;
  color: #6b6253;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  padding: 15px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-secondary:hover {
  background: rgba(40, 32, 20, 0.04);
}

.step-nav {
  display: flex;
  gap: 12px;
}

.signup-switch {
  text-align: center;
  font-size: 14px;
  color: #9c9079;
  margin: 22px 0 0;
}

.signup-switch a {
  color: #1e3a3a;
  font-weight: 700;
  text-decoration: none;
  margin-left: 6px;
}

.signup-switch a:hover {
  text-decoration: underline;
}
</style>
