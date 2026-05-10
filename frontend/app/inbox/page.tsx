'use client'
import { useState, useEffect, useCallback } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Check, Inbox, RefreshCw, ThumbsUp, ThumbsDown, X, ImageOff, Eye } from 'lucide-react'

const FILTERS = ['All', 'Therapia', 'Qawwi', 'ProductBench', 'SahmAlgo']
const CHANNEL_LABELS: Record<string, string> = {
  instagram: 'Instagram', linkedin: 'LinkedIn', x: 'X / Twitter', google_ads: 'Google Ads'
}
const API = '/api/proxy'

interface Approval { id: string; asset_id: string | null; weekly_plan_id: string | null; decision: string | null; created_at: string }
interface Asset { id: string; type: string; channel: string; language: string; copy_ar: string | null; copy_en: string | null; design_thumbnail_url: string | null; design_url: string | null; qa_score: number | null; status: string }

function proxyImg(url: string | null) {
  if (!url) return null
  if (url.startsWith('file://') || url.includes('railway.app') || url.includes('localhost'))
    return `/api/img?url=${encodeURIComponent(url)}`
  return url
}

function Thumb({ url, size = 'sm' }: { url: string | null; size?: 'sm' | 'lg' }) {
  const [broken, setBroken] = useState(false)
  const src = proxyImg(url)
  const cls = size === 'lg' ? 'w-full aspect-video rounded-xl' : 'w-20 h-20 rounded-xl shrink-0'
  if (!src || broken) return (
    <div className={`${cls} bg-[#0A0A0A] border border-[rgba(255,255,255,0.06)] flex items-center justify-center`}>
      <ImageOff size={size === 'lg' ? 32 : 20} className="text-[rgba(248,246,241,0.1)]" />
    </div>
  )
  return (
    <div className={`${cls} bg-[#0A0A0A] overflow-hidden border border-[rgba(201,168,76,0.1)]`}>
      <img src={src} alt="" className="w-full h-full object-cover" onError={() => setBroken(true)} />
    </div>
  )
}

