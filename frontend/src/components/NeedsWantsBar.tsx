import type { Metrics } from '../api/types'

interface Props {
  metrics: Metrics
  wantsBudget: number | null
}

export default function NeedsWantsBar({ metrics, wantsBudget }: Props) {
  const total = metrics.needs_total + metrics.wants_total
  if (total === 0) return null

  const needsPct = Math.round((metrics.needs_total / total) * 100)
  const wantsPct = 100 - needsPct

  const overBudget = wantsBudget !== null && metrics.wants_total > wantsBudget
  const wantsColor = overBudget ? 'bg-red-400' : 'bg-amber-400'
  const wantsText = overBudget ? 'text-red-700' : 'text-amber-700'

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Needs vs Wants</h3>

      {/* Stacked bar */}
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="bg-blue-500 transition-all"
          style={{ width: `${needsPct}%` }}
          title={`Needs ${needsPct}%`}
        />
        <div
          className={`${wantsColor} transition-all`}
          style={{ width: `${wantsPct}%` }}
          title={`Wants ${wantsPct}%`}
        />
      </div>

      {/* Budget threshold marker */}
      {wantsBudget !== null && (
        <div className="relative mt-1 h-3 w-full">
          {(() => {
            const budgetWantsPct = Math.min(100, Math.round((wantsBudget / total) * 100))
            const markerLeft = 100 - budgetWantsPct
            return (
              <div
                className="absolute top-0 h-3 w-0.5 bg-slate-500"
                style={{ left: `${markerLeft}%` }}
                title={`Wants budget ₹${wantsBudget.toLocaleString('en-IN')}`}
              />
            )
          })()}
        </div>
      )}

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
          <span className="text-slate-600">
            Needs — <span className="font-medium text-slate-900">₹{metrics.needs_total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${wantsColor}`} />
          <span className={`${wantsText}`}>
            Wants — <span className="font-medium">₹{metrics.wants_total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            {wantsBudget !== null && (
              <span className="ml-1 text-slate-500">
                (budget ₹{wantsBudget.toLocaleString('en-IN', { maximumFractionDigits: 0 })})
              </span>
            )}
          </span>
        </span>
      </div>
    </div>
  )
}
