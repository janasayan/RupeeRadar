import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Metrics } from '../api/types'

const COLOURS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#3b82f6', '#ef4444', '#14b8a6', '#f97316', '#64748b',
]

interface Props {
  metrics: Metrics
}

export default function CategoryChart({ metrics }: Props) {
  const data = metrics.top_categories.map((c) => ({
    name: c.category,
    amount: c.total,
  }))

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 font-semibold text-slate-900">Spend by Category</h3>
        <p className="text-sm text-slate-500">No spend data</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 font-semibold text-slate-900">Spend by Category</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) =>
              v >= 1000 ? `₹${(v / 1000).toFixed(0)}k` : `₹${v}`
            }
          />
          <Tooltip
            formatter={(v) =>
              [`₹${Number(v).toLocaleString('en-IN')}`, 'Amount']
            }
          />
          <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLOURS[i % COLOURS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
