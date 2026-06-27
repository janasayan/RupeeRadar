import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import FileUpload from '../components/FileUpload'

export default function Landing() {
  const navigate = useNavigate()

  const handleUploaded = useCallback(
    (sessionId: string, warnings: string[]) => {
      navigate(`/analysis/${sessionId}`, { state: { warnings } })
    },
    [navigate],
  )

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">
            ₹
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900">RupeeRadar</h1>
            <p className="text-sm text-slate-500">Personal finance insights from bank statements</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-16">
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold text-slate-900">
            Understand where your money goes
          </h2>
          <p className="mt-3 text-slate-500">
            Upload your HDFC, ICICI, or any bank statement CSV / Excel file and get categorized expenses,
            spending insights, and a clear dashboard — in seconds.
          </p>
        </div>

        <FileUpload onUploaded={handleUploaded} />

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[
            { icon: '🏷️', title: 'Auto-categorize', desc: 'Food, Travel, EMI, Subscriptions & more.' },
            { icon: '📊', title: 'Visual breakdown', desc: 'See exactly where each rupee went.' },
            { icon: '💡', title: 'Smart insights', desc: 'Top spends and personalized summaries.' },
          ].map((card) => (
            <div key={card.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm text-center">
              <div className="text-2xl">{card.icon}</div>
              <h3 className="mt-2 font-semibold text-slate-900">{card.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{card.desc}</p>
            </div>
          ))}
        </div>

        <p className="mt-8 text-center text-xs text-slate-400">
          Your data is processed in-memory and auto-deleted after 24 hours.
          We never store your raw file or share transaction data with third parties.
        </p>
      </main>
    </div>
  )
}
