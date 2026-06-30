import { apiRequest } from './client'

export function analyzeReviews(bookId) {
  return apiRequest(`/ai/analyze_reviews/${bookId}/`, { method: 'POST' })
}

export function askStorySeeds(payload) {
  return apiRequest('/ai/ask_story_seeds/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function generateIdeas(payload) {
  return apiRequest('/ai/generate_ideas/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function suggestPlot(payload) {
  return apiRequest('/ai/suggest_plot/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function correctText(payload) {
  return apiRequest('/ai/correct_text/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchRecommendations() {
  return apiRequest('/ai/recommendations/')
}

export function saveDraft(payload) {
  return apiRequest('/ai/drafts/', { method: 'POST', body: JSON.stringify(payload) })
}

export function fetchDrafts() {
  return apiRequest('/ai/drafts/')
}

export function deleteDraft(id) {
  return apiRequest(`/ai/drafts/${id}/`, { method: 'DELETE' })
}

export function updateDraft(id, payload) {
  return apiRequest(`/ai/drafts/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function toggleDraftLike(id) {
  return apiRequest(`/ai/drafts/${id}/like/`, { method: 'POST' })
}

export function fetchDraftComments(id) {
  return apiRequest(`/ai/drafts/${id}/comments/`)
}

export function createDraftComment(id, content) {
  return apiRequest(`/ai/drafts/${id}/comments/`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

export function deleteDraftComment(commentId) {
  return apiRequest(`/ai/comments/${commentId}/`, { method: 'DELETE' })
}

export function updateDraftComment(commentId, content) {
  return apiRequest(`/ai/comments/${commentId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ content }),
  })
}

export function toggleDraftCommentLike(commentId) {
  return apiRequest(`/ai/comments/${commentId}/like/`, {
    method: 'POST',
  })
}
