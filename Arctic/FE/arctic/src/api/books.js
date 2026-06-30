import { apiRequest } from './client'

export function getBookCoverUrl(bookId) {
  return `/api/books/${bookId}/cover/`
}

export function fetchBooks(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, value)
    }
  })

  const query = searchParams.toString()
  return apiRequest(`/books/${query ? `?${query}` : ''}`)
}

export function fetchGenres() {
  return apiRequest('/books/genres/', {
    auth: false,
  })
}

export function fetchBook(bookId) {
  return apiRequest(`/books/${bookId}/`)
}

export function toggleWishlist(bookId) {
  return apiRequest(`/books/${bookId}/wishlist/`, {
    method: 'POST',
  })
}

export function toggleCollection(bookId) {
  return apiRequest(`/books/${bookId}/collection/`, {
    method: 'POST',
  })
}

export function createReview(bookId, payload) {
  return apiRequest(`/books/${bookId}/reviews/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function toggleReviewLike(reviewId) {
  return apiRequest(`/books/reviews/${reviewId}/like/`, {
    method: 'POST',
  })
}

export function updateReview(bookId, reviewId, payload) {
  return apiRequest(`/books/${bookId}/reviews/${reviewId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteReview(bookId, reviewId) {
  return apiRequest(`/books/${bookId}/reviews/${reviewId}/`, {
    method: 'DELETE',
  })
}

export function materializeBook(payload) {
  return apiRequest('/books/materialize/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchWishlist() {
  return apiRequest('/books/wishlist/')
}
