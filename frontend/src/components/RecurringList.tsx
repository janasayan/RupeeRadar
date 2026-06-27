import type { RecurringGroup } from '../api/types'

const FREQ_LABELS: Record<string, string> = {
  monthly: 'Monthly',
  weekly: 'Weekly',
  irregular: 'Irregular',
}

const FREQ_COLOURS: Record<string, string> = {
  monthly: 'bg-indigo-100 text-indigo-700',
  weekly: 'bg-blue-100 text-blue-700',
  irregular: 'bg-slate-100 text-slate-600',
}

interface Props {
  groups: RecurringGroup[]
}

export default function RecurringList({ groups }: Props) {
  if (groups.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm text-center">
        <p className="text-slate-500 text-sm">No recurring payments detected.</p>
        <p className="mt-1 text-xs text-slate-400">
          Recurring payments need ≥ 2 occurrences with a stable amount.
        </p>
      </div>
    )
  }

  const totalMonthly = groups
    .filter((g) => g.frequency === 'monthly')
    .reduce((sum, g) => sum + Math.abs(g.amount), 0)

  return (
    <div className="space-y-4">
      {totalMonthly > 0 && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 px-5 py-3 flex items-center justify-between">
          <span className="text-sm font-medium text-indigo-800">
            Estimated monthly recurring spend
          </span>
          <span className="text-lg font-bold text-indigo-700">
            ₹{totalMonthly.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </span>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold text-slate-900">
            Recurring Payments{' '}
            <span className="ml-1 text-sm font-normal text-slate-400">({groups.length})</span>
          </h3>
        </div>

        <ul className="divide-y divide-slate-50">
          {groups.map((g) => (
            <li key={g.id} className="flex items-center justify-between px-5 py-4 hover:bg-slate-50">
              <div className="flex-1 min-w-0 mr-4">
                <p className="font-medium text-slate-800 truncate">{g.label}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-slate-400">{g.category}</span>
                  <span className="text-slate-200">·</span>
                  <span className="text-xs text-slate-400">{g.occurrence_count}× · last {g.last_seen}</span>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    FREQ_COLOURS[g.frequency] ?? 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {FREQ_LABELS[g.frequency] ?? g.frequency}
                </span>
                <span className="font-semibold text-slate-800 text-sm">
                  ₹{Math.abs(g.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
