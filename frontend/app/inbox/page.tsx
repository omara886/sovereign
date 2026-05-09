'use client'
import { useState, useEffect, useCallback } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Check, Inbox, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react'

const FILTER_PROJECTS = ['الكل', 'Therapia', 'Qawwi', 'ProductBench', 'Sahmalgo']
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Approval {
  id: string
  asset_id: string | null
  weekly_plan_id: string | null
  decision: string | null
  created_at: string
}

interface Asset {
  id: string
  type: string
  channel: string
  language: string
  copy_ar: string | null
  copy_en: string | null
  design_thumbnail_url: string | null
  qa_score: number | null
  status: string
}

export default function InboxPage() {
  const [activeProject, setActiveProject] = useState('الكل')
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [assets, setAssets] = useState<Record<string, Asset>>({})
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState<string | null>(null)

  const fetchApprovals = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/approvals?status=pending`)
      const data: Approval[] = await res.json()
      setApprovals(data)

      // Fetch asset details for each approval
      const assetMap: Record<string, Asset> = {}
      await Promise.all(
        data.filter(a => a.asset_id).map(async (a) => {
          const ar = await fetch(`${API}/api/assets/${a.asset_id}`)
          if (ar.ok) assetMap[a.asset_id!] = await ar.json()
        })
      )
      setAssets(assetMap)
    } catch {
      // backend not reachable locally — show connection error
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchApprovals() }, [fetchApprovals])

  const decide = async (approvalId: string, decision: 'approved' | 'rejected') => {
    setDeciding(approvalId)
    try {
      await fetch(`${API}/api/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      })
      await fetchApprovals()
    } finally {
      setDeciding(null)
    }
  }

  const CHANNEL_LABELS: Record<string, string> = {
    instagram: 'Instagram', linkedin: 'LinkedIn', x: 'X', google_ads: 'Google Ads'
  }

  const pending = approvals.filter(a => !a.decision)

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-32 md:pb-12">
      {/* Header */}
      <div className="pt-12 pb-6 px-6 md:px-8 border-b border-[rgba(201,168,76,0.1)]" dir="rtl">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <Inbox size={24} className="text-[#C9A84C]" />
              <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">صندوق الموافقة</h1>
              <span className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C] bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.2)] px-2.5 py-0.5 rounded-full">
                {pending.length}
              </span>
            </div>
            <p className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.4)]">
              وافق أو ارفض — كل قرارك يُحفظ ويُعلّم النظام
            </p>
          </div>
          <button onClick={fetchApprovals} className="text-[rgba(248,246,241,0.4)] hover:text-[#C9A84C] transition-colors">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 md:px-8 pt-6">
        {/* Project filter */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-6" dir="rtl">
          {FILTER_PROJECTS.map((p) => (
            <button key={p} onClick={() => setActiveProject(p)}
              className={`shrink-0 font-['Cairo'] text-sm px-4 py-1.5 rounded-full border transition-all duration-200 ${
                activeProject === p
                  ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]'
                  : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)] hover:text-[#F8F6F1]'
              }`}
            >{p}</button>
          ))}
        </div>

        {loading ? (
          <Card><p className="font-['Cairo'] text-center text-[rgba(248,246,241,0.4)] py-12">جاري التحميل...</p></Card>
        ) : pending.length === 0 ? (
          <AnimatedContent delay={100}>
            <Card>
              <div className="flex flex-col items-center py-16 gap-4" dir="rtl">
                <div className="w-16 h-16 rounded-2xl bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] flex items-center justify-center">
                  <Check size={32} className="text-[#10B981]" />
                </div>
                <h2 className="font-['Cairo'] text-xl text-[#F8F6F1] font-semibold">كل شي تمام</h2>
                <p className="font-['Cairo'] text-[rgba(248,246,241,0.4)] text-center max-w-xs">
                  ما في موافقات معلقة.
                </p>
              </div>
            </Card>
          </AnimatedContent>
        ) : (
          <div className="space-y-4" dir="rtl">
            {pending.map((approval, i) => {
              const asset = approval.asset_id ? assets[approval.asset_id] : null
              return (
                <AnimatedContent key={approval.id} delay={i * 80}>
                  <Card>
                    <div className="flex gap-4">
                      {/* Thumbnail */}
                      <div className="shrink-0 w-20 h-20 rounded-xl bg-[#0A0A0A] border border-[rgba(201,168,76,0.1)] overflow-hidden flex items-center justify-center">
                        {asset?.design_thumbnail_url ? (
                          <img src={asset.design_thumbnail_url} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <span className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.2)]">
                            {asset?.channel?.slice(0,2).toUpperCase() || 'AS'}
                          </span>
                        )}
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
                          {asset?.qa_score && (
                            <span className="font-['IBM_Plex_Mono'] text-xs text-[#10B981]">
                              QA {asset.qa_score}/100
                            </span>
                          )}
                        </div>

                        {asset?.copy_ar && (
                          <p className="font-['Cairo'] text-sm text-[#F8F6F1] leading-relaxed line-clamp-2 mb-1">
                            {asset.copy_ar.slice(0, 120)}...
                          </p>
                        )}
                        {asset?.copy_en && (
                          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] line-clamp-1">
                            {asset.copy_en.slice(0, 100)}...
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 mt-4 pt-4 border-t border-[rgba(201,168,76,0.08)]" dir="ltr">
                      <Button
                        variant="approve"
                        onClick={() => decide(approval.id, 'approved')}
                        disabled={deciding === approval.id}
                        className="flex-1"
                      >
                        <ThumbsUp size={15} />
                        وافق
                      </Button>
                      <Button
                        variant="reject"
                        onClick={() => decide(approval.id, 'rejected')}
                        disabled={deciding === approval.id}
                        className="flex-1"
                      >
                        <ThumbsDown size={15} />
                        ارفض
                      </Button>
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
