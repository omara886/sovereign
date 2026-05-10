'use client'
import { useEffect, useState } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import CountUp from '@/components/react-bits/CountUp'
import { Card } from '@/components/ui/Card'
import { BarChart3, Loader2 } from 'lucide-react'

type MetricsSummary = {
  published_assets: number
  pending_approvals: number
  total_assets_generated: number
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/proxy/metrics/summary')
        if (res.ok) setSummary(await res.json())
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Analytics</h1>
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mt-1">
            Performance metrics across all projects.
          </p>
        </div>
      </div>
      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8">
        <AnimatedContent delay={100}>
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { label: 'Published Assets', value: summary?.published_assets ?? 0 },
                { label: 'Pending Approvals', value: summary?.pending_approvals ?? 0 },
                { label: 'Total Assets', value: summary?.total_assets_generated ?? 0 },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-2xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.05)] p-4">
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-2">{label}</p>
                  <p className="font-['IBM_Plex_Mono'] text-3xl text-[#F8F6F1]">
                    {loading ? <Loader2 size={18} className="animate-spin text-[#C9A84C]" /> : <CountUp end={value} />}
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-2 text-[rgba(248,246,241,0.45)]">
              <BarChart3 size={16} className="text-[#C9A84C]" />
              <p className="font-['IBM_Plex_Sans'] text-sm">Metrics populate as assets are published. Run the pipeline to get started.</p>
            </div>
          </Card>
        </AnimatedContent>
      </div>
    </div>
  )
}
