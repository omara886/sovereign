'use client'
import { useState, useEffect, useCallback } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Check, Inbox, RefreshCw, ThumbsUp, ThumbsDown, X, ImageOff } from 'lucide-react'

const FILTERS = ['All', 'Therapia', 'Qawwi', 'ProductBench', 'SahmAlgo']
const CHANNEL_LABELS: Record<string, string> = {
  instagram: 'Instagram', linkedin: 'LinkedIn', x: 'X / Twitter', google_ads: 'Google Ads'
}
const API = '/api/proxy'

interface Approval { id: string; asset_id: string | null; weekly_plan_id: string | null; decision: string | null; created_at: string }
interface Asset { id: string; type: string; channel: string; language: string; copy_ar: string | null; copy_en: string | null; design_thumbnail_url: string | null; qa_score: number | null; status: string }

function AssetThumb({ url }: { url: string | null }) {
  const [broken, setBroken] = useState(false)
  if (!url || broken) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <ImageOff size={20} className="text-[rgba(248,246,241,0.15)]" />
      </div>
    )
  }
  // Proxy image through backend to avoid CORS / file:// issues
  const src = url.startsWith('file://') || url.includes('railway.app')
    ? `/api/img?url=${encodeURIComponent(url)}`
    : url
  return (
    <img src={src} alt="" className="w-full h-full object-cover"
      onError={() => setBroken(true)} />
  )
}

