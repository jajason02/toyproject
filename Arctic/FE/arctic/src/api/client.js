const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

function getApiBaseUrl() {
  if (!configuredApiBaseUrl) {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`
  }

  try {
    const url = new URL(configuredApiBaseUrl)
    const isLocalApi = ['localhost', '127.0.0.1'].includes(url.hostname)
    const isLocalClient = ['localhost', '127.0.0.1'].includes(window.location.hostname)

    if (isLocalApi && isLocalClient) {
      url.hostname = window.location.hostname
      return url.toString().replace(/\/$/, '')
    }
  } catch {
    return configuredApiBaseUrl
  }

  return configuredApiBaseUrl
}

const API_BASE_URL = getApiBaseUrl()

const ERROR_MESSAGES = {
  'Authentication credentials were not provided.': '로그인이 필요합니다.',
  'Authentication required': '로그인이 필요합니다.',
  'authentication required': '로그인이 필요합니다.',
  'Given token not valid for any token type': '로그인이 만료되었습니다. 다시 로그인해주세요.',
  'Token is invalid or expired': '로그인이 만료되었습니다. 다시 로그인해주세요.',
  'No active account found with the given credentials': '이메일 또는 비밀번호가 올바르지 않습니다.',
  'Book not found.': '도서를 찾을 수 없습니다.',
  'Could not load the book cover.': '도서 표지를 불러오지 못했습니다.',
  'The cover URL did not return an image.': '표지 주소가 이미지가 아닙니다.',
  'The book cover is too large.': '도서 표지 파일이 너무 큽니다.',
}

function getErrorMessage(data, fallback = '요청을 처리하지 못했습니다.') {
  const rawMessage = data?.error || data?.detail || fallback
  const message = Array.isArray(rawMessage) ? rawMessage[0] : rawMessage

  if (typeof message !== 'string') {
    return fallback
  }

  return ERROR_MESSAGES[message] || message
}

export function isAuthenticated() {
  return document.cookie.split(';').some((c) => c.trim().startsWith('auth_state='))
}

export function clearTokens() {
  document.cookie = 'auth_state=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax'
}

async function parseResponse(response) {
  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error('서버에서 JSON이 아닌 응답을 받았습니다. API 주소를 확인해주세요.')
  }

  const data = await response.json()
  if (!response.ok) {
    throw new Error(getErrorMessage(data))
  }
  return data
}

async function refreshAccessToken() {
  const response = await fetch(`${API_BASE_URL}/accounts/token/refresh/`, {
    method: 'POST',
    credentials: 'include',
  })

  if (!response.ok) {
    clearTokens()
    return false
  }
  return true
}

function createHeaders(options) {
  const isFormData = options.body instanceof FormData
  return {
    ...(options.body && !isFormData ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  }
}

async function sendRequest(path, options) {
  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: createHeaders(options),
    credentials: 'include',
  })
}

export async function apiRequest(path, options = {}) {
  let response = await sendRequest(path, options)

  if (response.status === 401 && options.auth !== false) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      response = await sendRequest(path, options)
    } else {
      throw new Error('로그인이 필요합니다.')
    }
  }

  return parseResponse(response)
}
