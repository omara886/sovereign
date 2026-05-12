'use client'
import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Loader2, RefreshCw } from 'lucide-react'

const API = '/api/proxy'

const PROJECT_COLORS: Record<string, string> = {
  therapia:     '#4C1D95',
  qawwi:        '#1D4ED8',
  productbench: '#0F766E',
  sahmalgo:     '#B45309',
}

const STAGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  'Strategy':  { bg: '#EEF2FF', text: '#4F46E5', border: '#C7D2FE' },
  'Copy':      { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' },
  'Design':    { bg: '#F5F3FF', text: '#7C3AED', border: '#DDD6FE' },
  'Arabic QA': { bg: '#FFFBEB', text: '#D97706', border: '#FCD34D' },
  'Brand QA':  { bg: '#FFF7ED', text: '#EA580C', border: '#FED7AA' },
  'Approval':  { bg: '#FEF3C7', text: '#B45309', border: '#FDE68A' },
  'Scheduled': { bg: '#ECFEFF', text: '#0891B2', border: '#A5F3FC' },
  'Published': { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' },
  'Rejected':  { bg: '#F9FAFB', text: '#6B7280', border: '#E5E7EB' },
}

const CHANNEL_ICONS: Record<string, string> = {
  instagram: '📷', linkedin: '💼', x: '𝕏', google_ads: '🔍', email: '📧',
}

type AssetCard = {
  id: string
  project_name: string
  project_slug: string
  channel: string
  type: string
  language: string
  copy_ar: string
  copy_en: string
  thumbnail_url: string | null
  status: string
  qa_score: number | null
  created_at: string | null
}

type Stage = { name: string; count: number; assets: AssetCard[] }

function timeAgo(iso: string | null) {
  if (!iso) return ''
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (diff < 60) return `${diff}m`
  if (diff < 1440) return `${Math.floor(diff / 60)}h`
  return `${Math.floor(diff / 1440)}d`
}

function resolveThumb(url: string | null): string {
  if (!url) return ''
  if (url.startsWith('data:')) return url
  if (url.includes('...r2.dev/')) return `/api/img?url=${encodeURIComponent(url)}`
  if (url.includes('railway.app') || url.includes('localhost'))
    return `/api/img?url=${encodeURIComponent(url)}`
  return url
}

function AssetTile({ asset }: { asset: AssetCard }) {
  const projColor = PROJECT_COLORS[asset.project_slug] ?? '#6B7280'
  const thumb = resolveThumb(asset.thumbnail_url)

  return (
    <Link href={`/inbox?asset=${asset.id}`}>
      <div className="group bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 hover:shadow-card transition-all cursor-pointer">
        {/* Project + channel */}
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-2 h-2 rounded-full shrink-0" style={{ background: projColor }} />
          <span className="text-xs font-medium text-gray-700 truncate">{asset.project_name}</span>
          <span className="ml-auto text-sm">{CHANNEL_ICONS[asset.channel] ?? '📄'}</span>
        </div>

        {/* Thumbnail or copy preview */}
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={thumb} alt="" className="w-full aspect-square object-cover rounded mb-2" />
        ) : (
          <div className="w-full rounded mb-2 p-2 bg-gray-50 border border-gray-100">
            {asset.copy_ar ? (
              <p dir="rtl" className="font-arabic text-xs text-gray-800 line-clamp-3 leading-relaxed">{asset.copy_ar}</p>
            ) : (
              <p className="text-xs text-gray-500 line-clamp-3">{asset.copy_en}</p>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-gray-400">{timeAgo(asset.created_at)}</span>
          {asset.qa_score != null && (
            <span className={`text-xs font-mono font-medium ${asset.qa_score >= 70 ? 'text-emerald-600' : 'text-red-500'}`}>
              {asset.qa_score}%
            </span>
          )}
          <span className="text-xs text-gray-400 capitalize">{asset.type}</span>
        </div>
      </div>
    </Link>
  )
}

function StageColumn({ stage, filter }: { stage: Stage; filter: string }) {
  const colors = STAGE_COLORS[stage.name] ?? STAGE_COLORS['Copy']
  const assets = filter === 'all'
    ? stage.assets
    : stage.assets.filter(a => a.project_slug === filter)

  return (
    <div className="flex-none w-56">
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <div className="w-2 h-2 rounded-full" style={{ background: colors.text }} />
          <span className="text-xs font-semibold text-gray-700 truncate">{stage.name}</span>
        </div>
        {assets.length > 0 && (
          <span className="text-xs font-mono text-gray-400 shrink-0">{assets.length}</span>
        )}
      </div>

      {/* Cards */}
      <div className="space-y-2 min-h-[120px]">
        {assets.map(asset => (
          <AssetTile key={asset.id} asset={asset} />
        ))}
        {assets.length === 0 && (
          <div className="border border-dashed border-gray-200 rounded-lg h-20 flex items-center justify-center">
            <span className="text-xs text-gray-300">Empty</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function PipelinePage() {
  const [stages, setStages] = useState<Stage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [projects, setProjects] = useState<{ slug: string; name: string }[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [boardRes, projRes] = await Promise.all([
        fetch(`${API}/pipeline/board`),
        fetch(`${API}/projects`),
      ])
      if (boardRes.ok) setStages((await boardRes.json()).stages)
      else setError(`HTTP ${boardRes.status}`)
      if (projRes.ok) setProjects(await projRes.json())
    } catch {
      setError('Backend unreachable')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const totalAssets = stages.reduce((n, s) => n + s.count, 0)

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-full mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-gray-900">Pipeline Board</h1>
            <p className="text-xs text-gray-500 mt-0.5">{totalAssets} assets across all stages</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Project filter */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setFilter('all')}
                className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition-colors ${filter === 'all' ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                All
              </button>
              {projects.map(p => (
                <button
                  key={p.slug}
                  onClick={() => setFilter(p.slug)}
                  className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition-colors ${filter === p.slug ? 'text-white' : 'text-gray-600 hover:bg-gray-100'}`}
                  style={filter === p.slug ? { background: PROJECT_COLORS[p.slug] ?? '#4F46E5' } : {}}
                >
                  {p.name}
                </button>
              ))}
            </div>
            <button onClick={load} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Board */}
      <div className="overflow-x-auto px-6 py-5">
        {loading && (
          <div className="flex items-center gap-2 text-gray-400 py-16 justify-center">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Loading pipeline...</span>
          </div>
        )}
        {error && !loading && (
          <p className="text-sm text-red-500 text-center py-16">{error}</p>
        )}
        {!loading && !error && (
          <div className="flex gap-4 pb-4" style={{ minWidth: 'max-content' }}>
            {stages.map(stage => (
              <StageColumn key={stage.name} stage={stage} filter={filter} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
