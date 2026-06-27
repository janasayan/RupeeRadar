import { useState } from 'react'
import type { TransactionPage } from '../api/types'
import { CATEGORIES } from '../api/types'
import { updateTransactionCategory } from '../api/client'

const CATEGORY_COLOURS: Record<string, string> = {
  Food: 'bg-orange-100 text-orange-800',
  Travel: 'bg-blue-100 text-blue-800',
  Shopping: 'bg-pink-100 text-pink-800',
  Bills: 'bg-yellow-100 text-yellow-800',
  EMI: 'bg-red-100 text-red-800',
  Subscriptions: 'bg-purple-100 text-purple-800',
  Salary: 'bg-green-100 text-green-800',
  Rent: 'bg-cyan-100 text-cyan-800',
  Investments: 'bg-teal-100 text-teal-800',
  Other: 'bg-slate-100 text-slate-600',
}

interface Props {
  sessionId: string
  data: TransactionPage
  onPageChange: (page: number) => void
  onCategoryChanged?: () => void
}

export default function TransactionTable({ sessionId, data, onPageChange, onCategoryChanged }: Props) {
  const [search, setSearch] = useState('')
  const [updating, setUpdating] = useState<string | null>(null)

  const filtered = search
    ? data.items.filter(
        (t) =>
          t.description_clean.toLowerCase().includes(search.toLowerCase()) ||
          t.category.toLowerCase().includes(search.toLowerCase()) ||
          (t.merchant ?? '').toLowerCase().includes(search.toLowerCase()),
      )
    : data.items

  const totalPages = Math.ceil(data.total / data.page_size)

  async function handleCategoryChange(transactionId: string, category: string) {
    setUpdating(transactionId)
    try {
      await updateTransactionCategory(sessionId, transactionId, category)
      onCategoryChanged?.()
    } catch {
      // silently ignore — category reverts on next reload
    } finally {
      setUpdating(null)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">
          Transactions{' '}
          <span className="ml-1 text-sm font-normal text-slate-400">({data.total})</span>
        </h3>
        <input
          type="search"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-indigo-400"
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs text-slate-500 uppercase tracking-wide">
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Description</th>
              <th className="px-5 py-3">Category</th>
              <th className="px-5 py-3 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-slate-400">
                  No transactions match your search.
                </td>
              </tr>
            )}
            {filtered.map((txn) => (
              <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="whitespace-nowrap px-5 py-3 text-slate-500">
                  {txn.date}
                  {txn.is_recurring && (
                    <span className="ml-1.5 text-xs text-indigo-400" title="Recurring">↻</span>
                  )}
                </td>
                <td className="px-5 py-3">
                  <p className="font-medium text-slate-800">
                    {txn.merchant ?? txn.description_clean}
                  </p>
                  {txn.description_clean !== txn.description_raw && (
                    <p className="mt-0.5 text-xs text-slate-400 truncate max-w-xs">
                      {txn.description_raw}
                    </p>
                  )}
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-1.5">
                    <select
                      value={txn.category}
                      disabled={updating === txn.id}
                      onChange={(e) => handleCategoryChange(txn.id, e.target.value)}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium border-0 cursor-pointer appearance-none pr-5
                        ${CATEGORY_COLOURS[txn.category] ?? 'bg-slate-100 text-slate-600'}
                        ${updating === txn.id ? 'opacity-50' : ''}`}
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                    {txn.category_source === 'llm' && (
                      <span className="text-xs text-purple-400" title="AI categorized">AI</span>
                    )}
                    {txn.category_source === 'user' && (
                      <span className="text-xs text-emerald-500" title="User override">✓</span>
                    )}
                  </div>
                </td>
                <td
                  className={`whitespace-nowrap px-5 py-3 text-right font-medium ${
                    txn.txn_type === 'credit' ? 'text-emerald-600' : 'text-slate-800'
                  }`}
                >
                  {txn.txn_type === 'credit' ? '+' : ''}
                  ₹{Math.abs(txn.amount).toLocaleString('en-IN')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm text-slate-500">
          <span>
            Page {data.page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              onClick={() => onPageChange(data.page - 1)}
              className="rounded-lg border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              disabled={data.page >= totalPages}
              onClick={() => onPageChange(data.page + 1)}
              className="rounded-lg border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

