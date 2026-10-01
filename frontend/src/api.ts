import type { DailySummary, Meal, PeriodSummary, Profile, Suggestion } from './types'

const API = '/api'
const TOKEN_KEY = 'caltracker_token'

export const getToken = () => window.localStorage.getItem(TOKEN_KEY)
export const saveToken = (token: string) => window.localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => window.localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API}${path}`, { ...init, headers })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401) clearToken()
    const detail = typeof data?.detail === 'string' ? data.detail : 'Une erreur est survenue.'
    throw new ApiError(detail, response.status)
  }
  return data as T
}

export const api = {
  register: (payload: { email: string; password: string; display_name: string }) =>
    request<Profile>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; expires_in: number }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  profile: () => request<Profile>('/users/me'),
  updateProfile: (payload: Partial<Profile>) =>
    request<Profile>('/users/me', { method: 'PUT', body: JSON.stringify(payload) }),
  daily: (day?: string) => request<DailySummary>(`/nutrition/daily${day ? `?day=${day}` : ''}`),
  weekly: (end?: string) => request<PeriodSummary>(`/nutrition/weekly${end ? `?end_date=${end}` : ''}`),
  meals: () => request<Meal[]>('/meals'),
  addMeal: (payload: {
    meal_type: string
    eaten_at?: string
    description?: string
    items: Array<{ food?: string; food_id?: string; quantity: number; unit: string }>
  }) => request<Meal>('/meals', { method: 'POST', body: JSON.stringify(payload) }),
  removeMeal: (id: string) => request<{ message: string }>(`/meals/${id}`, { method: 'DELETE' }),
  analyzeMeal: (text: string) =>
    request<{ items: import('./types').ParsedItem[]; clarification: string | null; provider: string }>(
      '/ai/analyze-meal',
      { method: 'POST', body: JSON.stringify({ text }) },
    ),
  recommendations: (day?: string) =>
    request<{ recommendations: string[]; provider: string }>('/ai/recommendations', {
      method: 'POST',
      body: JSON.stringify(day ? { day } : {}),
    }),
  suggestions: (meal_type: string) =>
    request<{ suggestions: Suggestion[]; provider: string }>('/ai/meal-suggestions', {
      method: 'POST',
      body: JSON.stringify({ meal_type }),
    }),
  chat: (message: string) =>
    request<{ answer: string; provider: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  exportData: () => request<Record<string, unknown>>('/users/me/export'),
  deleteAccount: () => request<{ message: string }>('/users/me', { method: 'DELETE' }),
}
