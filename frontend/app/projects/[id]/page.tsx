'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'
import { ProjectImage } from '@/components/ui/ProjectImage'
import { Upload, Image, Type, Palette, FileText, Check, Loader2, Zap, Play, Sparkles } from 'lucide-react'

const API = '/api/proxy'

type PlanTactic = {
  id?: string
  channel?: string
  asset_type?: string
  funnel_stage?: string
  rationale?: string
  rationale_simple?: string
  budget_estimate_sar?: number | string
  budget_type?: string
  stop_loss_sar?: number | string | null
  expected_metric?: string
  expected_value?: string
}

type WeeklyPlan = {
  id: string
  week_start: string
  objective: string
  funnel_focus: string
  tactics: PlanTactic[]
  total_budget_estimate: number | string
  rationale: string
  risk_flags: string[]
  status: string
  approval_id?: string | null
}

const FILE_TYPES = [
  { key: 'logo', label: 'Logo', icon: Image, accept: 'image/png,image/jpeg,image/webp,image/svg+xml', hint: 'PNG, SVG, WebP' },
  { key: 'screenshot', label: 'App Screenshots', icon: FileText, accept: 'image/png,image/jpeg', hint: 'PNG, JPG' },
  { key: 'font', label: 'Arabic Font', icon: Type, accept: '.ttf,.otf,.woff,.woff2', hint: 'TTF, OTF, WOFF' },
  { key: 'color_palette', label: 'Brand Colors', icon: Palette, accept: 'image/png,image/jpeg,application/pdf', hint: 'Image or PDF' },
  { key: 'other', label: 'Other', icon: FileText, accept: '*/*', hint: 'Any file · Max 10MB' },
]

const TABS = ['Brand Guide', 'Pipeline', 'Assets', 'Memory', 'Analytics']

type AnalyticsAsset = {
  asset_id: string
  channel: string
  type: string
  published_at: string | null
  platform_post_id: string | null
  thumbnail_url: string | null
  metrics: {
    impressions: number
    clicks: number
    engagement_rate: number
  }
}

