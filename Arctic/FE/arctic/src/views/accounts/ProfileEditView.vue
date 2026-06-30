<script setup>
/**
 * ProfileEditView.vue — Arctic 디자인 적용 완성본
 * 로직 기존과 동일 (FormData, 이미지 업로드, 장르 체크박스, 비밀번호 변경)
 */
import { onMounted, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { fetchProfile, updateProfile } from '@/api/accounts'
import { fetchGenres } from '@/api/books'
import { isAuthenticated } from '@/api/client'

const router = useRouter()

const username = ref('')
const bio = ref('')
const profileImage = ref('')
const profileImageFile = ref(null)
const profileImagePreview = ref('')
const genres = ref([])
const selectedGenreIds = ref([])
const currentPassword = ref('')
const newPassword = ref('')
const newPasswordConfirmation = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

function handleProfileImageChange(event) {
  const file = event.target.files[0] || null
  profileImageFile.value = file
  if (file) {
    profileImagePreview.value = URL.createObjectURL(file)
  }
}

function toggleGenre(id) {
  const idx = selectedGenreIds.value.indexOf(id)
  if (idx === -1) selectedGenreIds.value.push(id)
  else selectedGenreIds.value.splice(idx, 1)
}

async function loadProfileEditData() {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [profile, genreList] = await Promise.all([fetchProfile(), fetchGenres()])
    username.value = profile.username || ''
    bio.value = profile.bio || ''
    profileImage.value = profile.profile_image || ''
    selectedGenreIds.value = (profile.preferred_genres || []).map((g) => g.id)
    genres.value = genreList
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  errorMessage.value = ''
  successMessage.value = ''

  if (newPassword.value && newPassword.value !== newPasswordConfirmation.value) {
    errorMessage.value = '새 비밀번호가 일치하지 않습니다.'
    return
  }

  isSaving.value = true
  const payload = new FormData()
  payload.append('username', username.value)
  payload.append('bio', bio.value)
  if (profileImageFile.value) payload.append('profile_image', profileImageFile.value)
  selectedGenreIds.value.forEach((id) => payload.append('preferred_genres', String(id)))
  if (currentPassword.value || newPassword.value) {
    payload.append('current_password', currentPassword.value)
    payload.append('new_password', newPassword.value)
  }

  try {
    await updateProfile(payload)
    router.push({ name: 'profile' })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isSaving.value = false
  }
}

onMounted(loadProfileEditData)
</script>

<template>
  <div class="edit-page">
    <div class="edit-inner">
      <div class="page-header">
        <RouterLink :to="{ name: 'profile' }" class="back-link">← 프로필</RouterLink>
        <h1 class="page-title">프로필 수정</h1>
      </div>

      <div v-if="isLoading" class="loading-msg">불러오는 중...</div>

      <form v-else novalidate class="edit-form" @submit.prevent="handleSubmit">
        <!-- ── 프로필 이미지 ── -->
        <div class="section-card">
          <h2 class="section-title">프로필 사진</h2>
          <div class="avatar-edit-row">
            <div class="avatar-preview-wrap">
              <img
                v-if="profileImagePreview || profileImage"
                :src="profileImagePreview || profileImage"
                alt="프로필 사진"
                class="avatar-preview"
              />
              <div v-else class="avatar-preview avatar-fallback">
                {{ username?.[0]?.toUpperCase() }}
              </div>
            </div>
            <div class="avatar-edit-info">
              <p class="avatar-hint">JPG, PNG 권장 · 최대 5MB</p>
              <label class="btn-upload" for="profile-image-input">사진 변경</label>
              <input
                id="profile-image-input"
                type="file"
                accept="image/*"
                class="file-input-hidden"
                @change="handleProfileImageChange"
              />
            </div>
          </div>
        </div>

        <!-- ── 기본 정보 ── -->
        <div class="section-card">
          <h2 class="section-title">기본 정보</h2>

          <div class="form-field">
            <label class="form-label" for="username">닉네임</label>
            <input
              id="username"
              v-model="username"
              class="form-input"
              type="text"
              autocomplete="username"
              placeholder="서재 주인의 이름"
            />
          </div>

          <div class="form-field">
            <label class="form-label" for="bio">소개</label>
            <textarea
              id="bio"
              v-model="bio"
              class="form-textarea"
              placeholder="나를 한 줄로 소개해 주세요."
              rows="3"
            ></textarea>
          </div>
        </div>

        <!-- ── 관심 장르 ── -->
        <div class="section-card">
          <h2 class="section-title">관심 장르</h2>
          <p class="section-sub">좋아하는 장르를 골라주세요.</p>
          <div class="genre-grid">
            <button
              v-for="genre in genres"
              :key="genre.id"
              type="button"
              :class="['genre-chip', { active: selectedGenreIds.includes(genre.id) }]"
              @click="toggleGenre(genre.id)"
            >
              {{ genre.name }}
            </button>
          </div>
        </div>

        <!-- ── 비밀번호 변경 ── -->
        <div class="section-card">
          <h2 class="section-title">비밀번호 변경</h2>
          <p class="section-sub">변경하지 않으려면 비워두세요.</p>

          <div class="form-field">
            <label class="form-label" for="current-password">현재 비밀번호</label>
            <input
              id="current-password"
              v-model="currentPassword"
              class="form-input"
              type="password"
              autocomplete="current-password"
              placeholder="현재 비밀번호를 입력해 주세요"
            />
          </div>

          <div class="form-field">
            <label class="form-label" for="new-password">새 비밀번호</label>
            <input
              id="new-password"
              v-model="newPassword"
              class="form-input"
              type="password"
              autocomplete="new-password"
              placeholder="8자 이상"
            />
          </div>

          <div class="form-field">
            <label class="form-label" for="new-password-confirmation">새 비밀번호 확인</label>
            <input
              id="new-password-confirmation"
              v-model="newPasswordConfirmation"
              class="form-input"
              type="password"
              autocomplete="new-password"
              placeholder="한 번 더 입력해 주세요"
            />
          </div>
        </div>

        <!-- 에러 / 성공 -->
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="form-success">{{ successMessage }}</p>

        <!-- 하단 버튼 -->
        <div class="form-actions">
          <RouterLink :to="{ name: 'profile' }" class="btn-cancel">취소</RouterLink>
          <button class="btn-save" type="submit" :disabled="isSaving">
            {{ isSaving ? '저장 중...' : '저장하기' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.edit-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 52px 0 80px;
}

.edit-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 0 32px;
}

.back-link {
  display: inline-block;
  font-size: 14px;
  color: #9c9079;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.15s;
}
.back-link:hover {
  color: #1e3a3a;
}

.page-title {
  font-family: 'Newsreader', serif;
  font-size: 34px;
  font-weight: 400;
  margin: 0 0 36px;
  letter-spacing: -0.5px;
}

.loading-msg {
  font-size: 15px;
  color: #9c9079;
  padding: 40px 0;
  text-align: center;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 섹션 카드 */
.section-card {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.1);
  border-radius: 16px;
  padding: 28px 32px;
}

.section-title {
  font-family: 'Newsreader', serif;
  font-size: 19px;
  font-weight: 400;
  color: #262019;
  margin: 0 0 18px;
}

.section-sub {
  font-size: 13.5px;
  color: #9c9079;
  margin: -10px 0 18px;
}

/* 아바타 */
.avatar-edit-row {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar-preview-wrap {
  flex-shrink: 0;
}
.avatar-preview {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(40, 32, 20, 0.1);
}
.avatar-fallback {
  background: #1e3a3a;
  color: #f4eedf;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Newsreader', serif;
  font-size: 28px;
}

.avatar-hint {
  font-size: 12.5px;
  color: #b8ad9a;
  margin: 0 0 12px;
}

.btn-upload {
  display: inline-block;
  border: 1px solid rgba(40, 32, 20, 0.2);
  border-radius: 999px;
  padding: 9px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 13.5px;
  color: #4a4337;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-upload:hover {
  background: rgba(40, 32, 20, 0.05);
}

.file-input-hidden {
  display: none;
}

/* 폼 필드 */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 16px;
}
.form-field:last-of-type {
  margin-bottom: 0;
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
  border-radius: 10px;
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

.form-textarea {
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 10px;
  padding: 13px 16px;
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
  line-height: 1.8;
}
.form-textarea:focus {
  border-color: #1e3a3a;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}
.form-textarea::placeholder {
  color: #c2b8a4;
}

/* 장르 */
.genre-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.genre-chip {
  background: transparent;
  color: #4a4337;
  border: 1.5px solid #d3c9b0;
  border-radius: 999px;
  padding: 9px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 14.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.genre-chip:hover {
  border-color: #1e3a3a;
  color: #1e3a3a;
}
.genre-chip.active {
  background: #1e3a3a;
  border-color: #1e3a3a;
  color: #f4eedf;
  font-weight: 700;
}

/* 에러/성공 */
.form-error {
  font-size: 13px;
  color: #b06a3c;
  padding: 12px 16px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 9px;
  border-left: 3px solid #b06a3c;
  margin: 0;
}
.form-success {
  font-size: 13px;
  color: #3f6b5f;
  padding: 12px 16px;
  background: rgba(63, 107, 95, 0.08);
  border-radius: 9px;
  border-left: 3px solid #3f6b5f;
  margin: 0;
}

/* 하단 버튼 */
.form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 4px;
}

.btn-cancel {
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  color: #9c9079;
  text-decoration: none;
  padding: 13px 24px;
  border: 1px solid rgba(40, 32, 20, 0.15);
  border-radius: 999px;
  transition: background 0.15s;
}
.btn-cancel:hover {
  background: rgba(40, 32, 20, 0.04);
}

.btn-save {
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 13px 34px;
  font-family: 'Gowun Batang', serif;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-save:hover {
  background: #152a2a;
}
.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
