'use client'
import { useState, useEffect, useCallback } from 'react'
import { BarChart3, TrendingUp, TrendingDown, Minus, AlertCircle, Loader2 } from 'lucide-react'

const API = '/api/proxy'

const PROJECT_COLORS: Record<string, string> = {
  therapia: '#4C1D95', qawwi: '#1D4ED8', productbench: '#0F766E', sahmalgo: '#B45309',
}

type FunnelMetric = {
  label: string; value: number | string; target?: number | string
  unit?: string; trend?: 'up' | 'down' | 'flat'; delta?: string
  live: boolean; connector?: string
}

const SAMPLE_DATA: Record<string, FunnelMetric[]> = {
  therapia: [
    { label: 'Instagram Followers', value: 1240, target: 5000, unit: 'followers', trend: 'up', delta: '+87 this week', live: false, connector: 'Instagram' },
    { label: 'Profile Visits / Week', value: 3200, unit: 'visits', trend: 'up', delta: '+340 vs last week', live: false, connector: 'Instagram' },
    { label: 'App Downloads / Week', value: 148, target: 500, unit: 'downloads', trend: 'flat', delta: 'No change', live: false, connector: 'App Store / Play Store' },
    { label: 'Health Assessments Completed', value: 62, target: 200, unit: '/week', trend: 'up', delta: '+12 vs last week', live: false, connector: 'Therapia API' },
    { label: 'Visitor → Assessment Rate', value: '4.2%', target: '8%', trend: 'up', delta: '+0.4pp', live: false, connector: 'Google Analytics' },
    { label: 'Content Engagement Rate', value: '3.8%', trend: 'down', delta: '-0.6pp vs last week', live: false, connector: 'Instagram' },
  ],
  qawwi: [
    { label: 'Demo Requests This Week', value: 7, target: 20, trend: 'up', delta: '+3 vs last week', live: false, connector: 'CRM' },
    { label: 'Active Leads', value: 23, target: 50, unit: 'leads', trend: 'up', delta: '+5 this week', live: false, connector: 'CRM' },
    { label: 'LinkedIn Profile Clicks', value: 420, unit: '/week', trend: 'up', delta: '+120 vs last week', live: false, connector: 'LinkedIn' },
    { label: 'Coach Applications', value: 3, target: 10, unit: '/week', trend: 'flat', delta: 'No change', live: false, connector: 'Qawwi API' },
    { label: 'Cold Outreach Reply Rate', value: '12%', target: '20%', trend: 'up', delta: '+2pp', live: false, connector: 'Email / LinkedIn' },
  ],
  productbench: [
    { label: 'Waitlist Signups', value: 34, target: 200, unit: '/week', trend: 'up', delta: '+8 this week', live: false, connector: 'ProductBench API' },
    { label: 'LinkedIn Impressions', value: 2100, unit: '/week', trend: 'up', delta: '+400 vs last week', live: false, connector: 'LinkedIn' },
  ],
  sahmalgo: [
    { label: 'X Followers', value: 890, target: 5000, trend: 'up', delta: '+43 this week', live: false, connector: 'X API' },
    { label: 'Signups / Week', value: 28, target: 100, trend: 'up', delta: '+6 vs last week', live: false, connector: 'SahmAlgo API' },
  ],
}

function TrendIcon({ trend }: { trend?: 'up' | 'down' | 'flat' }) {
  if (trend === 'up') return <TrendingUp size={12} className="text-emerald-500" />
  if (trend === 'down') return <TrendingDown size={12} className="text-red-500" />
  return <Minus size={12} className="text-gray-400" />
}

