/**
 * Centralized API client for ClarityAI frontend.
 * Communicates with backend endpoints using relative URLs by default
 * so the Vite/Docker reverse proxy handles routing.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('clarityai_token') || null
    this.onUnauthorized = null
  }

  setToken(token) {
    this.token = token
    if (token) {
      localStorage.setItem('clarityai_token', token)
    } else {
      localStorage.removeItem('clarityai_token')
    }
  }

  getToken() {
    return this.token
  }

  setOnUnauthorized(callback) {
    this.onUnauthorized = callback
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const config = {
      ...options,
      headers,
    }

    let response
    try {
      response = await fetch(url, config)
    } catch (networkError) {
      throw new ApiError('Unable to connect to ClarityAI server. Please check your connection.', 0)
    }

    if (response.status === 401) {
      this.setToken(null)
      if (this.onUnauthorized) {
        this.onUnauthorized()
      }
    }

    let data = null
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json()
      } catch {
        data = null
      }
    }

    if (!response.ok) {
      let errorMessage = 'An unexpected error occurred'
      if (data && data.detail) {
        if (typeof data.detail === 'string') {
          errorMessage = data.detail
        } else if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((err) => err.msg || JSON.stringify(err)).join(', ')
        }
      } else if (response.statusText) {
        errorMessage = response.statusText
      }
      throw new ApiError(errorMessage, response.status, data)
    }

    return data
  }

  // Authentication
  async register(email, password) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (data && data.access_token) {
      this.setToken(data.access_token)
    }
    return data
  }

  async getCurrentUser() {
    return this.request('/auth/me', {
      method: 'GET',
    })
  }

  // Jobs
  async createTextJob(content) {
    return this.request('/jobs', {
      method: 'POST',
      body: JSON.stringify({
        input_type: 'text_paste',
        content,
      }),
    })
  }

  async listJobs(page = 1, pageSize = 20) {
    return this.request(`/jobs?page=${page}&page_size=${pageSize}`, {
      method: 'GET',
    })
  }

  async getJob(jobId) {
    return this.request(`/jobs/${jobId}`, {
      method: 'GET',
    })
  }
}

export const apiClient = new ApiClient()
export { ApiError }