export default function InboxPage() {
  const [filter, setFilter] = useState('All')
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [assets, setAssets] = useState<Record<string, Asset>>({})
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState<string | null>(null)
  const [error, setError] = useState('')
  // Rejection reason state
  const [rejectTarget, setRejectTarget] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const fetchApprovals = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/approvals?status=pending`)
      if (!res.ok) throw new Error('API error')
      const data: Approval[] = await res.json()
      setApprovals(data)
      const assetMap: Record<string, Asset> = {}
      await Promise.all(
        data.filter(a => a.asset_id).map(async a => {
          const ar = await fetch(`${API}/assets/${a.asset_id}`)
          if (ar.ok) assetMap[a.asset_id!] = await ar.json()
        })
      )
      setAssets(assetMap)
    } catch {
      setError('Could not connect to backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchApprovals() }, [fetchApprovals])

  const decide = async (approvalId: string, decision: 'approved' | 'rejected', reason?: string) => {
    setDeciding(approvalId)
    try {
      await fetch(`${API}/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reason: reason || null }),
      })
      setApprovals(current => current.filter(a => a.id !== approvalId))
      await fetchApprovals()
    } finally {
      setDeciding(null)
      setRejectTarget(null)
      setRejectReason('')
    }
  }

  const pending = approvals.filter(a => a.decision == null)

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Rejection reason modal */}
      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/60 backdrop-blur-sm px-4 pb-4 md:pb-0">
          <div className="w-full max-w-md rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(239,68,68,0.2)] to-transparent border border-[rgba(239,68,68,0.2)]">
            <div className="rounded-[18px] bg-[#1E293B] p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-['IBM_Plex_Sans'] text-base font-semibold text-[#F8F6F1]">Why are you rejecting this?</h3>
                <button onClick={() => { setRejectTarget(null); setRejectReason('') }}
                  className="text-[rgba(248,246,241,0.4)] hover:text-[#F8F6F1] p-1">
                  <X size={18} />
                </button>
              </div>
              <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-3">
                Your reason teaches the AI what to avoid next time.
              </p>
              <textarea
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                placeholder="e.g. Wrong tone, too formal, not about our actual product..."
                rows={3}
                className="w-full bg-[#0A0A0A] border border-[rgba(255,255,255,0.1)] rounded-xl px-4 py-3 font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] outline-none focus:border-[#C9A84C] resize-none transition-colors"
              />
              <div className="flex gap-3 mt-4">
                <button onClick={() => { setRejectTarget(null); setRejectReason('') }}
                  className="flex-1 font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.5)] border border-[rgba(255,255,255,0.1)] rounded-xl py-3 hover:border-[rgba(255,255,255,0.2)] transition-colors min-h-[48px]">
                  Cancel
                </button>
                <button onClick={() => decide(rejectTarget, 'rejected', rejectReason)}
                  disabled={deciding === rejectTarget}
                  className="flex-1 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.3)] rounded-xl py-3 hover:bg-[rgba(239,68,68,0.2)] transition-colors disabled:opacity-40 min-h-[48px]">
                  Reject {rejectReason ? '& Save Feedback' : 'Anyway'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="pt-12 pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox size={22} className="text-[#C9A84C]" />
            <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Approval Inbox</h1>
            <span className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.2)] px-2.5 py-0.5 rounded-full">
              {pending.length}
            </span>
          </div>
          <button onClick={fetchApprovals} className="text-[rgba(248,246,241,0.4)] hover:text-[#C9A84C] transition-colors p-2">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-5">
        {/* Filters */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-5">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`shrink-0 font-['IBM_Plex_Sans'] text-sm px-4 py-2 rounded-full border transition-all duration-200 min-h-[40px] ${
                filter === f
                  ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]'
                  : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)]'
              }`}
            >{f}</button>
          ))}
        </div>

        {error && <Card><p className="font-['IBM_Plex_Sans'] text-sm text-[#EF4444] text-center py-4">{error}</p></Card>}
        {loading && !error && <Card><p className="font-['IBM_Plex_Sans'] text-center text-[rgba(248,246,241,0.4)] py-12 text-sm">Loading...</p></Card>}

        {!loading && !error && pending.length === 0 && (
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
              </div>
            </Card>
          </AnimatedContent>
        )}

        {!loading && !error && pending.length > 0 && (
          <div className="space-y-4 pb-4">
            {pending.map((approval, i) => {
              const asset = approval.asset_id ? assets[approval.asset_id] : null
              return (
                <AnimatedContent key={approval.id} delay={i * 70}>
                  <Card>
                    <div className="flex gap-3">
                      {/* Thumbnail */}
                      <div className="shrink-0 w-20 h-20 rounded-xl bg-[#0A0A0A] border border-[rgba(201,168,76,0.1)] overflow-hidden">
                        <AssetThumb url={asset?.design_thumbnail_url ?? null} />
                      </div>
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.2)] px-2 py-0.5 rounded-full">
                            {asset ? CHANNEL_LABELS[asset.channel] || asset.channel : 'Plan'}
                          </span>
                          {asset?.type && (
                            <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] bg-[rgba(255,255,255,0.04)] px-2 py-0.5 rounded-full border border-[rgba(255,255,255,0.06)]">
                              {asset.type}
                            </span>
                          )}
                          {!!asset?.qa_score && (
                            <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">QA {asset.qa_score}/100</span>
                          )}
                        </div>
                        {asset?.copy_en && (
                          <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] leading-relaxed line-clamp-2 mb-1">
                            {asset.copy_en.slice(0, 150)}
                          </p>
                        )}
                        {asset?.copy_ar && (
                          <p className="font-['Cairo'] text-xs text-[rgba(248,246,241,0.35)] line-clamp-1" dir="rtl">
                            {asset.copy_ar.slice(0, 80)}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 mt-4 pt-4 border-t border-[rgba(201,168,76,0.08)]">
                      <button onClick={() => decide(approval.id, 'approved')}
                        disabled={!!deciding}
                        className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#10B981] bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.25)] hover:bg-[rgba(16,185,129,0.2)] rounded-xl py-3 transition-all disabled:opacity-40 min-h-[48px]"
                      >
                        <ThumbsUp size={15} /> Approve
                      </button>
                      <button onClick={() => { setRejectTarget(approval.id); setRejectReason('') }}
                        disabled={!!deciding}
                        className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] hover:bg-[rgba(239,68,68,0.2)] rounded-xl py-3 transition-all disabled:opacity-40 min-h-[48px]"
                      >
                        <ThumbsDown size={15} /> Reject
                      </button>
                    </div>
                  </Card>
                </AnimatedContent>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
