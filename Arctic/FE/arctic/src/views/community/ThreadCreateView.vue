<script setup>
/**
 * ThreadCreateView.vue — Arctic 디자인 적용 완성본
 * 로직 기존과 동일
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createThread } from '@/api/community'

const router = useRouter()

const title = ref('')
const content = ref('')
const isSaving = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  isSaving.value = true
  errorMessage.value = ''
  try {
    await createThread({ title: title.value, content: content.value })
    router.push({ name: 'community' })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="thread-create-page">
    <div class="thread-create-inner">
      <header class="create-header">
        <p class="section-label">Community</p>
        <h1>쓰레드 작성</h1>
      </header>

      <form class="thread-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label for="thread-title">제목</label>
          <input
            id="thread-title"
            v-model="title"
            type="text"
            placeholder="이야기의 첫 문장을 정하듯 제목을 적어주세요"
            required
          />
        </div>

        <div class="form-field">
          <label for="thread-content">내용</label>
          <textarea
            id="thread-content"
            v-model="content"
            rows="10"
            placeholder="책을 읽으며 남기고 싶은 생각을 자유롭게 적어주세요"
            required
          />
        </div>

        <div class="form-actions">
          <button type="button" class="secondary-btn" @click="router.push({ name: 'community' })">
            취소
          </button>
          <button
            type="submit"
            class="primary-btn"
            :disabled="isSaving || !title.trim() || !content.trim()"
          >
            {{ isSaving ? '저장 중...' : '작성하기' }}
          </button>
        </div>
      </form>

      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    </div>
  </section>
</template>

<style scoped>
.thread-create-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  color: #262019;
  padding: 48px 0 80px;
}

.thread-create-inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 32px;
}

.create-header {
  margin-bottom: 28px;
}

.section-label {
  margin: 0 0 8px;
  font-family: 'Spline Sans Mono', monospace;
  font-size: 12px;
  color: #8a7d68;
  text-transform: uppercase;
}

.create-header h1 {
  margin: 0;
  font-family: 'Newsreader', serif;
  font-size: 36px;
  font-weight: 400;
}

.thread-form {
  box-sizing: border-box;
  border: 1px solid rgba(40, 32, 20, 0.12);
  border-radius: 8px;
  background: rgba(255, 252, 244, 0.54);
  box-shadow: 0 14px 30px -26px rgba(38, 32, 25, 0.5);
  padding: 26px;
  display: grid;
  gap: 20px;
}

.form-field {
  display: grid;
  gap: 8px;
}

.form-field label {
  color: #4a4337;
  font-size: 14px;
  font-weight: 700;
}

.form-field input,
.form-field textarea {
  box-sizing: border-box;
  min-width: 0;
  width: 100%;
  border: 1px solid rgba(40, 32, 20, 0.16);
  border-radius: 8px;
  background: rgba(255, 252, 244, 0.82);
  color: #262019;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.55;
  padding: 12px 14px;
}

.form-field textarea {
  resize: vertical;
}

.form-field input:focus,
.form-field textarea:focus {
  border-color: #1e3a3a;
  outline: none;
  box-shadow: 0 0 0 3px rgba(30, 58, 58, 0.08);
}

.form-field input::placeholder,
.form-field textarea::placeholder {
  color: #b8ad9a;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.primary-btn,
.secondary-btn {
  min-height: 42px;
  border-radius: 999px;
  padding: 0 20px;
  font-family: inherit;
  font-weight: 700;
  cursor: pointer;
}

.primary-btn {
  border: none;
  background: #1e3a3a;
  color: #f4eedf;
}

.secondary-btn {
  border: 1px solid rgba(40, 32, 20, 0.16);
  background: transparent;
  color: #625846;
}

.primary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.error-text {
  margin-top: 16px;
  color: #a84f31;
}

@media (max-width: 640px) {
  .thread-create-page {
    padding-top: 34px;
  }

  .thread-create-inner {
    padding: 0 20px;
  }

  .thread-form {
    padding: 20px;
  }

  .form-actions {
    flex-direction: column-reverse;
  }
}
</style>
