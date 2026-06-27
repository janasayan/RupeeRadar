import { useCallback, useRef, useState } from 'react'
import { uploadStatement } from '../api/client'

interface Props {
  onUploaded: (sessionId: string, warnings: string[]) => void
}

export default function FileUpload({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      setLoading(true)
      try {
        const resp = await uploadStatement(file)
        onUploaded(resp.session_id, resp.warnings)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setLoading(false)
      }
    },
    [onUploaded],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
          dragging
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-slate-300 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50/40'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={onInputChange}
        />
        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
            <p className="text-sm font-medium text-slate-600">Analysing your statement…</p>
          </div>
        ) : (
          <>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 text-2xl">
              📂
            </div>
            <p className="text-base font-medium text-slate-800">
              Drop your bank statement here
            </p>
            <p className="mt-1 text-sm text-slate-500">or click to browse — HDFC, ICICI, or any bank CSV / Excel</p>
            <p className="mt-3 text-xs text-slate-400">Max 10 MB · CSV or XLSX</p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  )
}
