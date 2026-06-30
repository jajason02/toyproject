import { apiRequest } from './client'

export function fetchThreads({ page = 1, query = '', searchBy = 'all' } = {}) {
  const params = new URLSearchParams({ page: String(page) })
  if (query.trim()) {
    params.set('q', query.trim())
    params.set('search_by', searchBy)
  }
  return apiRequest(`/community/threads/?${params.toString()}`, { auth: false })
}

export function fetchThread(threadId) {
  return apiRequest(`/community/threads/${threadId}/`, {
    auth: false,
  })
}

export function createThread(payload) {
  return apiRequest('/community/threads/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function toggleThreadLike(threadId) {
  return apiRequest(`/community/threads/${threadId}/like/`, {
    method: 'POST',
  })
}

export function createComment(threadId, payload) {
  return apiRequest(`/community/threads/${threadId}/comments/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function toggleCommentLike(threadId, commentId) {
  return apiRequest(`/community/threads/${threadId}/comments/${commentId}/like/`, {
    method: 'POST',
  })
}

export function deleteComment(threadId, commentId) {
  return apiRequest(`/community/threads/${threadId}/comments/${commentId}/`, {
    method: 'DELETE',
  })
}

export function updateThread(threadId, payload) {
  return apiRequest(`/community/threads/${threadId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteThread(threadId) {
  return apiRequest(`/community/threads/${threadId}/`, {
    method: 'DELETE',
  })
}

export function updateComment(threadId, commentId, payload) {
  return apiRequest(`/community/threads/${threadId}/comments/${commentId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
