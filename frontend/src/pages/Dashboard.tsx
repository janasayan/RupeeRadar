import { useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getAnalytics, getInsights, getTransactions, getRecurring, getRecommendations, deleteSession, downloadReport } from '../api/client'
import CategoryChart from '../components/CategoryChart'
import InsightCards from '../components/InsightCards'
import MonthlyTrendChart from '../components/MonthlyTrendChart'
import NeedsWantsBar from '../components/NeedsWantsBar'
import RecurringList from '../components/RecurringList'
import RecommendationsPanel from '../components/RecommendationsPanel'
import SummaryCards from '../components/SummaryCards'
import TransactionTable from '../components/TransactionTable'

type Tab = 'summary' | 'transactions' | 'recurring' | 'insights' | 'recommendations'

export default function Dashboard() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const uploadWarnings: string[] = (location.state as { warnings?: string[] })?.warnings ?? []
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<Tab>('summary')
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const { data: metrics, isLoading: loadingMetrics, error: metricsError } = useQuery({
    queryKey: ['analytics', sessionId],
    queryFn: () => getAnalytics(sessionId!),
    enabled: !!sessionId,
  })

  const { data: insights } = useQuery({
    queryKey: ['insights', sessionId],
    queryFn: () => getInsights(sessionId!),
    enabled: !!sessionId,
  })

  const { data: txnPage } = useQuery({
    queryKey: ['transactions', sessionId, page],
    queryFn: () => getTransactions(sessionId!, page),
    enabled: !!sessionId,
  })

  const { data: recurringGroups } = useQuery({
    queryKey: ['recurring', sessionId],
    queryFn: () => getRecurring(sessionId!),
    enabled: !!sessionId,
  })

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations', sessionId],
    queryFn: () => getRecommendations(sessionId!),
    enabled: !!sessionId,
  })

  function invalidateAnalytics() {
    queryClient.invalidateQueries({ queryKey: ['analytics', sessionId] })
    queryClient.invalidateQueries({ queryKey: ['transactions', sessionId] })
  }

  async function handleDelete() {
    if (!sessionId) return
    if (!window.confirm('Delete all data for this session? This cannot be undone.')) return
    setDeleting(true)
    try {
      await deleteSession(sessionId)
      navigate('/')
    } catch {
      setDeleting(false)
    }
  }

  async function handleDownloadReport() {
    if (!sessionId) return
    setDownloading(true)
    try {
      await downloadReport(sessionId)
    } finally {
      setDownloading(false)
    }
  }

  const loading = loadingMetrics
  const error = metricsError ? (metricsError as Error).message : null

  const tabs: { id: Tab; label: string }[] = [
    { id: 'summary', label: 'Summary' },
    { id: 'transactions', label: 'Transactions' },
    { id: 'recurring', label: `Recurring${recurringGroups?.length ? ` (${recurringGroups.length})` : ''}` },
    { id: 'insights', label: 'Insights' },
    { id: 'recommendations', label: `Recommendations${recommendations?.recommendations.length ? ` (${recommendations.recommendations.length})` : ''}` },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <a href="/" className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">
              ₹
            </a>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">RupeeRadar</h1>
              <p className="text-sm text-slate-500">Analysis Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadReport}
              disabled={downloading}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              {downloading ? 'Generating…' : 'Download Report'}
            </button>
            <a
              href="/"
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              New upload
            </a>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {deleting ? 'Deleting…' : 'Delete my data'}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {uploadWarnings.length > 0 && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm font-medium text-amber-800">
              {uploadWarnings.length} parse warning(s)
            </p>
            <ul className="mt-1 list-inside list-disc text-xs text-amber-700">
              {uploadWarnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        )}

        {!loading && metrics && (
          <>
            {/* LLM notice */}
            {metrics.llm_categorized > 0 && (
              <div className="mb-4 rounded-lg border border-purple-100 bg-purple-50 px-4 py-2 text-xs text-purple-700">
                {metrics.llm_categorized} transaction(s) were categorized using AI
              </div>
            )}

            {/* Tab nav */}
            <div className="mb-6 flex gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm w-fit">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    tab === t.id
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Summary tab */}
            {tab === 'summary' && (
              <div className="space-y-6">
                <SummaryCards metrics={metrics} />
                <NeedsWantsBar metrics={metrics} wantsBudget={recommendations?.wants_budget ?? null} />
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <CategoryChart metrics={metrics} />
                  <MonthlyTrendChart metrics={metrics} />
                </div>
              </div>
            )}

            {/* Transactions tab */}
            {tab === 'transactions' && txnPage && (
              <TransactionTable
                sessionId={sessionId!}
                data={txnPage}
                onPageChange={setPage}
                onCategoryChanged={invalidateAnalytics}
              />
            )}

            {/* Recurring tab */}
            {tab === 'recurring' && (
              <RecurringList groups={recurringGroups ?? []} />
            )}

            {/* Insights tab */}
            {tab === 'insights' && insights && (
              <InsightCards insights={insights.insights} />
            )}

            {/* Recommendations tab */}
            {tab === 'recommendations' && (
              recommendations
                ? <RecommendationsPanel sessionId={sessionId!} data={recommendations} />
                : <div className="py-10 text-center text-sm text-slate-400">Recommendations not available yet.</div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