function MetricCard({ m }: { m: FunnelMetric }) {
  const progress = typeof m.value === 'number' && typeof m.target === 'number'
    ? Math.min(100, Math.round((m.value / m.target) * 100)) : null

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-gray-600 leading-tight">{m.label}</p>
        {!m.live && <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200">Sample</span>}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold text-gray-900 font-mono">{m.value}</span>
        {m.unit && <span className="text-xs text-gray-400">{m.unit}</span>}
        {m.target && <span className="text-xs text-gray-400 ml-auto">/ {m.target} goal</span>}
      </div>
      {progress != null && (
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${progress}%`, background: progress >= 80 ? '#10B981' : progress >= 50 ? '#4F46E5' : '#F59E0B' }} />
        </div>
      )}
      {m.delta && (
        <div className="flex items-center gap-1">
          <TrendIcon trend={m.trend} />
          <span className={`text-xs ${m.trend === 'up' ? 'text-emerald-600' : m.trend === 'down' ? 'text-red-500' : 'text-gray-400'}`}>{m.delta}</span>
        </div>
      )}
      {!m.live && m.connector && (
        <p className="text-[10px] text-gray-400 pt-1 border-t border-gray-50">Connect {m.connector} for live data</p>
      )}
    </div>
  )
}

export default function AnalyticsPage() {
  const [projects, setProjects] = useState<{ id: string; slug: string; name: string }[]>([])
  const [assetStats, setAssetStats] = useState({ published: 0, pending: 0 })
  const [loading, setLoading] = useState(true)
  const [activeSlug, setActiveSlug] = useState('therapia')

  const load = useCallback(async () => {
    try {
      const [projRes, summaryRes] = await Promise.all([
        fetch(`${API}/projects`),
        fetch(`${API}/metrics/summary`),
      ])
      if (projRes.ok) {
        const data = await projRes.json()
        setProjects(data)
        if (data.length > 0) setActiveSlug(data[0].slug)
      }
      if (summaryRes.ok) {
        const s = await summaryRes.json()
        setAssetStats({ published: s.published_assets ?? 0, pending: s.pending_approvals ?? 0 })
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const activeProject = projects.find(p => p.slug === activeSlug)
  const metrics = SAMPLE_DATA[activeSlug] ?? []

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 size={18} className="text-gray-500" />
            <h1 className="text-base font-semibold text-gray-900">Analytics</h1>
          </div>
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            {loading ? <Loader2 size={14} className="animate-spin text-gray-400 mx-3" /> : projects.map(p => (
              <button key={p.slug} onClick={() => setActiveSlug(p.slug)}
                className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${activeSlug === p.slug ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-500 hover:text-gray-700'}`}
                style={activeSlug === p.slug ? { borderLeft: `3px solid ${PROJECT_COLORS[p.slug] ?? '#4F46E5'}` } : {}}>
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-3 h-3 rounded-full" style={{ background: PROJECT_COLORS[activeSlug] ?? '#6B7280' }} />
          <h2 className="text-sm font-semibold text-gray-900">{activeProject?.name ?? activeSlug} — Funnel Metrics</h2>
          <div className="ml-auto flex items-center gap-3 text-xs text-gray-500">
            <span><strong className="text-emerald-600">{assetStats.published}</strong> published</span>
            <span><strong className="text-amber-600">{assetStats.pending}</strong> pending approval</span>
          </div>
        </div>

        {metrics.some(m => !m.live) && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4 text-xs text-amber-700">
            <AlertCircle size={13} />
            Showing sample data — connect platform APIs to see real metrics
          </div>
        )}

        {metrics.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
            <BarChart3 size={28} className="text-gray-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-gray-700">No metrics configured yet</p>
            <p className="text-xs text-gray-400 mt-1">Run the pipeline first, then connect your analytics integrations</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {metrics.map((m, i) => <MetricCard key={i} m={m} />)}
          </div>
        )}

        <div className="mt-5 bg-indigo-50 border border-indigo-100 rounded-xl p-4">
          <p className="text-xs font-semibold text-indigo-700 mb-2">Connect live analytics</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {['Instagram Business API', 'LinkedIn Analytics', 'Google Analytics 4', 'App Store Connect'].map(name => (
              <div key={name} className="text-[11px] text-indigo-600 bg-white rounded-lg px-2 py-1.5 border border-indigo-100 text-center">{name}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
