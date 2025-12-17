/**
 * API Helper - Automatically adds JWT token to requests
 */

const API_BASE = ''

/**
 * Fetch with authentication
 * Automatically adds JWT token from localStorage
 */
export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('auth_token')

  const headers = {
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  return response
}

/**
 * GET request with auth
 */
export async function apiGet(endpoint) {
  return apiFetch(endpoint, { method: 'GET' })
}

/**
 * POST request with auth
 */
export async function apiPost(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'POST',
    body: data,
  })
}

/**
 * PUT request with auth
 */
export async function apiPut(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'PUT',
    body: data,
  })
}

/**
 * DELETE request with auth
 */
export async function apiDelete(endpoint) {
  return apiFetch(endpoint, { method: 'DELETE' })
}

export default apiFetch
