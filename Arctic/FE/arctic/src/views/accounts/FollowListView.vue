<script setup>
/**
 * FollowListView.vue — Arctic 디자인 적용 완성본
 * 로직 기존과 동일
 */
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { fetchFollowers, fetchFollowing, fetchProfile, toggleFollow } from '@/api/accounts'
import { isAuthenticated } from '@/api/client'

const route = useRoute()
const router = useRouter()

const users = ref([])
const profile = ref(null)
const currentUser = ref(null)
const isLoading = ref(false)
const loadingUserId = ref(null)
const errorMessage = ref('')

const profileUserId = computed(() => route.params.userId || null)
const listType = computed(() => (route.query.tab === 'following' ? 'following' : 'followers'))
const followerCount = computed(() => profile.value?.follower_count || 0)
const followingCount = computed(() => profile.value?.following_count || 0)
const followListPath = computed(() =>
  profileUserId.value ? `/profile/${profileUserId.value}/follows` : '/profile/follows',
)

function getInitial(user) {
  return (user.username || 'A').trim().charAt(0).toUpperCase()
}

function switchListType(type) {
  router.push({ path: followListPath.value, query: { tab: type } })
}

async function loadUsers() {
  if (!isAuthenticated()) {
    router.push('/login')
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  try {
    currentUser.value = await fetchProfile()
    profile.value = await fetchProfile(profileUserId.value)
    users.value =
      listType.value === 'following'
        ? await fetchFollowing(profileUserId.value)
        : await fetchFollowers(profileUserId.value)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

function isCurrentUser(user) {
  return currentUser.value?.id === user.id
}

async function handleFollowToggle(user) {
  loadingUserId.value = user.id
  errorMessage.value = ''
  try {
    const result = await toggleFollow(user.id)
    user.is_following = result.is_following
    if (!profileUserId.value) {
      profile.value = { ...profile.value, following_count: result.following_count }
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loadingUserId.value = null
  }
}

onMounted(loadUsers)
watch(() => route.fullPath, loadUsers)
</script>

<template>
  <div class="follow-page">
    <div class="follow-inner">
      <!-- 뒤로 가기 -->
      <RouterLink :to="profileUserId ? `/profile/${profileUserId}` : '/profile'" class="back-link"
        >← 프로필</RouterLink
      >

      <!-- 탭 헤더 -->
      <div class="tab-header">
        <button
          :class="['tab-btn', { active: listType === 'followers' }]"
          type="button"
          @click="switchListType('followers')"
        >
          팔로워
          <span class="tab-count">{{ followerCount }}</span>
        </button>
        <button
          :class="['tab-btn', { active: listType === 'following' }]"
          type="button"
          @click="switchListType('following')"
        >
          팔로잉
          <span class="tab-count">{{ followingCount }}</span>
        </button>
      </div>

      <!-- 에러 -->
      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 로딩 -->
      <div v-else-if="isLoading" class="user-list">
        <div v-for="n in 5" :key="n" class="user-card skeleton">
          <div class="sk-avatar"></div>
          <div class="sk-info">
            <div class="sk-line w50"></div>
            <div class="sk-line w30"></div>
          </div>
        </div>
      </div>

      <!-- 빈 상태 -->
      <div v-else-if="users.length === 0" class="empty-state">
        <p class="empty-title">
          {{ listType === 'following' ? '팔로잉이 없어요.' : '팔로워가 없어요.' }}
        </p>
        <p class="empty-sub">
          {{
            listType === 'following'
              ? '관심 있는 독자를 팔로우해 보세요.'
              : '아직 이 계정을 팔로우하는 사람이 없어요.'
          }}
        </p>
      </div>

      <!-- 유저 목록 -->
      <div v-else class="user-list">
        <div v-for="user in users" :key="user.id" class="user-card">
          <RouterLink :to="`/profile/${user.id}`" class="user-link">
            <div class="user-avatar-wrap">
              <img
                v-if="user.profile_image"
                :src="user.profile_image"
                :alt="user.username"
                class="user-avatar"
              />
              <div v-else class="user-avatar avatar-fallback">
                {{ user.username?.[0]?.toUpperCase() }}
              </div>
            </div>
            <div class="user-info">
              <span class="user-name">{{ user.username }}</span>
              <span v-if="user.bio" class="user-bio"
                >{{ user.bio?.slice(0, 40) }}{{ user.bio?.length > 40 ? '…' : '' }}</span
              >
            </div>
          </RouterLink>

          <button
            v-if="!isCurrentUser(user)"
            :class="['btn-follow', { following: user.is_following }]"
            type="button"
            :disabled="loadingUserId === user.id"
            @click="handleFollowToggle(user)"
          >
            {{ user.is_following ? '팔로잉' : '팔로우' }}
          </button>
        </div>
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

.follow-page {
  min-height: calc(100vh - 64px);
  background: #f4eedf;
  font-family: 'Gowun Batang', serif;
  color: #262019;
  padding: 52px 0 80px;
}

.follow-inner {
  max-width: 600px;
  margin: 0 auto;
  padding: 0 32px;
}

.back-link {
  display: inline-block;
  font-size: 14px;
  color: #9c9079;
  text-decoration: none;
  margin-bottom: 24px;
  transition: color 0.15s;
}
.back-link:hover {
  color: #1e3a3a;
}

/* 탭 헤더 */
.tab-header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid rgba(40, 32, 20, 0.1);
  margin-bottom: 28px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  border-bottom: 2.5px solid transparent;
  padding: 14px 24px;
  margin-bottom: -1px;
  font-family: 'Gowun Batang', serif;
  font-size: 16px;
  font-weight: 700;
  color: #9c9079;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-btn:hover {
  color: #262019;
}
.tab-btn.active {
  color: #1e3a3a;
  border-bottom-color: #1e3a3a;
}

.tab-count {
  font-family: 'Spline Sans Mono', monospace;
  font-size: 13px;
  color: #b8ad9a;
  background: rgba(40, 32, 20, 0.07);
  border-radius: 999px;
  padding: 2px 9px;
}
.tab-btn.active .tab-count {
  color: #1e3a3a;
  background: rgba(30, 58, 58, 0.1);
}

/* 유저 목록 */
.user-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user-card {
  background: #fbf7ee;
  border: 1px solid rgba(40, 32, 20, 0.1);
  border-radius: 14px;
  padding: 18px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: box-shadow 0.15s;
}
.user-card:hover {
  box-shadow: 0 4px 16px -8px rgba(40, 32, 20, 0.2);
}

.user-link {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  text-decoration: none;
  color: inherit;
  min-width: 0;
}

.user-avatar-wrap {
  flex-shrink: 0;
}
.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  border: 1.5px solid rgba(40, 32, 20, 0.1);
}
.avatar-fallback {
  background: #1e3a3a;
  color: #f4eedf;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Newsreader', serif;
  font-size: 20px;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.user-name {
  font-size: 16px;
  font-weight: 700;
  color: #262019;
}
.user-bio {
  font-size: 13px;
  color: #9c9079;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 팔로우 버튼 */
.btn-follow {
  flex-shrink: 0;
  background: #1e3a3a;
  color: #f4eedf;
  border: none;
  border-radius: 999px;
  padding: 9px 20px;
  font-family: 'Gowun Batang', serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.btn-follow:hover {
  background: #152a2a;
}
.btn-follow.following {
  background: transparent;
  color: #6b6253;
  border: 1px solid rgba(40, 32, 20, 0.2);
}
.btn-follow.following:hover {
  background: rgba(40, 32, 20, 0.04);
}
.btn-follow:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 빈 상태 */
.empty-state {
  text-align: center;
  padding: 60px 24px;
}
.empty-title {
  font-family: 'Newsreader', serif;
  font-size: 20px;
  color: #4a4337;
  margin: 0 0 8px;
}
.empty-sub {
  font-size: 14px;
  color: #9c9079;
  margin: 0;
}

/* 에러 */
.page-error {
  font-size: 14px;
  color: #b06a3c;
  padding: 14px 18px;
  background: rgba(176, 106, 60, 0.08);
  border-radius: 10px;
  border-left: 3px solid #b06a3c;
}

/* 스켈레톤 */
.skeleton {
  animation: shimmer 1.6s ease-in-out infinite;
  pointer-events: none;
}
.sk-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #e7dcc4;
  flex-shrink: 0;
}
.sk-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sk-line {
  height: 12px;
  border-radius: 6px;
  background: #e7dcc4;
}
.w30 {
  width: 30%;
}
.w50 {
  width: 50%;
}
</style>
