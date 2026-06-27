import { Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/analysis/:sessionId" element={<Dashboard />} />
      <Route
        path="*"
        element={
          <div className="flex min-h-screen flex-col items-center justify-center gap-4">
            <p className="text-lg font-semibold text-slate-700">Page not found</p>
            <a href="/" className="text-indigo-600 underline">Go back home</a>
          </div>
        }
      />
    </Routes>
  )
}