function DetailModal({ approval, asset, onApprove, onClose, deciding }: {
  approval: Approval; asset: Asset | null; deciding: boolean;
  onApprove: () => void; onClose: () => void;
}) {
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const reject = async () => {
    setSubmitting(true)
    await fetch(`${API}/approvals/${approval.id}/decide`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: 'rejected', reason: rejectReason || null }),
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.15)] to-transparent border border-[rgba(201,168,76,0.15)]">
        <div className="rounded-[18px] bg-[#1E293B]">
          <div className="flex items-center justify-between p-5 border-b border-[rgba(255,255,255,0.06)]">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.2)] px-2 py-0.5 rounded-full">
                {asset ? CHANNEL_LABELS[asset.channel] || asset.channel : 'Plan'}
              </span>
              {asset?.type && <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)]">{asset.type}</span>}
              {!!asset?.qa_score && <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">QA {asset.qa_score}/100</span>}
            </div>
            <button onClick={onClose} className="text-[rgba(248,246,241,0.4)] hover:text-[#F8F6F1] p-2 min-h-[44px] min-w-[44px] flex items-center justify-center">
              <X size={18} />
            </button>
          </div>

          {(asset?.design_url || asset?.design_thumbnail_url) && (
            <div className="px-5 pt-5">
              <Thumb url={asset.design_url || asset.design_thumbnail_url} size="lg" />
            </div>
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

          <div className="flex gap-3 p-5 pt-3">
            {!showReject ? (
              <>
                <button onClick={onApprove} disabled={deciding || submitting}
                  className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#10B981] bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.25)] rounded-xl py-3 min-h-[48px] hover:bg-[rgba(16,185,129,0.2)] transition-all disabled:opacity-40">
                  <ThumbsUp size={15} /> Approve
                </button>
                <button onClick={() => setShowReject(true)}
                  className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-xl py-3 min-h-[48px] hover:bg-[rgba(239,68,68,0.2)] transition-all">
                  <ThumbsDown size={15} /> Reject
                </button>
              </>
            ) : (
              <>
                <button onClick={() => setShowReject(false)}
                  className="flex-1 font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.5)] border border-[rgba(255,255,255,0.1)] rounded-xl py-3 min-h-[48px]">
                  Back
                </button>
                <button onClick={reject} disabled={submitting}
                  className="flex-1 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-xl py-3 min-h-[48px] disabled:opacity-40 hover:bg-[rgba(239,68,68,0.2)] transition-all">
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
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<{ approval: Approval; asset: Asset | null } | null>(null)

  const fetchApprovals = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/approvals?status=pending`)
      if (!res.ok) throw new Error()
      const data: Approval[] = await res.json()
      setApprovals(data)
      const assetMap: Record<string, Asset> = {}
      await Promise.all(data.filter(a => a.asset_id).map(async a => {
        const ar = await fetch(`${API}/assets/${a.asset_id}`)
        if (ar.ok) assetMap[a.asset_id!] = await ar.json()
      }))
      setAssets(assetMap)
    } catch { setError('Could not connect to backend.') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchApprovals() }, [fetchApprovals])

  const approve = async (approvalId: string) => {
    setDeciding(approvalId)
    await fetch(`${API}/approvals/${approvalId}/decide`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision: 'approved' }),
    })
    setDeciding(null); setSelected(null)
    await fetchApprovals()
  }

  const pending = approvals.filter(a => a.decision == null)

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {selected && (
        <DetailModal approval={selected.approval} asset={selected.asset}
          deciding={deciding === selected.approval.id}
          onApprove={() => approve(selected.approval.id)}
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

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-5">
        <div className="flex gap-2 overflow-x-auto pb-4 mb-5">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`shrink-0 font-['IBM_Plex_Sans'] text-sm px-4 py-2 rounded-full border transition-all min-h-[40px] ${filter === f ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]' : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)]'}`}>{f}</button>
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
          <div className="space-y-3 pb-4">
            {pending.map((approval, i) => {
              const asset = approval.asset_id ? assets[approval.asset_id] : null
              return (
                <AnimatedContent key={approval.id} delay={i * 60}>
                  <Card>
                    <div className="flex gap-3">
                      <Thumb url={asset?.design_thumbnail_url ?? null} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] bg-[rgba(201,168,76,0.1)] border border-[rgba(201,168,76,0.2)] px-2 py-0.5 rounded-full">
                            {asset ? CHANNEL_LABELS[asset.channel] || asset.channel : 'Plan'}
                          </span>
                          {asset?.type && <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] bg-[rgba(255,255,255,0.04)] px-2 py-0.5 rounded-full border border-[rgba(255,255,255,0.06)]">{asset.type}</span>}
                          {!!asset?.qa_score && <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">QA {asset.qa_score}/100</span>}
                        </div>
                        {asset?.copy_en && <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] line-clamp-2 mb-1">{asset.copy_en}</p>}
                        {asset?.copy_ar && <p className="font-['Cairo'] text-xs text-[rgba(248,246,241,0.35)] line-clamp-1" dir="rtl">{asset.copy_ar}</p>}
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4 pt-4 border-t border-[rgba(201,168,76,0.08)]">
                      <button onClick={() => setSelected({ approval, asset })}
                        className="flex items-center justify-center gap-1.5 font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] border border-[rgba(255,255,255,0.08)] rounded-xl px-3 py-2.5 min-h-[44px] hover:text-[#F8F6F1] transition-all">
                        <Eye size={13} /> View
                      </button>
                      <button onClick={() => approve(approval.id)} disabled={deciding === approval.id}
                        className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#10B981] bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.25)] rounded-xl py-2.5 min-h-[44px] hover:bg-[rgba(16,185,129,0.2)] transition-all disabled:opacity-40">
                        <ThumbsUp size={14} /> Approve
                      </button>
                      <button onClick={() => setSelected({ approval, asset })}
                        className="flex-1 flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#EF4444] bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.25)] rounded-xl py-2.5 min-h-[44px] hover:bg-[rgba(239,68,68,0.2)] transition-all">
                        <ThumbsDown size={14} /> Reject
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
