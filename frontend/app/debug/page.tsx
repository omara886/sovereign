'use client'
import { useState } from 'react'
import { Card } from '@/components/ui/Card'

export default function DebugPage() {
  const [results, setResults] = useState<string[]>([])

  const log = (msg: string) => setResults(p => [...p, msg])

  const test = async () => {
    setResults([])

    // 1. Health
    try {
      const r = await fetch('/api/proxy/health')
      log(`Health: ${r.status} — ${await r.text()}`)
    } catch (e) { log(`Health ERROR: ${e}`) }

    // 2. Upload test
    try {
      const form = new FormData()
      const blob = new Blob(['test'], { type: 'text/plain' })
      form.append('file', blob, 'test.txt')
      form.append('file_type', 'other')
      const r = await fetch('/api/proxy/uploads/therapia', { method: 'POST', body: form })
      const text = await r.text()
      log(`Upload: ${r.status} — ${text.slice(0, 300)}`)
    } catch (e) { log(`Upload ERROR: ${e}`) }

    // 3. Backend URL
    try {
      const r = await fetch('/api/debug-url')
      log(`Backend URL: ${await r.text()}`)
    } catch (e) { log(`URL check: ${e}`) }
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] p-6">
      <Card>
        <h1 className="font-['IBM_Plex_Sans'] text-lg text-[#F8F6F1] mb-4">Debug</h1>
        <button onClick={test}
          className="bg-[#C9A84C] text-[#0A0A0A] font-bold px-6 py-3 rounded-xl mb-4 font-['IBM_Plex_Sans']">
          Run Tests
        </button>
        <div className="space-y-2">
          {results.map((r, i) => (
            <p key={i} className="font-['IBM_Plex_Mono'] text-xs text-[#F8F6F1] bg-[#0A0A0A] p-2 rounded">{r}</p>
          ))}
        </div>
      </Card>
    </div>
  )
}
