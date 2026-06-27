import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Metrics } from '../api/types'

interface Props {
  metrics: Metrics
}

const fmt = (v: number) => (v >= 1000 ? `₹${(v / 1000).toFixed(0)}k` : `₹${v}`)

export default function MonthlyTrendChart({ metrics }: Props) {
  const data = metrics.monthly_breakdown.map((m) => ({
    month: m.month,
    Income: m.income,
    Spend: m.spend,
  }))

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 font-semibold text-slate-900">Monthly Trend</h3>
        <p className="text-sm text-slate-500">Not enough data for monthly breakdown</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 font-semibold text-slate-900">Monthly Trend</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
          <Tooltip
            formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, '']}
          />
          <Legend />
          <Bar dataKey="Income" fill="#10b981" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Spend" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
