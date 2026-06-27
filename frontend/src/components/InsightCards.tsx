interface Props {
  insights: string[]
}

export default function InsightCards({ insights }: Props) {
  if (insights.length === 0) return null

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 font-semibold text-slate-900">Insights</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {insights.map((text, i) => (
          <div
            key={i}
            className="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-900"
          >
            {text}
          </div>
        ))}
      </div>
    </div>
  )
}
