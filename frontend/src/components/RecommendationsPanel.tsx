import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateRecommendationSettings } from '../api/client'
import type { RecommendationsOut } from '../api/types'

interface Props {
  sessionId: string
  data: RecommendationsOut
}

export default function RecommendationsPanel({ sessionId, data }: Props) {
  const queryClient = useQueryClient()
  const [salary, setSalary] = useState(data.salary_monthly?.toString() ?? '')
  const [pct, setPct] = useState(data.wants_budget_pct.toString())

  const mutation = useMutation({
    mutationFn: (settings: { salary_monthly?: number; wants_budget_pct?: number }) =>
      updateRecommendationSettings(sessionId, settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] })
    },
  })

  function handleRecalculate() {
    const s = parseFloat(salary)
    const p = parseFloat(pct)
    mutation.mutate({
      salary_monthly: isNaN(s) ? undefined : s,
      wants_budget_pct: isNaN(p) ? undefined : p,
    })
  }

  // Use latest data from mutation if available
  const rec = (mutation.data ?? data) as RecommendationsOut

  return (
    <div className="space-y-6">

      {/* Salary / budget settings */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-700">Budget Settings</h3>
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Monthly Salary (₹)</label>
            <input
              type="number"
              value={salary}
              onChange={e => setSalary(e.target.value)}
              placeholder="e.g. 75000"
              className="w-36 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500">Wants Budget (%)</label>
            <input
              type="number"
              value={pct}
              onChange={e => setPct(e.target.value)}
              min={0}
              max={100}
              className="w-24 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleRecalculate}
            disabled={mutation.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {mutation.isPending ? 'Recalculating…' : 'Recalculate'}
          </button>
        </div>
      </div>

      {/* Summary banner */}
      <div className={`rounded-xl border px-5 py-4 text-sm font-medium ${
        rec.is_over_budget
          ? 'border-red-200 bg-red-50 text-red-800'
          : 'border-green-200 bg-green-50 text-green-800'
      }`}>
        {rec.summary}
      </div>

      {/* Spend split */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <_MetricCard label="Needs Spend" value={`₹${rec.needs_actual.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} color="blue" />
        <_MetricCard label="Wants Spend" value={`₹${rec.wants_actual.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} color={rec.is_over_budget ? 'red' : 'amber'} />
        {rec.wants_budget !== null && (
          <_MetricCard label="Wants Budget" value={`₹${rec.wants_budget.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} color="slate" />
        )}
        {rec.salary_monthly !== null && (
          <_MetricCard label="Monthly Salary" value={`₹${rec.salary_monthly!.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} color="slate" />
        )}
      </div>

      {/* Recommendations list */}
      {rec.recommendations.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-700">Where you can save</h3>
          {rec.recommendations.map((r, i) => (
            <div key={i} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
                      {r.category}
                    </span>
                    <span className="text-xs text-slate-500">
                      {r.top_merchants.slice(0, 2).join(', ')}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{r.suggestion_text}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-lg font-bold text-green-600">
                    ₹{r.potential_saving.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-slate-400">potential saving</p>
                </div>
              </div>
              <div className="mt-3 flex gap-4 text-xs text-slate-500">
                <span>Spent: <span className="font-medium text-red-600">₹{r.amount_spent.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span></span>
                <span>Target: <span className="font-medium text-green-600">₹{r.suggested_cap.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span></span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !rec.is_over_budget && rec.salary_monthly !== null && (
          <div className="rounded-xl border border-green-200 bg-green-50 px-5 py-6 text-center text-sm text-green-700">
            You're within budget — no specific savings actions needed right now.
          </div>
        )
      )}

      {rec.salary_monthly === null && (
        <p className="text-center text-xs text-slate-400">
          Enter your monthly salary above to get personalised savings recommendations.
        </p>
      )}
    </div>
  )
}

function _MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'border-blue-100 bg-blue-50 text-blue-900',
    amber: 'border-amber-100 bg-amber-50 text-amber-900',
    red: 'border-red-100 bg-red-50 text-red-900',
    green: 'border-green-100 bg-green-50 text-green-900',
    slate: 'border-slate-200 bg-slate-50 text-slate-900',
  }
  return (
    <div className={`rounded-xl border px-4 py-3 ${colors[color] ?? colors.slate}`}>
      <p className="text-xs opacity-70">{label}</p>
      <p className="mt-0.5 text-base font-bold">{value}</p>
    </div>
  )
}