export default function ProjectPage() {
  const params = useParams()
  const slug = params.id as string
  const projectName = slug.charAt(0).toUpperCase() + slug.slice(1)

  const [tab, setTab] = useState('Brand Guide')
  const [activeType, setActiveType] = useState('logo')
  const [uploads, setUploads] = useState<Array<{ type: string; url: string; name: string }>>([])
  const [memory, setMemory] = useState<Record<string, unknown> | null>(null)
  const [brand, setBrand] = useState<Record<string, unknown> | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadDone, setUploadDone] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisDone, setAnalysisDone] = useState(false)
  const [jobStatus, setJobStatus] = useState<Record<string, unknown> | null>(null)
  const [running, setRunning] = useState(false)
  const [currentPlan, setCurrentPlan] = useState<WeeklyPlan | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [planError, setPlanError] = useState('')
  const [approvalBusy, setApprovalBusy] = useState(false)
  const [approvalMessage, setApprovalMessage] = useState('')
  const [analyticsAssets, setAnalyticsAssets] = useState<AnalyticsAsset[]>([])
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [brief, setBrief] = useState('')
  const [briefSaving, setBriefSaving] = useState(false)
  const [briefSaved, setBriefSaved] = useState(false)
  const [analyticsError, setAnalyticsError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const hasPlan = Boolean(currentPlan)
  const hasApprovedAssets = Boolean(
    (jobStatus?.status === 'done' && Number(jobStatus?.assets_passed_qa || 0) > 0) ||
    currentPlan?.status === 'approved' ||
    currentPlan?.status === 'executing' ||
    currentPlan?.status === 'done'
  )

  const load = useCallback(async () => {
    try {
      const [uRes, mRes, bRes] = await Promise.all([
        fetch(`${API}/uploads/${slug}`),
        fetch(`${API}/projects/${slug}/memory`),
        fetch(`${API}/projects/${slug}/brand`),
      ])
      if (uRes.ok) { const d = await uRes.json(); setUploads(d.files || []) }
      if (mRes.ok) {
        const mem = await mRes.json()
        setMemory(mem)
        if (mem.brand_brief) setBrief(mem.brand_brief)
      }
      if (bRes.ok) setBrand(await bRes.json())
    } catch { /* silent */ }
  }, [slug])

  useEffect(() => { load() }, [load])

  const loadCurrentPlan = useCallback(async () => {
    setPlanLoading(true)
    setPlanError('')
    try {
      const res = await fetch(`${API}/plans/current/${slug}`)
      if (res.status === 404) {
        setCurrentPlan(null)
        return
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      setCurrentPlan(await res.json())
    } catch (err: unknown) {
      setPlanError(err instanceof Error ? err.message : 'Could not load current plan')
      setCurrentPlan(null)
    } finally {
      setPlanLoading(false)
    }
  }, [slug])

  const loadAnalytics = useCallback(async () => {
    setAnalyticsLoading(true)
    setAnalyticsError('')
    try {
      const res = await fetch(`${API}/metrics/assets?project_slug=${slug}&limit=20`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setAnalyticsAssets(await res.json())
    } catch (err: unknown) {
      setAnalyticsAssets([])
      setAnalyticsError(err instanceof Error ? err.message : 'Could not load analytics')
    } finally {
      setAnalyticsLoading(false)
    }
  }, [slug])

  useEffect(() => {
    if (tab === 'Pipeline') {
      void loadCurrentPlan()
    }
  }, [tab, loadCurrentPlan])

  useEffect(() => {
    void loadCurrentPlan()
  }, [loadCurrentPlan])

  useEffect(() => {
    if (tab === 'Analytics') {
      void loadAnalytics()
    }
  }, [tab, loadAnalytics])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true); setUploadError(''); setUploadDone(false)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('file_type', activeType)
      const res = await fetch(`${API}/uploads/${slug}`, { method: 'POST', body: form })
      const text = await res.text()
      if (!res.ok) {
        let detail = text
        try { detail = JSON.parse(text).detail || text } catch { /* use raw */ }
        throw new Error(`${res.status}: ${detail}`)
      }
      setUploadDone(true)
      await load()
      setTimeout(() => setUploadDone(false), 4000)
      // analysis runs in background on server — reload memory after 8s to show updates
      setTimeout(async () => { await load() }, 8000)
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const runPipeline = async (mode: 'plan' | 'run') => {
    setRunning(true); setJobStatus(null)
    try {
      const res = await fetch(`${API}/pipeline/${mode}/${slug}`, { method: 'POST' })
      const data = await res.json()
      const interval = setInterval(async () => {
        const sr = await fetch(`${API}/pipeline/status/${data.job_id}`)
        const sd = await sr.json()
        setJobStatus(sd)
        if (sd.status === 'done' || sd.status === 'error') {
          clearInterval(interval); setRunning(false)
        }
      }, 2000)
    } catch { setRunning(false) }
  }

  const handleApprovePlan = async () => {
    if (!currentPlan || approvalBusy || running) return
    setApprovalBusy(true)
    setApprovalMessage('')
    try {
      const approvalRes = await fetch(`${API}/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weekly_plan_id: currentPlan.id }),
      })
      const text = await approvalRes.text()
      if (!approvalRes.ok) {
        let detail = text
        try { detail = JSON.parse(text).detail || text } catch { /* use raw */ }
        throw new Error(`${approvalRes.status}: ${detail}`)
      }
      const approval = JSON.parse(text) as { id: string }
      setCurrentPlan({ ...currentPlan, status: 'approved' })
      setApprovalMessage(`Approval submitted (${approval.id.slice(0, 8)}). Generating copy and designs...`)
      await runPipeline('run')
    } catch (err: unknown) {
      setApprovalMessage(err instanceof Error ? err.message : 'Could not approve plan')
    } finally {
      setApprovalBusy(false)
    }
  }

  const active = FILE_TYPES.find(f => f.key === activeType)!

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Header */}
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-0 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.3)] mb-1">Project</p>
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1] mb-4">{projectName}</h1>
          {/* Tabs */}
          <div className="flex gap-1 overflow-x-auto whitespace-nowrap pb-2 -mx-4 px-4 md:mx-0 md:px-0">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`shrink-0 font-['IBM_Plex_Sans'] text-xs sm:text-sm px-4 py-3 min-h-[44px] border-b-2 transition-all duration-200 ${
                  tab === t
                    ? 'border-[#C9A84C] text-[#C9A84C]'
                    : 'border-transparent text-[rgba(248,246,241,0.4)] hover:text-[#F8F6F1]'
                }`}
              >{t}</button>
            ))}
          </div>
          {(uploads.length === 0 || !currentPlan) && (
            <SetupProgress uploads={uploads.length} hasPlan={hasPlan} hasApprovedAssets={hasApprovedAssets} />
          )}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-[7rem]">

        {/* ── BRAND GUIDE TAB ── */}
        {tab === 'Brand Guide' && (
          <div className="space-y-4">
            <div className="bg-white border border-white/[0.08] rounded-xl p-5">
              <div className="flex items-center justify-between mb-1">
                <div>
                  <h2 className="text-sm font-semibold text-gray-900">Brand Guide</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Paste your full brand.md here — agents read this before every pipeline run.
                    Colors, tone, positioning, audience, dos/don&apos;ts, Arabic rules.
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${brief.length > 100 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-600 border border-amber-200'}`}>
                  {brief.length > 100 ? '✓ Active' : 'Empty — agents using defaults'}
                </span>
              </div>

              {brief.length === 0 && (
                <div className="mt-3 mb-3 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2.5 text-xs text-indigo-700">
                  No brand guide yet. Paste your brand.md or write it here. The more context you give, the better every generated asset will match your brand.
                </div>
              )}

              <textarea
                value={brief}
                onChange={e => { setBrief(e.target.value); setBriefSaved(false) }}
                rows={24}
                placeholder={`# ${slug.charAt(0).toUpperCase() + slug.slice(1)} Brand Guide\n\n## Colors\nprimary: #001A4D\naccent: #4169E1\n\n## Typography\nArabic: Thmanyah Sans Black (headlines)\nEnglish: Inter\n\n## Tone\nGulf Saudi dialect, warm, direct...\n\n## Target Audience\n...\n\n## Positioning\n...\n\n## Arabic Rules\nGulf dialect only. No فصحى...\n\n## Do\n- ...\n\n## Don't\n- ...`}
                className="w-full mt-3 bg-gray-50 border border-white/[0.08] focus:border-indigo-400 rounded-lg px-4 py-3 font-mono text-xs text-gray-800 resize-none outline-none transition-colors leading-relaxed placeholder:text-gray-400"
                dir="auto"
              />

              <div className="flex items-center justify-between mt-3">
                <p className="text-xs text-gray-400 font-mono">{brief.length.toLocaleString()} chars</p>
                <div className="flex items-center gap-2">
                  {briefSaved && (
                    <span className="text-xs text-emerald-600">Saved — agents will use this on next run</span>
                  )}
                  <button
                    disabled={briefSaving}
                    onClick={async () => {
                      setBriefSaving(true)
                      try {
                        const r = await fetch(`${API}/projects/${slug}/memory`, {
                          method: 'PATCH',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ brand_brief: brief }),
                        })
                        if (r.ok) setBriefSaved(true)
                      } finally { setBriefSaving(false) }
                    }}
                    className="flex items-center gap-1.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 rounded-lg min-h-[40px] disabled:opacity-40 transition-colors"
                  >
                    {briefSaving ? <Loader2 size={13} className="animate-spin" /> : briefSaved ? <Check size={13} /> : null}
                    {briefSaving ? 'Saving...' : briefSaved ? 'Saved ✓' : 'Save Brand Guide'}
                  </button>
                </div>
              </div>
            </div>

            {/* What agents do with it */}
            <div className="bg-gray-50 border border-white/[0.08] rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-600 mb-2">How agents use your brand guide</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ['Strategy Agent', 'Campaign goals, audience, funnel direction'],
                  ['Copy Agent', 'Tone, dialect, vocabulary, CTAs, forbidden words'],
                  ['Design Agent', 'Colors, style, visual direction, safe zones'],
                  ['QA Agent', 'Brand compliance, tone check, Arabic rules'],
                ].map(([agent, desc]) => (
                  <div key={agent} className="bg-white rounded-lg px-3 py-2 border border-white/[0.06]">
                    <p className="text-xs font-semibold text-gray-700">{agent}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5">{desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── ASSETS TAB ── */}
        {tab === 'Assets' && (
          <div className="space-y-6">
            <AnimatedContent delay={0}>
              {/* Type selector */}
              <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4">
                  {FILE_TYPES.map(({ key, label, icon: Icon }) => (
                    <button key={key} onClick={() => setActiveType(key)}
                    className={`shrink-0 flex items-center gap-1.5 px-3 py-3 rounded-xl border text-xs font-['IBM_Plex_Sans'] transition-all min-h-[44px] ${
                      activeType === key
                        ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]'
                        : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.4)]'
                    }`}
                  ><Icon size={12} /> {label}</button>
                ))}
              </div>

              {/* Drop zone */}
              <Card>
                <input ref={fileRef} type="file" accept={active.accept}
                  onChange={handleUpload} className="hidden" id="fu" />
                <label htmlFor="fu" className="flex flex-col items-center gap-3 py-10 cursor-pointer group">
                  <div className={`w-16 h-16 rounded-2xl border-2 border-dashed flex items-center justify-center transition-all ${
                    uploading ? 'border-[#C9A84C] bg-[rgba(201,168,76,0.08)]' :
                    uploadDone ? 'border-[#10B981] bg-[rgba(16,185,129,0.08)]' :
                    'border-[rgba(201,168,76,0.25)] group-hover:border-[#C9A84C]'
                  }`}>
                    {uploading ? <Loader2 size={24} className="text-[#C9A84C] animate-spin" /> :
                     uploadDone ? <Check size={24} className="text-[#10B981]" /> :
                     <Upload size={24} className="text-[rgba(201,168,76,0.4)] group-hover:text-[#C9A84C]" />}
                  </div>
                  <div className="text-center">
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">
                      {uploading ? `Uploading ${active.label}...` :
                       uploadDone ? 'Uploaded — AI will use this in designs' :
                       `Tap to upload ${active.label}`}
                    </p>
                    <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] mt-1">
                      {active.hint}
                    </p>
                  </div>
                </label>
                {uploadError && (
                  <div className="pb-4">
                    <FetchError message={uploadError} onRetry={load} />
                  </div>
                )}
              </Card>
            </AnimatedContent>

            {/* Uploaded files */}
            {uploads.length > 0 && (
              <AnimatedContent delay={100}>
                <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.4)] uppercase tracking-wider mb-3">
                  Uploaded Assets ({uploads.length})
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {uploads.map((file, i) => (
                    <Card key={i}>
                      {file.type === 'font' ? (
                        <div className="aspect-square rounded-xl bg-[#0A0A0A] flex items-center justify-center">
                          <Type size={28} className="text-[#C9A84C]" />
                        </div>
                      ) : (
                        <ProjectImage
                          url={file.url}
                          alt={file.name}
                          className="aspect-square rounded-xl overflow-hidden flex items-center justify-center border border-[rgba(255,255,255,0.05)]"
                        />
                      )}
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.6)] truncate mt-2">{file.name}</p>
                      <Badge variant="gold" className="mt-1 text-[10px]">{file.type}</Badge>
                    </Card>
                  ))}
                </div>
              </AnimatedContent>
            )}

            {uploads.length === 0 && !uploading && (
              <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.2)] text-center py-4">
                No assets yet. Upload your logo first — the AI uses it in every design.
              </p>
            )}

            {/* Re-analyze button */}
            {uploads.length > 0 && (
              <AnimatedContent delay={300}>
                <button
                  onClick={async () => {
                    setAnalyzing(true); setAnalysisDone(false)
                    await fetch(`${API}/uploads/${slug}/analyze-now`, { method: 'POST' })
                    setTimeout(async () => { await load(); setAnalyzing(false); setAnalysisDone(true) }, 10000)
                    setTimeout(() => setAnalysisDone(false), 15000)
                  }}
                  disabled={analyzing}
                  className="w-full flex items-center justify-center gap-2 mt-4 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-dashed border-[rgba(201,168,76,0.3)] rounded-xl py-3 hover:bg-[rgba(201,168,76,0.05)] transition-all disabled:opacity-40 min-h-[48px]"
                >
                  {analyzing ? <Loader2 size={15} className="animate-spin" /> :
                   analysisDone ? <Check size={15} /> : <Sparkles size={15} />}
                  {analyzing ? 'AI is reading your assets...' :
                   analysisDone ? 'Memory updated from assets' :
                   'Re-analyze assets & update brand guide'}
                </button>
              </AnimatedContent>
            )}
          </div>
        )}

        {/* ── MEMORY TAB ── */}
        {tab === 'Memory' && (
          <div className="space-y-4">

            {/* Brand Brief (editable — agents read this on every run) */}
            <AnimatedContent delay={0}>
              <div className="bg-white border border-white/[0.08] rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles size={15} className="text-indigo-500" />
                    <h2 className="text-sm font-semibold text-gray-900">Brand Brief</h2>
                    <span className="text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100">Active — read on every pipeline run</span>
                  </div>
                </div>
                <textarea
                  value={brief}
                  onChange={e => { setBrief(e.target.value); setBriefSaved(false) }}
                  rows={7}
                  placeholder={`## What we do\nTherapia is a mental wellness platform...\n\n## Visual direction\nNavy blue (#001A4D) primary, electric blue (#4169E1) accent...\n\n## Tone\nWarm, professional, never clinical...\n\n## Target audience\nSaudi professionals 25-45, urban, health-conscious...`}
                  className="w-full bg-gray-50 border border-white/[0.08] focus:border-indigo-400 rounded-lg px-3 py-2.5 font-mono text-xs text-gray-800 resize-none outline-none transition-colors leading-relaxed placeholder:text-gray-400"
                  dir="auto"
                />
                <div className="flex items-center justify-between mt-2.5">
                  <p className="text-xs text-gray-400">{brief.length} chars</p>
                  <button
                    disabled={briefSaving}
                    onClick={async () => {
                      setBriefSaving(true)
                      try {
                        const r = await fetch(`${API}/projects/${slug}/memory`, {
                          method: 'PATCH',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ brand_brief: brief }),
                        })
                        if (r.ok) setBriefSaved(true)
                      } finally { setBriefSaving(false) }
                    }}
                    className="flex items-center gap-1.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg min-h-[36px] disabled:opacity-40 transition-colors"
                  >
                    {briefSaving ? <Loader2 size={13} className="animate-spin" /> : briefSaved ? <Check size={13} /> : null}
                    {briefSaving ? 'Saving...' : briefSaved ? 'Saved' : 'Save Brief'}
                  </button>
                </div>
              </div>
            </AnimatedContent>

            {/* Funnel Goals — with progress */}
            {memory && (memory.funnel_goals as Record<string, unknown>) && Object.keys(memory.funnel_goals as Record<string,unknown>).length > 0 && (
              <AnimatedContent delay={60}>
                <div className="bg-white border border-white/[0.08] rounded-xl p-5">
                  <h2 className="text-sm font-semibold text-gray-900 mb-3">Funnel Goals</h2>
                  <div className="space-y-3">
                    {Object.entries((memory.funnel_goals as Record<string, unknown>) || {}).map(([stage, data]) => {
                      const d = data as Record<string, unknown>
                      const current = Number(d.current ?? 0)
                      const target = Number(d.target ?? 0)
                      const progress = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0
                      return (
                        <div key={stage}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-gray-700 capitalize">{stage}</span>
                            <span className="text-xs font-mono text-gray-500">
                              {current} / {target || '?'} {String(d.metric ?? '')}
                            </span>
                          </div>
                          {target > 0 && (
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${progress}%`, background: progress >= 80 ? '#10B981' : progress >= 50 ? '#4F46E5' : '#F59E0B' }} />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </AnimatedContent>
            )}

            {/* ICP + Positioning + Tone — key strategy inputs */}
            {memory && (
              <AnimatedContent delay={100}>
                <div className="bg-white border border-white/[0.08] rounded-xl p-5 space-y-4">
                  <h2 className="text-sm font-semibold text-gray-900">Strategy Context</h2>
                  {!!(memory.positioning as string) && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Positioning</p>
                      <p className="text-sm text-gray-700">{memory.positioning as string}</p>
                    </div>
                  )}
                  {!!(memory.tone as string) && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Tone</p>
                      <p className="text-sm text-gray-700">{memory.tone as string}</p>
                    </div>
                  )}
                  {!!(memory.icp) && Object.keys(memory.icp as Record<string,unknown>).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Target Audience (ICP)</p>
                      <div className="space-y-1">
                        {Object.entries(memory.icp as Record<string,unknown>).slice(0,4).map(([k, v]) => (
                          <div key={k} className="flex gap-2 text-xs">
                            <span className="text-gray-400 capitalize w-20 shrink-0">{k}:</span>
                            <span className="text-gray-700">{Array.isArray(v) ? (v as string[]).slice(0,3).join(', ') : String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {!!(memory.constraints) && !!(memory.constraints as Record<string,unknown>).excluded_topics && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Never mention</p>
                      <div className="flex flex-wrap gap-1.5">
                        {((memory.constraints as Record<string,unknown>).excluded_topics as string[] ?? []).map((t: string, i: number) => (
                          <span key={i} className="text-xs bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-full">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </AnimatedContent>
            )}

            {/* Brand Memory — colors, voice, dos/don'ts */}
            {brand && (
              <AnimatedContent delay={140}>
                <div className="bg-white border border-white/[0.08] rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-gray-900">Brand Identity</h2>
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${brand.is_provisional ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                      {brand.is_provisional ? 'Provisional' : 'Approved'}
                    </span>
                  </div>
                  {(brand.color_palette as Record<string,string>) && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Colors</p>
                      <div className="flex gap-2 flex-wrap">
                        {Object.entries(brand.color_palette as Record<string,string>).map(([k, v]) => (
                          <div key={k} className="flex items-center gap-1.5 bg-gray-50 rounded px-2 py-1 border border-white/[0.06]">
                            <div className="w-3 h-3 rounded-full border border-white/[0.08]" style={{ background: v }} />
                            <span className="text-xs text-gray-600 capitalize">{k}</span>
                            <span className="text-xs font-mono text-gray-400">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {!!(brand.visual_style) && <div><p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Visual Style</p><p className="text-sm text-gray-700">{brand.visual_style as string}</p></div>}
                  {((brand.dos as string[]) || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Content Rules — DO</p>
                      {(brand.dos as string[]).slice(0,5).map((d, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-gray-700 py-0.5">
                          <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>{d}
                        </div>
                      ))}
                    </div>
                  )}
                  {((brand.donts as string[]) || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Content Rules — DON&apos;T</p>
                      {(brand.donts as string[]).slice(0,5).map((d, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-gray-700 py-0.5">
                          <span className="text-red-500 shrink-0 mt-0.5">✗</span>{d}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </AnimatedContent>
            )}

            {/* Approved / Rejected examples */}
            {memory && ((memory.approved_examples as unknown[]) || []).length > 0 && (
              <AnimatedContent delay={180}>
                <div className="bg-white border border-white/[0.08] rounded-xl p-5">
                  <h2 className="text-sm font-semibold text-gray-900 mb-3">Learning Examples</h2>
                  <div className="space-y-2">
                    {(memory.approved_examples as Array<Record<string,unknown>>).slice(0,3).map((ex, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs bg-emerald-50 rounded px-2.5 py-2 border border-emerald-100">
                        <span className="text-emerald-600 shrink-0 mt-0.5 font-bold">✓</span>
                        <span className="text-emerald-800">{String(ex.note || ex.copy_ar || ex.copy_en || JSON.stringify(ex)).slice(0,120)}</span>
                      </div>
                    ))}
                    {(memory.rejected_examples as Array<Record<string,unknown>> ?? []).slice(0,3).map((ex, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs bg-red-50 rounded px-2.5 py-2 border border-red-100">
                        <span className="text-red-600 shrink-0 mt-0.5 font-bold">✗</span>
                        <span className="text-red-800">{String((ex as Record<string,unknown>).what_to_avoid || (ex as Record<string,unknown>).note || '').slice(0,120)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </AnimatedContent>
            )}
          </div>
        )}

        {/* ── PIPELINE TAB ── */}
        {tab === 'Pipeline' && (
          <div className="space-y-4">
            <AnimatedContent delay={0}>
              {jobStatus && (
                <div className={`rounded-xl px-5 py-4 border flex items-center gap-3 mb-4 ${
                  jobStatus.status === 'error' ? 'bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.2)]' :
                  jobStatus.status === 'done' ? 'bg-[rgba(16,185,129,0.08)] border-[rgba(16,185,129,0.2)]' :
                  'bg-[rgba(201,168,76,0.08)] border-[rgba(201,168,76,0.2)]'
                }`}>
                  {running && <Loader2 size={16} className="text-[#C9A84C] animate-spin shrink-0" />}
                  {jobStatus.status === 'done' && <Check size={16} className="text-[#10B981] shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1]">{String(jobStatus.step)}</p>
                    {jobStatus.status === 'done' && typeof jobStatus.assets_passed_qa === 'number' && (
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-1">
                        {jobStatus.assets_passed_qa} assets ready for review
                      </p>
                    )}
                  </div>
                  {jobStatus.status === 'done' && typeof jobStatus.assets_passed_qa === 'number' && jobStatus.assets_passed_qa > 0 && (
                    <a
                      href="/inbox"
                      className="shrink-0 font-['IBM_Plex_Sans'] text-xs bg-[#C9A84C] text-[#0A0A0A] px-3 py-2 rounded-xl font-bold min-h-[40px] flex items-center"
                    >
                      Go to Inbox →
                    </a>
                  )}
                </div>
              )}

              <Card>
                <div className="flex items-start justify-between gap-3 mb-1">
                  <div>
                    <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Weekly Plan</h2>
                    <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                      Strategy Agent analyzes your memory + assets and creates this week&apos;s marketing plan.
                    </p>
                  </div>
                  {currentPlan && (
                    <Badge variant={currentPlan.status === 'approved' ? 'success' : 'gold'}>
                      {currentPlan.status.replace(/_/g, ' ')}
                    </Badge>
                  )}
                </div>

                <div className="flex flex-col gap-2 mt-4">
                  <button onClick={() => runPipeline('plan')} disabled={running}
                    className="w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] bg-[rgba(201,168,76,0.08)] hover:bg-[rgba(201,168,76,0.15)] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
                  >
                    {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                    Generate Weekly Plan
                  </button>
                  <button
                    onClick={() => void handleApprovePlan()}
                    disabled={!currentPlan || approvalBusy || running}
                    className="w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
                  >
                    {(approvalBusy || running) ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                    {approvalBusy ? 'Submitting approval...' : running ? 'Generating copy and designs...' : 'Approve Plan'}
                  </button>
                </div>

                <div className="mt-5">
                  {approvalMessage && (
                    <div className="rounded-xl border border-[rgba(201,168,76,0.18)] bg-[rgba(201,168,76,0.06)] px-4 py-3 mb-3">
                      <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1]">{approvalMessage}</p>
                    </div>
                  )}
                  {planLoading && (
                    <div className="flex items-center gap-2 text-sm text-[rgba(248,246,241,0.45)] font-['IBM_Plex_Sans']">
                      <Loader2 size={15} className="animate-spin text-[#C9A84C]" />
                      Loading current weekly plan...
                    </div>
                  )}
                  {planError && <FetchError message={planError} onRetry={loadCurrentPlan} />}
                  {!planLoading && !planError && !currentPlan && (
                    <div className="rounded-xl border border-dashed border-[rgba(201,168,76,0.18)] bg-[rgba(201,168,76,0.04)] px-4 py-4">
                      <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">No weekly plan yet</p>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-1">
                        Generate one to see the objective, tactics, and budget inline here.
                      </p>
                    </div>
                  )}
                  {currentPlan && (
                    <div className="space-y-4">
                      <Card>
                        <div className="flex flex-wrap items-center gap-2 mb-3">
                          <Badge variant="gold">{currentPlan.funnel_focus}</Badge>
                          <Badge variant="channel">{currentPlan.week_start}</Badge>
                          <Badge variant="default">{currentPlan.tactics.length} tactics</Badge>
                        </div>
                        <p className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1] leading-tight">
                          {currentPlan.objective}
                        </p>
                        <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.65)] mt-3 leading-relaxed">
                          {currentPlan.rationale}
                        </p>
                        <div className="mt-4 grid grid-cols-2 gap-3">
                          <Card>
                            <p className="font-['IBM_Plex_Sans'] text-[11px] uppercase tracking-[0.18em] text-[rgba(248,246,241,0.35)]">Budget</p>
                            <p className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C] mt-1">
                              SAR {Number(currentPlan.total_budget_estimate || 0).toLocaleString('en-US')}
                            </p>
                          </Card>
                          <Card>
                            <p className="font-['IBM_Plex_Sans'] text-[11px] uppercase tracking-[0.18em] text-[rgba(248,246,241,0.35)]">Status</p>
                            <p className="font-['IBM_Plex_Mono'] text-sm text-[#F8F6F1] mt-1">{currentPlan.status}</p>
                          </Card>
                        </div>
                      </Card>

                      <div className="space-y-3">
                        {currentPlan.tactics.map((tactic, index) => (
                          <Card key={tactic.id ?? `${tactic.channel}-${index}`}>
                            <div className="flex flex-wrap items-center gap-2 mb-3">
                              <Badge variant="channel">{tactic.channel || 'channel'}</Badge>
                              <Badge variant="default">{tactic.asset_type || 'asset'}</Badge>
                              {tactic.funnel_stage && <Badge variant="gold">{tactic.funnel_stage}</Badge>}
                              {tactic.budget_type && <Badge variant={tactic.budget_type === 'paid' ? 'warning' : 'success'}>{tactic.budget_type}</Badge>}
                            </div>
                            <div className="flex items-start justify-between gap-4">
                              <div className="min-w-0">
                                <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">
                                  {tactic.rationale_simple || tactic.rationale || 'Tactic details'}
                                </p>
                                {tactic.rationale && tactic.rationale_simple && tactic.rationale !== tactic.rationale_simple && (
                                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] mt-2 leading-relaxed">
                                    {tactic.rationale}
                                  </p>
                                )}
                              </div>
                              <div className="text-right shrink-0">
                                <p className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.45)]">Budget</p>
                                <p className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C]">
                                  SAR {Number(tactic.budget_estimate_sar || 0).toLocaleString('en-US')}
                                </p>
                              </div>
                            </div>
                            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                              {tactic.expected_metric && (
                                <Card>
                                  <p className="font-['IBM_Plex_Sans'] text-[11px] uppercase tracking-[0.16em] text-[rgba(248,246,241,0.35)]">Expected metric</p>
                                  <p className="font-['IBM_Plex_Sans'] text-xs text-[#F8F6F1] mt-1">{tactic.expected_metric}</p>
                                </Card>
                              )}
                              {tactic.expected_value && (
                                <Card>
                                  <p className="font-['IBM_Plex_Sans'] text-[11px] uppercase tracking-[0.16em] text-[rgba(248,246,241,0.35)]">Expected value</p>
                                  <p className="font-['IBM_Plex_Sans'] text-xs text-[#F8F6F1] mt-1">{tactic.expected_value}</p>
                                </Card>
                              )}
                            </div>
                            {tactic.stop_loss_sar !== null && tactic.stop_loss_sar !== undefined && (
                              <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-3">
                                Stop loss: SAR {Number(tactic.stop_loss_sar).toLocaleString('en-US')}
                              </p>
                            )}
                          </Card>
                        ))}
                      </div>

                      {currentPlan.risk_flags?.length > 0 && (
                        <Card>
                          <p className="font-['IBM_Plex_Sans'] text-sm font-medium text-[#F8F6F1] mb-2">Risk flags</p>
                          <div className="flex flex-wrap gap-2">
                            {currentPlan.risk_flags.map((flag, index) => (
                              <Badge key={`${flag}-${index}`} variant="warning">{flag}</Badge>
                            ))}
                          </div>
                        </Card>
                      )}
                    </div>
                  )}
                </div>
              </Card>
            </AnimatedContent>

            <AnimatedContent delay={100}>
              <Card>
                <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-1">Full Pipeline</h2>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-4">
                  Plan + Copy + Design + QA → assets appear in Inbox for approval. Uses your uploaded logo, font, and screenshots.
                </p>
                <button onClick={() => runPipeline('run')} disabled={running || uploads.length === 0}
                  title={uploads.length === 0 ? 'Upload a logo first so the AI can match your brand' : undefined}
                  className="w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
                >
                  {running ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                  Run Full Pipeline (~3 min)
                </button>
              </Card>
            </AnimatedContent>

            <AnimatedContent delay={200}>
              <Card>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] leading-relaxed">
                  The AI reads your uploaded logo, font, screenshots, ICP, and brand voice before generating anything. Upload assets first for best results.
                </p>
              </Card>
            </AnimatedContent>
          </div>
        )}

        {/* ── ANALYTICS TAB ── */}
        {tab === 'Analytics' && (
          <div className="space-y-4">
            <AnimatedContent delay={0}>
              <Card>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Project Analytics</h2>
                    <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                      Published assets and their latest performance snapshots.
                    </p>
                  </div>
                  <Badge variant="gold">Live</Badge>
                </div>

                {analyticsLoading && (
                  <div className="flex items-center gap-2 text-sm text-[rgba(248,246,241,0.45)] font-['IBM_Plex_Sans'] py-4">
                    <Loader2 size={15} className="animate-spin text-[#C9A84C]" />
                    Loading analytics...
                  </div>
                )}

                {analyticsError && <FetchError message={analyticsError} onRetry={loadAnalytics} />}

                {!analyticsLoading && !analyticsError && analyticsAssets.length === 0 && (
                  <div className="rounded-xl border border-dashed border-[rgba(201,168,76,0.18)] bg-[rgba(201,168,76,0.04)] px-4 py-4">
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">
                      Analytics update every Sunday 6PM. Approve content in Inbox to start publishing.
                    </p>
                    <a
                      href="/inbox"
                      className="inline-flex mt-3 items-center font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] rounded-xl px-4 py-2 min-h-[44px] hover:bg-[rgba(201,168,76,0.08)] transition-all"
                    >
                      Go to Inbox →
                    </a>
                  </div>
                )}

                {analyticsAssets.length > 0 && (
                  <div className="space-y-4">
                    {(() => {
                      const top = [...analyticsAssets].sort((a, b) => {
                        const aScore = (a.metrics.engagement_rate || 0) * 1000 + (a.metrics.impressions || 0)
                        const bScore = (b.metrics.engagement_rate || 0) * 1000 + (b.metrics.impressions || 0)
                        return bScore - aScore
                      })[0]
                      return (
                        <Card>
                          <p className="font-['IBM_Plex_Sans'] text-xs uppercase tracking-[0.18em] text-[rgba(248,246,241,0.35)] mb-2">Top Performer</p>
                          <div className="flex items-start gap-3">
                            <div className="w-20 shrink-0">
                              <ProjectImage
                                url={top.thumbnail_url || ''}
                                alt={`${top.channel} top asset`}
                                className="w-full aspect-square rounded-xl overflow-hidden border border-[rgba(201,168,76,0.1)]"
                              />
                            </div>
                            <div className="min-w-0">
                              <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">{top.channel} · {top.type}</p>
                              <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] mt-1">
                                Engagement {top.metrics.engagement_rate} · Impressions {top.metrics.impressions}
                              </p>
                              {top.published_at && (
                                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                                  Published {new Date(top.published_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          </div>
                        </Card>
                      )
                    })()}

                    <div className="space-y-3">
                      {analyticsAssets.map(asset => (
                        <Card key={asset.asset_id}>
                          <div className="flex items-start gap-3">
                            <div className="w-20 shrink-0">
                              <ProjectImage
                                url={asset.thumbnail_url || ''}
                                alt={`${asset.channel} asset`}
                                className="w-full aspect-square rounded-xl overflow-hidden border border-[rgba(201,168,76,0.1)]"
                              />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2 mb-2">
                                <Badge variant="channel">{asset.channel}</Badge>
                                <Badge variant="default">{asset.type}</Badge>
                              </div>
                              <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)]">
                                {asset.published_at ? `Published ${new Date(asset.published_at).toLocaleString()}` : 'Published asset'}
                              </p>
                              <div className="mt-3 grid grid-cols-3 gap-2">
                                <MetricPill label="Impr." value={asset.metrics.impressions} />
                                <MetricPill label="Clicks" value={asset.metrics.clicks} />
                                <MetricPill label="Eng." value={`${asset.metrics.engagement_rate}%`} />
                              </div>
                              {asset.platform_post_id && (
                                <p className="font-['IBM_Plex_Mono'] text-[10px] text-[rgba(248,246,241,0.35)] mt-3 break-all">
                                  {asset.platform_post_id}
                                </p>
                              )}
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            </AnimatedContent>
          </div>
        )}
      </div>
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function Row({ label, value }: { label: string; value: string | undefined }) {
  if (!value) return null
  return (
    <div className="border-b border-white/[0.06] pb-2 last:border-0">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm text-gray-800 mt-0.5">{value}</p>
    </div>
  )
}

function SetupProgress({
  uploads,
  hasPlan,
  hasApprovedAssets,
}: {
  uploads: number
  hasPlan: boolean
  hasApprovedAssets: boolean
}) {
  const steps = [
    { label: 'Upload logo', done: uploads > 0 },
    { label: 'Generate plan', done: hasPlan },
    { label: 'Approve & publish', done: hasApprovedAssets },
  ]
  const allDone = steps.every(step => step.done)
  if (allDone) return null

  return (
    <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-xl bg-[rgba(201,168,76,0.06)] border border-[rgba(201,168,76,0.15)] overflow-x-auto">
      {steps.map((step, i) => (
        <div key={step.label} className="flex items-center gap-2 shrink-0">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
            step.done ? 'bg-[#10B981] text-white' : 'bg-[rgba(201,168,76,0.2)] text-[#C9A84C]'
          }`}>
            {step.done ? '✓' : i + 1}
          </div>
          <span className={`font-['IBM_Plex_Sans'] text-xs ${step.done ? 'text-[rgba(248,246,241,0.35)] line-through' : 'text-[rgba(248,246,241,0.7)]'}`}>
            {step.label}
          </span>
          {i < steps.length - 1 && <div className="w-4 h-px bg-[rgba(255,255,255,0.1)]" />}
        </div>
      ))}
    </div>
  )
}

function MetricPill({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-[rgba(255,255,255,0.03)] px-3 py-2">
      <p className="font-['IBM_Plex_Sans'] text-[10px] uppercase tracking-[0.14em] text-[rgba(248,246,241,0.35)]">{label}</p>
      <p className="font-['IBM_Plex_Mono'] text-xs text-[#F8F6F1] mt-1">{value}</p>
    </div>
  )
}
