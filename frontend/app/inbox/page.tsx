'use client'
import { useState, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'
import { ProjectImage } from '@/components/ui/ProjectImage'
import { Check, Inbox, RefreshCw, ThumbsUp, ThumbsDown, X, Eye, ImageOff } from "lucide-react"

const FILTERS = ['All', 'Therapia', 'Qawwi', 'ProductBench', 'SahmAlgo']
const CHANNEL_LABELS: Record<string, string> = {
  instagram: 'Instagram', linkedin: 'LinkedIn', x: 'X / Twitter', google_ads: 'Google Ads'
}
const API = '/api/proxy'

interface Approval { id: string; asset_id: string | null; weekly_plan_id: string | null; decision: string | null; created_at: string }
interface Asset { id: string; project_id: string; type: string; channel: string; language: string; copy_ar: string | null; copy_en: string | null; design_thumbnail_url: string | null; design_url: string | null; qa_score: number | null; status: string }
interface WeeklyPlan { id: string; objective: string; funnel_focus: string; rationale: string; tactics: unknown[]; status: string; total_budget_estimate: number }
interface Project { id: string; slug: string; name: string }
interface PublishJob { id: string; asset_id: string; approval_id: string; channel: string; scheduled_at: string; published_at: string | null; platform_post_id: string | null; status: string; error_message: string | null }

const PROJECT_FILTERS: Record<string, string> = {
  Therapia: 'therapia',
  Qawwi: 'qawwi',
  ProductBench: 'productbench',
  SahmAlgo: 'sahmalgo',
}

function resolveImgUrl(url: string): string {
  if (url.startsWith('data:')) return url
  if (url.includes('sovereign-backend.railway.app'))
    url = url.replace('sovereign-backend', 'backend-production-37a17')
  if (url.startsWith('file://')) return ''
  if (url.includes('railway.app') || url.includes('localhost'))
    return `/api/img?url=${encodeURIComponent(url)}`
  return url
}

function ImageViewer({ url, onFullscreen }: { url: string | null | undefined; onFullscreen: (u: string) => void }) {
  const [broken, setBroken] = useState(false)
  if (!url) return null
  const src = resolveImgUrl(url)
  if (!src) return null
  return (
    <div className="px-5 pt-5">
      <button type="button" style={{ width: '100%', display: 'block', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }} onClick={() => onFullscreen(url)}>
        {broken ? (
          <div style={{ width: '100%', aspectRatio: '1/1', borderRadius: 10, background: '#0A0A0A', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ImageOff size={32} style={{ color: 'rgba(248,246,241,0.1)' }} />
          </div>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt="" style={{ width: '100%', aspectRatio: '1/1', objectFit: 'cover', borderRadius: 10, display: 'block' }} onError={() => setBroken(true)} />
        )}
        <p style={{ fontSize: 11, color: 'rgba(248,246,241,0.35)', textAlign: 'center', marginTop: 8 }}>Tap image to view full size</p>
      </button>
    </div>
  )
}

function PlanSummary({ planId }: { planId: string }) {
  const [plan, setPlan] = useState<WeeklyPlan | null>(null)
  useEffect(() => {
    fetch(`${API}/plans/${planId}`).then(r => r.ok ? r.json() : null).then(d => d && setPlan(d))
  }, [planId])
  if (!plan) return <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)]">Loading plan...</p>
  return (
    <div className="space-y-3">
      <div>
        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-1 uppercase tracking-wider">Weekly Plan</p>
        <p className="font-['Cormorant_Garamond'] text-lg text-[#F8F6F1]">{plan.objective}</p>
      </div>
      <div className="flex gap-2 flex-wrap">
        <Badge variant="gold">{plan.funnel_focus}</Badge>
        <Badge variant="default">{Array.isArray(plan.tactics) ? plan.tactics.length : 0} tactics</Badge>
        <Badge variant="default">SAR {Number(plan.total_budget_estimate||0).toLocaleString('en-US')}</Badge>
      </div>
      {plan.rationale && <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)] leading-relaxed">{plan.rationale}</p>}
      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)]">Approve this plan to start generating content automatically.</p>
    </div>
  )
}

