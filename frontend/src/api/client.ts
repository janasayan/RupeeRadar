import type {
  HealthResponse,
  UploadResponse,
  SessionStatus,
  TransactionPage,
  Metrics,
  InsightsOut,
  RecurringGroup,
  RecommendationsOut,
} from './types'

const API_BASE = `${(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''}/api/v1`

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    let message = `Request failed: ${response.status}`
    try {
      const body = await response.json()
      message = body.detail ?? message
    } catch {
      // ignore
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export async function uploadStatement(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return request<UploadResponse>('/upload', { method: 'POST', body: form })
}

export function getSession(sessionId: string): Promise<SessionStatus> {
  return request<SessionStatus>(`/sessions/${sessionId}`)
}

export function getTransactions(
  sessionId: string,
  page = 1,
  pageSize = 50,
): Promise<TransactionPage> {
  return request<TransactionPage>(
    `/sessions/${sessionId}/transactions?page=${page}&page_size=${pageSize}`,
  )
}

export function getAnalytics(sessionId: string): Promise<Metrics> {
  return request<Metrics>(`/sessions/${sessionId}/analytics`)
}

export function getInsights(sessionId: string): Promise<InsightsOut> {
  return request<InsightsOut>(`/sessions/${sessionId}/insights`)
}

export function getRecurring(sessionId: string): Promise<RecurringGroup[]> {
  return request<RecurringGroup[]>(`/sessions/${sessionId}/recurring`)
}

export function updateTransactionCategory(
  sessionId: string,
  transactionId: string,
  category: string,
): Promise<import('./types').Transaction> {
  return request(`/sessions/${sessionId}/transactions/${transactionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
}

export function getRecommendations(sessionId: string): Promise<RecommendationsOut> {
  return request<RecommendationsOut>(`/sessions/${sessionId}/recommendations`)
}

export function updateRecommendationSettings(
  sessionId: string,
  settings: { salary_monthly?: number; wants_budget_pct?: number },
): Promise<RecommendationsOut> {
  return request<RecommendationsOut>(`/sessions/${sessionId}/recommendations/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error(`Delete failed: ${response.status}`)
}

export async function downloadReport(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/report`)
  if (!response.ok) throw new Error('Report generation failed')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'rupeeradar-report.html'
  a.click()
  URL.revokeObjectURL(url)
}

