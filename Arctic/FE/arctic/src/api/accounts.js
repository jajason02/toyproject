import { apiRequest } from './client'

export function login(payload) {
  return apiRequest('/accounts/login/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  })
}

export function signup(payload) {
  return apiRequest('/accounts/signup/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  })
}

export function checkEmailAvailability(email) {
  const params = new URLSearchParams({ email })
  return apiRequest(`/accounts/email-availability/?${params.toString()}`, {
    auth: false,
  })
}

export function logout(payload) {
  return apiRequest('/accounts/logout/', {
    method: 'POST',
    auth: false,
    body: JSON.stringify(payload),
  })
}

export function fetchProfile(userId) {
  const path = userId ? `/accounts/profile/${userId}/` : '/accounts/profile/'
  return apiRequest(path)
}

export function fetchFollowers(userId) {
  const path = userId ? `/accounts/profile/${userId}/followers/` : '/accounts/profile/followers/'
  return apiRequest(path)
}

export function fetchFollowing(userId) {
  const path = userId ? `/accounts/profile/${userId}/following/` : '/accounts/profile/following/'
  return apiRequest(path)
}

export function updateProfile(payload) {
  const body = payload instanceof FormData ? payload : JSON.stringify(payload)

  return apiRequest('/accounts/profile/edit/', {
    method: 'PATCH',
    body,
  })
}

export function toggleFollow(userId) {
  return apiRequest(`/accounts/follow/${userId}/`, {
    method: 'POST',
  })
}

export function searchUsers(q) {
  return apiRequest(`/accounts/users/search/?q=${encodeURIComponent(q)}`)
}
