'use client'
import { useState, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import {
  CheckCircle, ChevronRight, Inbox, Loader2, RefreshCw,
  ThumbsDown, ThumbsUp, ImageOff, AlertTriangle, CheckCheck
} from 'lucide-react'

const API = '/api/proxy'

const PROJECT_COLORS: Record<string, string> = {
  therapia:     '#4C1D95',
  qawwi:        '#1D4ED8',
  productbench: '#0F766E',
  sahmalgo:     '#B45309',
}

const CHANNEL_LABELS: Record<string, string> = {
  instagram: 'Instagram', linkedin: 'LinkedIn', x: 'X / Twitter', google_ads: 'Google Ads'
}

const FUNNEL_LABELS: Record<string, string> = {
  awareness: 'Brand Awareness', consideration: 'Consideration',
  conversion: 'Conversion', retention: 'Retention',
}

const ASSET_TYPE_LABELS: Record<string, string> = {
  post: 'Single Post', carousel: 'Carousel', story: 'Story', reel: 'Reel',
  ad_creative: 'Ad Creative', ad_copy: 'Ad Copy', email: 'Email',
}

interface Approval {
  id: string
  asset_id: string | null
  weekly_plan_id: string | null
  decision: string | null
  created_at: string
}
interface Asset {
  id: string
  project_id: string
  type: string
  channel: string
  language: string
  copy_ar: string | null
  copy_en: string | null
  cta_ar: string | null
  cta_en: string | null
  design_thumbnail_url: string | null
  design_url: string | null
  qa_score: number | null
  qa_notes: unknown[] | null
  status: string
}
interface Project { id: string; slug: string; name: string }
interface WeeklyPlan { id: string; objective: string; funnel_focus: string; total_budget_estimate: number }

function resolveImgUrl(url: string): string {
  if (!url) return ''
  if (url.startsWith('data:')) return url
  if (url.startsWith('file://')) return ''
  if (url.includes('...r2.dev/')) return `/api/img?url=${encodeURIComponent(url)}`
  if (url.includes('sovereign-backend.railway.app'))
    url = url.replace('sovereign-backend', 'backend-production-37a17')
  if (url.includes('railway.app') || url.includes('localhost'))
    return `/api/img?url=${encodeURIComponent(url)}`
  return url
}

function QABadge({ label, passed }: { label: string; passed: boolean | null }) {
  if (passed === null) return null
  return (
    <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md ${passed ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
      {passed ? <CheckCheck size={11} /> : <AlertTriangle size={11} />}
      {label}
    </div>
  )
}

function AssetPreview({ url, onFail }: { url: string | null; onFail?: () => void }) {
  const [broken, setBroken] = useState(false)
  const src = url ? resolveImgUrl(url) : ''

  // Missing URL = immediate fail
  if (!src) {
    onFail?.()
    return (
      <div className="w-full aspect-square bg-red-50 border border-red-200 rounded-xl flex flex-col items-center justify-center gap-2">
        <ImageOff size={28} className="text-red-400" />
        <p className="text-xs font-medium text-red-600 text-center px-4">No creative URL — cannot approve</p>
      </div>
    )
  }

  if (broken) {
    return (
      <div className="w-full aspect-square bg-red-50 border border-red-200 rounded-xl flex flex-col items-center justify-center gap-2">
        <ImageOff size={28} className="text-red-400" />
        <p className="text-xs font-medium text-red-600 text-center px-4">Creative failed to render — cannot approve</p>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      className="w-full aspect-square object-cover rounded-xl border border-gray-200"
      onError={() => { setBroken(true); onFail?.() }}
    />
  )
}

function ApprovalCockpit({
  asset,
  project,
  plan,
  onApprove,
  onReject,
  deciding,
}: {
  approval?: Approval
  asset: Asset | null
  project: Project | null
  plan: WeeklyPlan | null
  onApprove: () => Promise<void>
  onReject: (reason: string) => Promise<void>
  deciding: boolean
}) {
  const [showReject, setShowReject] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [previewFailed, setPreviewFailed] = useState(false)

  const projColor = project ? (PROJECT_COLORS[project.slug] ?? '#6B7280') : '#6B7280'
  const qaScore = previewFailed ? null : asset?.qa_score
  const qaChecks = (asset?.qa_notes as Array<{ check_name: string; status: string; note?: string }> | null) ?? []
  const arabicQA = qaChecks.find(c => c.check_name === 'arabic_script_qa')
  const brandQA = qaChecks.find(c => c.check_name === 'tone_match' || c.check_name === 'copy_validation')

  // Safety gates — all must pass for Approve to be available
  const safetyChecks = [
    { label: 'Creative renders', passed: !previewFailed, blocking: true },
    { label: 'Arabic script clean', passed: arabicQA ? arabicQA.status === 'pass' : true, blocking: true },
    { label: `QA score ≥ 70 (${asset?.qa_score ?? '—'})`, passed: !previewFailed && (asset?.qa_score ?? 0) >= 70, blocking: true },
    { label: 'Channel set', passed: !!asset?.channel, blocking: false },
  ]
  const isBlocked = safetyChecks.some(c => c.blocking && !c.passed)

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-card">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
        <div className="w-3 h-3 rounded-full shrink-0" style={{ background: projColor }} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900">{project?.name ?? 'Unknown'}</p>
          <p className="text-xs text-gray-500">
            {CHANNEL_LABELS[asset?.channel ?? ''] ?? asset?.channel}
            {' · '}
            {ASSET_TYPE_LABELS[asset?.type ?? ''] ?? asset?.type}
            {' · '}
            {FUNNEL_LABELS[asset?.type ?? ''] ?? 'Awareness'}
          </p>
        </div>
        {previewFailed ? (
          <div className="text-xs font-semibold px-2 py-1 rounded-md bg-red-50 text-red-600 flex items-center gap-1">
            <AlertTriangle size={11} /> Blocked
          </div>
        ) : qaScore != null ? (
          <div className={`text-xs font-mono font-semibold px-2 py-1 rounded-md ${qaScore >= 70 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
            QA {qaScore}
          </div>
        ) : null}
      </div>

      <div className="p-5 space-y-4">
        {/* Creative preview */}
        <AssetPreview
          url={asset?.design_thumbnail_url ?? asset?.design_url ?? null}
          onFail={() => setPreviewFailed(true)}
        />

        {/* Copy */}
        {asset?.copy_ar && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Arabic Copy</p>
            <p dir="rtl" className="font-arabic text-sm text-gray-900 leading-relaxed bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-100">
              {asset.copy_ar}
            </p>
            {asset.cta_ar && (
              <p dir="rtl" className="font-arabic text-xs text-indigo-700 bg-indigo-50 rounded px-2 py-1 mt-1 w-fit mr-auto">
                CTA: {asset.cta_ar}
              </p>
            )}
          </div>
        )}
        {asset?.copy_en && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">English Copy</p>
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-100">{asset.copy_en}</p>
            {asset.cta_en && (
              <p className="text-xs text-indigo-700 bg-indigo-50 rounded px-2 py-1 mt-1 w-fit">
                CTA: {asset.cta_en}
              </p>
            )}
          </div>
        )}

        {/* Safety checklist — always visible */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Safety Checks</p>
          {safetyChecks.map((c, i) => (
            <div key={i} className={`flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-md ${c.passed ? 'bg-emerald-50 text-emerald-700' : c.blocking ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'}`}>
              {c.passed ? <CheckCheck size={11} /> : <AlertTriangle size={11} />}
              {c.label}
              {!c.passed && c.blocking && <span className="ml-auto font-semibold">BLOCKED</span>}
            </div>
          ))}
        </div>

        {/* Post-approval context */}
        <div className="bg-gray-50 rounded-lg px-3 py-2.5 space-y-1 border border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">After approval</p>
          <p className="text-sm text-gray-800">
            Moves to publish queue for <strong>{CHANNEL_LABELS[asset?.channel ?? ''] ?? asset?.channel ?? 'Unknown channel'}</strong>
          </p>
          {plan && (
            <p className="text-xs text-gray-500">
              Goal: <span className="font-medium text-gray-700">{plan.funnel_focus ? (FUNNEL_LABELS[plan.funnel_focus] ?? plan.funnel_focus) : '—'}</span>
              {' · '}
              {plan.objective?.slice(0, 80)}
            </p>
          )}
        </div>

        {/* QA detail */}
        {(arabicQA || brandQA) && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">QA Detail</p>
            <div className="flex flex-wrap gap-2">
              <QABadge label="Arabic Script" passed={arabicQA ? arabicQA.status === 'pass' : null} />
              <QABadge label="Brand Voice" passed={brandQA ? brandQA.status === 'pass' : null} />
            </div>
            {qaChecks.filter(c => c.status === 'fail').map((c, i) => (
              <p key={i} className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">{c.note || c.check_name}</p>
            ))}
          </div>
        )}

        {/* Reject reason input */}
        {showReject && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500">
              Rejection reason — becomes a negative memory example for the AI
            </p>
            <textarea
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              rows={3}
              placeholder="What went wrong? e.g. Wrong tone, too clinical, CTA doesn't match brand voice..."
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:border-indigo-400 text-gray-800 placeholder:text-gray-400"
            />
          </div>
        )}

        {/* Actions */}
        {!showReject ? (
          <div className="space-y-2 pt-1">
            {isBlocked && (
              <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
                <AlertTriangle size={14} className="text-red-500 shrink-0" />
                <p className="text-xs font-medium text-red-700">
                  Approval blocked — {previewFailed ? 'creative preview failed to render' : 'one or more safety checks failed'}
                </p>
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => onApprove()}
                disabled={deciding || isBlocked}
                title={isBlocked ? 'Fix safety check failures before approving' : 'Approve and add to publish queue'}
                className={`flex-1 flex items-center justify-center gap-2 text-sm font-semibold rounded-lg py-2.5 min-h-[44px] transition-colors ${
                  isBlocked
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-900 hover:bg-gray-800 text-white disabled:opacity-40'
                }`}
              >
                {deciding ? <Loader2 size={14} className="animate-spin" /> : <ThumbsUp size={14} />}
                {isBlocked ? 'Blocked' : 'Approve'}
              </button>
              <button
                onClick={() => setShowReject(true)}
                disabled={deciding}
                className="flex-1 flex items-center justify-center gap-2 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg py-2.5 min-h-[44px] disabled:opacity-40 hover:bg-gray-50 transition-colors"
              >
                <ThumbsDown size={14} /> Reject
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => { setShowReject(false); setRejectReason('') }}
              className="flex-none px-4 border border-gray-200 text-gray-600 text-sm rounded-lg py-2.5 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => onReject(rejectReason)}
              disabled={deciding}
              className="flex-1 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white text-sm font-semibold rounded-lg py-2.5 disabled:opacity-40 transition-colors"
            >
              {deciding ? <Loader2 size={14} className="animate-spin" /> : <ThumbsDown size={14} />}
              Confirm Reject
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function InboxPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [assets, setAssets] = useState<Record<string, Asset>>({})
  const [plans, setPlans] = useState<Record<string, WeeklyPlan>>({})
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [toast, setToast] = useState<string | null>(null)
  const [filterSlug, setFilterSlug] = useState('all')
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [appRes, projRes] = await Promise.all([
        fetch(`${API}/approvals?status=pending`),
        fetch(`${API}/projects`),
      ])
      if (projRes.ok) setProjects(await projRes.json())
      if (!appRes.ok) throw new Error(`HTTP ${appRes.status}`)
      const data: Approval[] = await appRes.json()
      setApprovals(data)

      const assetMap: Record<string, Asset> = {}
      const planMap: Record<string, WeeklyPlan> = {}
      await Promise.all(data.map(async a => {
        if (a.asset_id) {
          const r = await fetch(`${API}/assets/${a.asset_id}`)
          if (r.ok) assetMap[a.asset_id] = await r.json()
        }
        if (a.weekly_plan_id && !planMap[a.weekly_plan_id]) {
          const r = await fetch(`${API}/plans/${a.weekly_plan_id}`)
          if (r.ok) planMap[a.weekly_plan_id] = await r.json()
        }
      }))
      setAssets(assetMap)
      setPlans(planMap)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not load inbox')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void fetchAll() }, [fetchAll])

  const decide = async (approvalId: string, decision: 'approved' | 'rejected', reason?: string) => {
    setDeciding(approvalId)
    try {
      await fetch(`${API}/approvals/${approvalId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, rejection_reason: reason ?? null }),
      })
      setToast(decision === 'approved' ? 'Approved — scheduled for publishing' : 'Rejected — saved as negative example')
      setApprovals(prev => prev.filter(a => a.id !== approvalId))
      setActiveIndex(i => Math.max(0, i - 1))
    } finally {
      setDeciding(null)
    }
  }

  const projectMap = useMemo(() => {
    const m = new Map<string, Project>()
    projects.forEach(p => m.set(p.id, p))
    return m
  }, [projects])

  const pending = useMemo(() => {
    const filtered = filterSlug === 'all'
      ? approvals.filter(a => a.decision == null)
      : approvals.filter(a => {
        if (a.decision != null) return false
        const asset = a.asset_id ? assets[a.asset_id] : null
        if (!asset) return true
        const proj = projectMap.get(asset.project_id)
        return proj?.slug === filterSlug
      })
    return filtered
  }, [approvals, assets, projectMap, filterSlug])

  const current = pending[activeIndex] ?? null
  const currentAsset = current?.asset_id ? assets[current.asset_id] ?? null : null
  const currentProject = currentAsset ? projectMap.get(currentAsset.project_id) ?? null : null
  const currentPlan = current?.weekly_plan_id ? plans[current.weekly_plan_id] ?? null : null

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-gray-900 text-white text-sm font-medium px-4 py-2.5 rounded-lg shadow-elevated flex items-center gap-2">
          <CheckCircle size={14} className="text-emerald-400" />
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox size={18} className="text-gray-500" />
            <h1 className="text-base font-semibold text-gray-900">Approval Inbox</h1>
            {pending.length > 0 && (
              <span className="bg-indigo-600 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
                {pending.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Filter tabs */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setFilterSlug('all')}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${filterSlug === 'all' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-600'}`}
              >
                All
              </button>
              {projects.map(p => (
                <button
                  key={p.slug}
                  onClick={() => setFilterSlug(p.slug)}
                  className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${filterSlug === p.slug ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-600'}`}
                >
                  {p.name}
                </button>
              ))}
            </div>
            <button onClick={fetchAll} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6">
        {loading && (
          <div className="flex items-center justify-center gap-2 text-gray-400 py-24">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Loading inbox...</span>
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-16">
            <p className="text-sm text-red-500">{error}</p>
            <button onClick={fetchAll} className="mt-3 text-sm text-indigo-600 hover:underline">Retry</button>
          </div>
        )}

        {!loading && !error && pending.length === 0 && (
          <div className="text-center py-24">
            <CheckCircle size={40} className="text-emerald-400 mx-auto mb-3" />
            <p className="text-base font-semibold text-gray-900">All clear</p>
            <p className="text-sm text-gray-500 mt-1">No assets waiting for approval</p>
            <Link href="/pipeline" className="mt-4 inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline">
              View pipeline board <ChevronRight size={14} />
            </Link>
          </div>
        )}

        {!loading && !error && pending.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
            {/* Left — queue list */}
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">
                Queue — {pending.length} pending
              </p>
              {pending.map((approval, idx) => {
                const asset = approval.asset_id ? assets[approval.asset_id] : null
                const proj = asset ? projectMap.get(asset.project_id) : null
                const projColor = proj ? (PROJECT_COLORS[proj.slug] ?? '#6B7280') : '#6B7280'
                const isActive = idx === activeIndex

                return (
                  <button
                    key={approval.id}
                    onClick={() => setActiveIndex(idx)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${isActive ? 'bg-white border border-gray-200 shadow-xs' : 'hover:bg-white hover:border-gray-200 border border-transparent'}`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: projColor }} />
                      <span className="text-sm font-medium text-gray-800 truncate">{proj?.name ?? '—'}</span>
                      <span className="text-xs text-gray-400 ml-auto shrink-0">{CHANNEL_LABELS[asset?.channel ?? ''] ?? asset?.channel ?? '—'}</span>
                    </div>
                    {asset?.copy_ar && (
                      <p dir="rtl" className="font-arabic text-xs text-gray-500 truncate mt-1">{asset.copy_ar}</p>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Right — cockpit */}
            <div>
              {current ? (
                <ApprovalCockpit
                  approval={current}
                  asset={currentAsset}
                  project={currentProject}
                  plan={currentPlan}
                  deciding={deciding === current.id}
                  onApprove={() => decide(current.id, 'approved')}
                  onReject={(reason) => decide(current.id, 'rejected', reason)}
                />
              ) : (
                <div className="bg-white border border-gray-200 rounded-xl h-64 flex items-center justify-center">
                  <p className="text-sm text-gray-400">Select an item from the queue</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
