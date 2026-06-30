import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '@/api/client'
import LandingView from '@/views/LandingView.vue'
import HomeView from '@/views/HomeView.vue'
import FollowListView from '@/views/accounts/FollowListView.vue'
import LoginView from '@/views/accounts/LoginView.vue'
import ProfileEditView from '@/views/accounts/ProfileEditView.vue'
import ProfileView from '@/views/accounts/ProfileView.vue'
import SignupView from '@/views/accounts/SignupView.vue'
import BookDetailView from '@/views/books/BookDetailView.vue'
import CommunityView from '@/views/community/CommunityView.vue'
import ThreadCreateView from '@/views/community/ThreadCreateView.vue'
import ThreadDetailView from '@/views/community/ThreadDetailView.vue'
import AIStudioView from '@/views/AIStudioView.vue'
import WritingDraftView from '@/views/WritingDraftView.vue'
import RecommendationView from '@/views/RecommendationView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
  routes: [
    // 시작 화면 — 비로그인 시 랜딩, 로그인 시 LandingView 내부에서 /books로 리다이렉트
    {
      path: '/',
      name: 'landing',
      component: LandingView,
    },
    // 도서 목록
    {
      path: '/books',
      name: 'books',
      component: HomeView,
    },
    {
      path: '/books/:bookId',
      name: 'book-detail',
      component: BookDetailView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/signup',
      name: 'signup',
      component: SignupView,
    },
    {
      path: '/community',
      name: 'community',
      component: CommunityView,
      meta: { requiresAuth: true },
    },
    {
      path: '/community/create',
      name: 'thread-create',
      component: ThreadCreateView,
      meta: { requiresAuth: true },
    },
    {
      path: '/community/:threadId',
      name: 'thread-detail',
      component: ThreadDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/edit',
      name: 'profile-edit',
      component: ProfileEditView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/follows',
      name: 'profile-follow-list',
      component: FollowListView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/:userId/follows',
      name: 'user-follow-list',
      component: FollowListView,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/:userId',
      name: 'user-profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: '/studio',
      name: 'studio',
      component: AIStudioView,
      meta: { requiresAuth: true },
    },
    {
      path: '/studio/drafts',
      name: 'studio-drafts',
      component: WritingDraftView,
      meta: { requiresAuth: true },
    },
    {
      path: '/recommendations',
      name: 'recommendations',
      component: RecommendationView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const isLoggedIn = isAuthenticated()

  if (to.meta.requiresAuth && !isLoggedIn) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  return true
})

export default router
