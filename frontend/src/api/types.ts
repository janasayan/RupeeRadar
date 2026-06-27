// API types matching backend Pydantic schemas

export interface HealthResponse {
  status: string
  service: string
  llm_provider: string
  llm_configured: boolean
}

export interface UploadResponse {
  session_id: string
  status: string
  row_count: number | null
  warnings: string[]
  llm_categorized: number
}

export interface SessionStatus {
  id: string
  filename: string
  status: string
  row_count: number | null
  warnings: string[] | null
  error_message: string | null
}

export interface Transaction {
  id: string
  date: string
  description_raw: string
  description_clean: string
  amount: number
  txn_type: 'debit' | 'credit'
  balance: number | null
  category: string
  category_confidence: number
  category_source: 'rule' | 'llm' | 'user'
  is_recurring: boolean
  merchant: string | null
  needs_wants: 'need' | 'want' | 'income' | null
}

export interface TransactionPage {
  items: Transaction[]
  total: number
  page: number
  page_size: number
}

export interface CategoryBreakdown {
  category: string
  total: number
  count: number
}

export interface MonthlyBreakdown {
  month: string   // "YYYY-MM"
  income: number
  spend: number
}

export interface RecurringGroup {
  id: string
  label: string
  category: string
  amount: number
  frequency: 'monthly' | 'weekly' | 'irregular'
  occurrence_count: number
  last_seen: string
}

export interface Metrics {
  total_income: number
  total_spend: number
  savings: number
  savings_rate: number | null
  top_categories: CategoryBreakdown[]
  biggest_debit_amount: number | null
  biggest_debit_merchant: string | null
  biggest_debit_date: string | null
  period_start: string | null
  period_end: string | null
  recurring_total: number
  monthly_breakdown: MonthlyBreakdown[]
  llm_categorized: number
  needs_total: number
  wants_total: number
}

export interface RecommendationItem {
  category: string
  amount_spent: number
  suggested_cap: number
  potential_saving: number
  top_merchants: string[]
  suggestion_text: string
}

export interface RecommendationsOut {
  salary_monthly: number | null
  wants_budget_pct: number
  wants_budget: number | null
  wants_actual: number
  needs_actual: number
  is_over_budget: boolean
  recommendations: RecommendationItem[]
  summary: string
}

export interface InsightsOut {
  insights: string[]
}

export const CATEGORIES = [
  'Food', 'Travel', 'Shopping', 'Bills', 'EMI',
  'Subscriptions', 'Salary', 'Rent', 'Investments', 'Other',
] as const

export type Category = typeof CATEGORIES[number]
