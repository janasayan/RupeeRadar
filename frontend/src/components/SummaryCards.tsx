import type { Metrics } from '../api/types'

interface Props {
  metrics: Metrics
}

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

function fmt(n: number) {
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export default function SummaryCards({ metrics }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Total Income" value={fmt(metrics.total_income)} />
      <Card label="Total Spend" value={fmt(metrics.total_spend)} />
      <Card
        label="Savings"
        value={fmt(metrics.savings)}
        sub={metrics.savings_rate != null ? `${metrics.savings_rate}% savings rate` : undefined}
      />
      <Card
        label="Period"
        value={metrics.period_start ?? '—'}
        sub={metrics.period_end ? `to ${metrics.period_end}` : undefined}
      />
    </div>
  )
}