function DetailModal({ approval, asset, onApprove, onReject, onClose, deciding, onFullscreen }: {
  approval: Approval; asset: Asset | null; deciding: boolean;
  onApprove: () => Promise<void>; onReject: (reason: string) => Promise<void>; onClose: () => void;
  onFullscreen: (u: string) => void;
}) {
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-[20px] p-[2px] border border-[rgba(255,255,255,0.06)]" style={{
        background: 'linear-gradient(135deg, rgba(201,168,76,0.14), rgba(10,10,10,0.2) 55%, transparent)',
      }}>
        <div className="rounded-[18px] bg-[#1E293B]">
          <div className="flex items-center justify-between p-5 border-b border-[rgba(255,255,255,0.06)]">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.2)] px-2 py-0.5 rounded-full">
                {asset ? CHANNEL_LABELS[asset.channel] || asset.channel : 'Plan'}
              </span>
              {asset?.type && <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)]">{asset.type}</span>}
              {!!asset?.qa_score && <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">QA {asset.qa_score}/100</span>}
              <span className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.35)]">#{approval.id.slice(0, 8)}</span>
            </div>
            <button onClick={onClose} className="text-[rgba(248,246,241,0.4)] hover:text-[#F8F6F1] p-2 min-h-[44px] min-w-[44px] flex items-center justify-center">
              <X size={18} />
            </button>
          </div>

          {(asset?.design_url || asset?.design_thumbnail_url) && (
            <ImageViewer url={asset.design_url || asset.design_thumbnail_url} onFullscreen={onFullscreen} />
          )}

          <div className="p-5 space-y-4">
            {asset?.copy_en && (
              <div>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-2 uppercase tracking-wider">English Copy</p>
                <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] leading-relaxed whitespace-pre-wrap">{asset.copy_en}</p>
              </div>
            )}
            {asset?.copy_ar && (
              <div>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-2 uppercase tracking-wider">Arabic Copy</p>
                <p className="font-['Cairo'] text-sm text-[#F8F6F1] leading-relaxed" dir="rtl">{asset.copy_ar}</p>
              </div>
            )}
            {/* Plan approval — show plan details */}
            {!asset && approval.weekly_plan_id && (
              <PlanSummary planId={approval.weekly_plan_id} />
            )}
          </div>

          {showReject && (
            <div className="px-5 pb-2">
              <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-2">
                Why are you rejecting? The AI learns from this.
              </p>
              <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                placeholder="e.g. Wrong tone, mentions psychological content, off-brand..."
                rows={3}
                className="w-full bg-[#0A0A0A] border border-[rgba(255,255,255,0.1)] rounded-xl px-4 py-3 font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] outline-none focus:border-[#C9A84C] resize-none transition-colors"
              />
            </div>
          )}

          <div className="flex flex-col gap-2 p-5 pt-3 sm:flex-row">
            {!showReject ? (
              <>
                <button onClick={async () => { setSubmitting(true); await onApprove(); setSubmitting(false); onClose() }} disabled={deciding || submitting}
                  className="w-full sm:flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-base font-semibold text-[#10B981] bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.25)] rounded-xl py-3 min-h-[56px] hover:bg-[rgba(16,185,129,0.2)] transition-all disabled:opacity-40">
                  <ThumbsUp size={15} /> Approve
                </button>
                <button onClick={() => setShowReject(true)}
                  className="w-full sm:flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-base font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-xl py-3 min-h-[56px] hover:bg-[rgba(239,68,68,0.2)] transition-all">
                  <ThumbsDown size={15} /> Reject
                </button>
              </>
            ) : (
              <>
                <button onClick={() => setShowReject(false)}
                  className="w-full sm:flex-1 font-['IBM_Plex_Sans'] text-base text-[rgba(248,246,241,0.5)] border border-[rgba(255,255,255,0.1)] rounded-xl py-3 min-h-[56px]">
                  Back
                </button>
                <button onClick={async () => { setSubmitting(true); await onReject(rejectReason || ''); setSubmitting(false); onClose() }} disabled={submitting}
                  className="w-full sm:flex-1 font-['IBM_Plex_Sans'] text-base font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-xl py-3 min-h-[56px] disabled:opacity-40 hover:bg-[rgba(239,68,68,0.2)] transition-all">
                  {submitting ? 'Saving...' : rejectReason ? 'Reject & Save Feedback' : 'Reject'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function InboxPage() {
  const [filter, setFilter] = useState('All')
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [assets, setAssets] = useState<Record<string, Asset>>({})
  const [plans, setPlans] = useState<Record<string, WeeklyPlan>>({})
  const [projects, setProjects] = useState<Project[]>([])
  const [publishedJobs, setPublishedJobs] = useState<PublishJob[]>([])
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<{ approval: Approval; asset: Asset | null; plan: WeeklyPlan | null } | null>(null)
  const [toast, setToast] = useState<{ msg: string; color: string } | null>(null)
  const [bulkProgress, setBulkProgress] = useState('')
  // Fullscreen image — rendered at PAGE level to escape overflow:auto clipping (iOS Safari bug)
  const [fullscreenUrl, setFullscreenUrl] = useState<string | null>(null)

  const fetchProjects = useCallback(async () => {
    const res = await fetch(`${API}/projects`)
    if (res.ok) setProjects(await res.json())
  }, [])

  const fetchApprovals = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/approvals?status=pending`)
      if (!res.ok) throw new Error()
      const data: Approval[] = await res.json()
      setApprovals(data)
      const assetMap: Record<string, Asset> = {}
      const planMap: Record<string, WeeklyPlan> = {}
      await Promise.all(data.map(async a => {
        if (a.asset_id) {
          const ar = await fetch(`${API}/assets/${a.asset_id}`)
          if (ar.ok) assetMap[a.asset_id] = await ar.json()
        }
        if (a.weekly_plan_id) {
          const pr = await fetch(`${API}/plans/${a.weekly_plan_id}`)
          if (pr.ok) planMap[a.weekly_plan_id] = await pr.json()
        }
      }))
      setAssets(assetMap)
      setPlans(planMap)
      await fetchProjects()
    } catch { setError('Could not connect to backend.') }
    finally { setLoading(false) }
  }, [fetchProjects])

  const loadPublishJobs = useCallback(async () => {
    const slug = PROJECT_FILTERS[filter]
    const project = projects.find(p => p.slug === slug)
    const url = project ? `${API}/publish-jobs?project_id=${project.id}` : `${API}/publish-jobs`
    const res = await fetch(url)
    if (res.ok) setPublishedJobs(await res.json())
  }, [filter, projects])

  useEffect(() => { void fetchApprovals() }, [fetchApprovals])
  useEffect(() => { void loadPublishJobs() }, [loadPublishJobs])
  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadPublishJobs()
    }, 30000)
    return () => window.clearInterval(interval)
  }, [loadPublishJobs])

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(null), 3000)
    return () => window.clearTimeout(timeout)
  }, [toast])

  const decideApproval = useCallback(async (approvalId: string, decision: 'approved' | 'rejected', reason?: string | null) => {
    setDeciding(approvalId)
    const res = await fetch(`${API}/approvals/${approvalId}/decide`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, reason: reason || null }),
    })
    setDeciding(null); setSelected(null)
    await fetchApprovals()
    await loadPublishJobs()
    return res.ok
  }, [fetchApprovals, loadPublishJobs])

  const approve = async (approvalId: string) => {
    const ok = await decideApproval(approvalId, 'approved')
    if (ok) setToast({ msg: '✅ Approved — scheduled for publish', color: 'success' })
  }

  const reject = async (approvalId: string, reason: string) => {
    const ok = await decideApproval(approvalId, 'rejected', reason || null)
    if (ok) setToast({ msg: 'Feedback saved — the AI will avoid this pattern next time', color: 'success' })
  }

  const approveAll = async () => {
    if (pending.length <= 1) return
    setBulkProgress(`Approving 0/${pending.length}...`)
    for (let i = 0; i < pending.length; i += 1) {
      setBulkProgress(`Approving ${i + 1}/${pending.length}...`)
      await decideApproval(pending[i].id, 'approved')
    }
    setBulkProgress('')
    setToast({ msg: `All ${pending.length} assets approved and scheduled`, color: 'success' })
  }

  const pending = approvals.filter(a => a.decision == null)
  const hasPublished = publishedJobs.length > 0
  const activePublishedJobs = useMemo(() => {
    if (filter === 'All') return publishedJobs
    const slug = PROJECT_FILTERS[filter]
    const project = projects.find(p => p.slug === slug)
    if (!project) return publishedJobs
    return publishedJobs.filter(job => {
      const asset = assets[job.asset_id]
      return asset ? asset.project_id === project.id : true
    })
  }, [assets, filter, projects, publishedJobs])

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Page-level fullscreen — outside every overflow/scroll container */}
      {fullscreenUrl && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 9999, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setFullscreenUrl(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={resolveImgUrl(fullscreenUrl)} alt="Full size" style={{ maxWidth: '100vw', maxHeight: '100vh', objectFit: 'contain' }} />
          <button
            style={{ position: 'absolute', top: 16, right: 16, width: 48, height: 48, borderRadius: '50%', background: 'rgba(255,255,255,0.15)', color: '#fff', fontSize: 24, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={e => { e.stopPropagation(); setFullscreenUrl(null) }}
          >×</button>
        </div>
      )}

      {selected && (
        <DetailModal approval={selected.approval} asset={selected.asset}
          onFullscreen={setFullscreenUrl}
          deciding={deciding === selected.approval.id}
          onApprove={() => approve(selected.approval.id)}
          onReject={(reason) => reject(selected.approval.id, reason)}
          onClose={() => { setSelected(null); fetchApprovals() }} />
      )}

      <div className="pt-12 pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox size={22} className="text-[#C9A84C]" />
            <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Approval Inbox</h1>
            <span className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.2)] px-2.5 py-0.5 rounded-full">{pending.length}</span>
          </div>
          <button onClick={fetchApprovals} className="text-[rgba(248,246,241,0.4)] hover:text-[#C9A84C] p-2 min-h-[44px] min-w-[44px] flex items-center justify-center">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-5 pb-[7rem]">
        <div className="flex gap-2 overflow-x-auto pb-4 mb-5">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`shrink-0 font-['IBM_Plex_Sans'] text-sm px-4 py-2.5 rounded-full border transition-all min-h-[44px] ${filter === f ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]' : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)]'}`}>{f}</button>
          ))}
        </div>

        {!loading && !error && pending.length > 1 && (
          <AnimatedContent delay={40}>
            <button
              onClick={() => void approveAll()}
              disabled={!!bulkProgress || deciding !== null}
              className="w-full flex items-center justify-center gap-2 mb-4 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
            >
              {bulkProgress || `Approve All (${pending.length})`}
            </button>
          </AnimatedContent>
        )}

        {toast && (
          <AnimatedContent delay={0}>
            <Card className={`mb-4 ${toast.color === 'success' ? 'border-[rgba(16,185,129,0.25)]' : ''}`}>
              <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1]">{toast.msg}</p>
            </Card>
          </AnimatedContent>
        )}

        {error && <FetchError message={error} onRetry={fetchApprovals} />}
        {loading && !error && <Card><p className="font-['IBM_Plex_Sans'] text-center text-[rgba(248,246,241,0.4)] py-12 text-sm">Loading...</p></Card>}

        {!loading && !error && pending.length === 0 && !hasPublished && (
          <AnimatedContent delay={100}>
            <Card>
              <div className="flex flex-col items-center py-16 gap-4">
                <div className="w-16 h-16 rounded-2xl bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] flex items-center justify-center">
                  <Check size={32} className="text-[#10B981]" />
                </div>
                <h2 className="font-['IBM_Plex_Sans'] text-lg text-[#F8F6F1] font-semibold">All caught up</h2>
                <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] text-center max-w-xs">
                  No pending approvals. Run the pipeline on a project to generate content.
                </p>
                <Link href="/projects/therapia" className="mt-3 inline-flex items-center font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] rounded-xl px-4 py-2 min-h-[44px] hover:bg-[rgba(201,168,76,0.08)] transition-all">
                  Run pipeline on Therapia →
                </Link>
              </div>
            </Card>
          </AnimatedContent>
        )}

        {!loading && !error && pending.length > 0 && (
          <div className="space-y-3 pb-4">
            {pending.map((approval, i) => {
              const asset = approval.asset_id ? assets[approval.asset_id] : null
              const accent = asset?.channel === 'instagram'
                ? 'rgba(225,48,108,0.18)'
                : asset?.channel === 'linkedin'
                ? 'rgba(0,119,181,0.18)'
                : asset?.channel === 'x'
                ? 'rgba(29,161,242,0.18)'
                : asset?.channel === 'google_ads'
                ? 'rgba(66,133,244,0.18)'
                : 'rgba(201,168,76,0.14)'
              const openDetail = () => setSelected({ approval, asset, plan: approval.weekly_plan_id ? plans[approval.weekly_plan_id] ?? null : null })
              return (
                <AnimatedContent key={approval.id} delay={i * 60}>
                  <div className="rounded-[20px] p-[2px]" style={{ background: `linear-gradient(135deg, ${accent}, rgba(10,10,10,0.2) 65%, transparent)` }}>
                    <div className="rounded-[18px] bg-[#111827] p-4">
                      {/* Thumbnail + content row */}
                      <div className="flex gap-3 mb-4">
                        <button onClick={openDetail} className="shrink-0">
                          <ProjectImage
                            url={asset?.design_thumbnail_url ?? null}
                            alt=""
                            className="w-20 h-20 rounded-xl overflow-hidden border border-[rgba(201,168,76,0.1)]"
                          />
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.2)] px-2 py-0.5 rounded-full">
                              {asset ? CHANNEL_LABELS[asset.channel] || asset.channel : 'Plan'}
                            </span>
                            {!!asset?.qa_score && <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">QA {asset.qa_score}/100</span>}
                          </div>
                          {asset?.copy_en && <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] line-clamp-2 mb-1">{asset.copy_en}</p>}
                          {asset?.copy_ar && <p className="font-['Cairo'] text-xs text-[rgba(248,246,241,0.35)] line-clamp-1" dir="rtl">{asset.copy_ar}</p>}
                          {!asset && approval.weekly_plan_id && plans[approval.weekly_plan_id] && (
                            <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] line-clamp-2">{plans[approval.weekly_plan_id].objective}</p>
                          )}
                          {!asset && approval.weekly_plan_id && !plans[approval.weekly_plan_id] && (
                            <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)]">Weekly plan — tap View to see details</p>
                          )}
                        </div>
                      </div>
                      {/* Action buttons — full width, large touch targets */}
                      <div className="grid grid-cols-3 gap-2">
                        <button
                          onClick={openDetail}
                          className="flex items-center justify-center gap-1.5 font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.6)] border border-[rgba(255,255,255,0.1)] rounded-xl py-3 min-h-[52px] active:bg-[rgba(255,255,255,0.05)] transition-colors"
                        >
                          <Eye size={14} /> View
                        </button>
                        <button
                          onClick={() => approve(approval.id)}
                          disabled={deciding === approval.id}
                          className="flex items-center justify-center gap-1.5 font-['IBM_Plex_Sans'] text-sm font-bold text-[#10B981] bg-[rgba(16,185,129,0.12)] border border-[rgba(16,185,129,0.3)] rounded-xl py-3 min-h-[52px] active:bg-[rgba(16,185,129,0.25)] transition-colors disabled:opacity-40"
                        >
                          <ThumbsUp size={15} /> Approve
                        </button>
                        <button
                          onClick={openDetail}
                          disabled={deciding === approval.id}
                          className="flex items-center justify-center gap-1.5 font-['IBM_Plex_Sans'] text-sm font-bold text-[#EF4444] bg-[rgba(239,68,68,0.12)] border border-[rgba(239,68,68,0.3)] rounded-xl py-3 min-h-[52px] active:bg-[rgba(239,68,68,0.25)] transition-colors disabled:opacity-40"
                        >
                          <ThumbsDown size={15} /> Reject
                        </button>
                      </div>
                    </div>
                  </div>
                </AnimatedContent>
              )
            })}
          </div>
        )}

        {!loading && !error && activePublishedJobs.length > 0 && (
          <AnimatedContent delay={180}>
            <div className="mt-6 mb-4 flex items-center justify-between">
              <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">Published</h2>
              <span className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.45)]">{activePublishedJobs.length} jobs</span>
            </div>
            <div className="space-y-3 pb-4">
              {activePublishedJobs.map((job, i) => (
                <AnimatedContent key={job.id} delay={i * 50}>
                  <Card>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">{job.channel}</p>
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-1">
                          {job.status === 'published' ? 'Published' : 'Scheduled'} • {new Date(job.scheduled_at).toLocaleString()}
                        </p>
                      </div>
                      <Badge variant={job.status === 'published' ? 'success' : 'gold'}>{job.status}</Badge>
                    </div>
                    {job.platform_post_id && (
                      <p className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C] mt-3 break-all">{job.platform_post_id}</p>
                    )}
                    {job.error_message && (
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[#EF4444] mt-3">{job.error_message}</p>
                    )}
                  </Card>
                </AnimatedContent>
              ))}
            </div>
          </AnimatedContent>
        )}
      </div>
    </div>
  )
}
