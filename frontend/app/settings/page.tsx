'use client'
import { useEffect, useState } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { FetchError } from '@/components/ui/FetchError'
import { Card } from '@/components/ui/Card'

export default function SettingsPage() {
  const [backendUrl, setBackendUrl] = useState('Loading...')
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      setError('')
      try {
        const res = await fetch('/api/debug-url')
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`)
        }
        const text = await res.text()
        setBackendUrl(text.trim())
      } catch {
        setBackendUrl('Unavailable')
        setError('Could not load backend URL')
      }
    }
    void load()
  }, [])

  const reload = async () => {
    try {
      setError('')
      const res = await fetch('/api/debug-url')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const text = await res.text()
      setBackendUrl(text.trim())
    } catch {
      setBackendUrl('Unavailable')
      setError('Could not load backend URL')
    }
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Settings</h1>
        </div>
      </div>
      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-[7rem] space-y-4">
        {error && (
          <AnimatedContent delay={50}>
            <FetchError message={error} onRetry={reload} />
          </AnimatedContent>
        )}

        <AnimatedContent delay={100}>
          <Card>
            <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-3">Account</h2>
            <div className="space-y-2">
              <div className="flex justify-between items-center py-2">
                <span className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">Username</span>
                <span className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C]">omar</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">Email</span>
                <span className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C]">oalomran443@gmail.com</span>
              </div>
            </div>
          </Card>
        </AnimatedContent>

        <AnimatedContent delay={200}>
          <Card>
            <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-3">Automation Schedule</h2>
            <div className="space-y-2">
              {[
                ['Weekly Plan', 'Every Monday 8:00 AM Riyadh'],
                ['Plan Notification', 'Every Monday 9:00 AM Riyadh'],
                ['Publish Queue', 'Every 5 minutes'],
                ['Analytics Report', 'Every Sunday 6:00 PM Riyadh'],
              ].map(([label, schedule]) => (
                <div key={label} className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:items-center py-2 border-b border-[rgba(255,255,255,0.04)] last:border-0">
                  <span className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">{label}</span>
                  <span className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.4)] sm:text-right">{schedule}</span>
                </div>
              ))}
            </div>
          </Card>
        </AnimatedContent>

        <AnimatedContent delay={300}>
          <Card>
            <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-3">System Status</h2>
            <div className="space-y-2">
              <div className="flex justify-between items-center py-2">
                <span className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">Backend</span>
                <span className="font-['IBM_Plex_Mono'] text-sm text-[#10B981]">Connected</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">URL</span>
                <span className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C] break-all text-right max-w-[60%]">{backendUrl}</span>
              </div>
            </div>
          </Card>
        </AnimatedContent>
      </div>
    </div>
  )
}
