'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'
import { ProjectImage } from '@/components/ui/ProjectImage'
import { Upload, Image, Type, Palette, FileText, Check, Loader2, Brain, Zap, Play, Sparkles } from 'lucide-react'

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

const TABS = ['Assets', 'Memory', 'Pipeline', 'Analytics']

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

  const [tab, setTab] = useState('Pipeline')
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
            <AnimatedContent delay={0}>
              <Card>
                <div className="flex items-center gap-2 mb-4">
                  <Brain size={16} className="text-[#C9A84C]" />
                  <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Brand Memory</h2>
                  {brand && <Badge variant={brand.is_provisional ? 'warning' : 'success'}>
                    {brand.is_provisional ? 'Provisional' : 'Approved'}
                  </Badge>}
                </div>
                {brand ? (
                  <div className="space-y-3">
                    <Row label="Visual Style" value={brand.visual_style as string} />
                    <Row label="Brand Voice" value={brand.brand_voice as string} />
                    <div>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-1">Do</p>
                      {((brand.dos as string[]) || []).map((d, i) => (
                        <p key={i} className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.7)] flex gap-2">
                          <span className="text-[#10B981]">✓</span>{d}
                        </p>
                      ))}
                    </div>
                    <div>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-1">Don&apos;t</p>
                      {((brand.donts as string[]) || []).map((d, i) => (
                        <p key={i} className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.7)] flex gap-2">
                          <span className="text-[#EF4444]">✗</span>{d}
                        </p>
                      ))}
                    </div>
                  </div>
                ) : <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.3)]">Loading...</p>}
              </Card>
            </AnimatedContent>

            <AnimatedContent delay={100}>
              <Card>
                <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-4">Project Memory</h2>
                {memory ? (
                  <div className="space-y-3">
                    <Row label="Positioning" value={memory.positioning as string} />
                    <Row label="Tone" value={memory.tone as string} />
                    <Row label="Languages" value={(memory.languages as string[])?.join(', ')} />
                    {!!memory.performance_learnings && (
                      <Row label="Learnings" value={String(memory.performance_learnings)} />
                    )}
                    <div>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-2">Funnel Goals</p>
                      <div className="overflow-x-auto">
                        {Object.entries((memory.funnel_goals as Record<string, unknown>) || {}).map(([stage, data]) => {
                          const d = data as Record<string, unknown>
                          return (
                            <div key={stage} className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:items-center py-1 border-b border-[rgba(255,255,255,0.04)] last:border-0">
                              <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] capitalize">{stage}</span>
                              <span className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C]">
                                {String(d.current ?? 0)} / {String(d.target ?? '?')} {String(d.metric ?? '')}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                ) : <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.3)]">Loading...</p>}
              </Card>
            </AnimatedContent>

            {/* Brand Brief — markdown text editor */}
            <AnimatedContent delay={160}>
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles size={16} className="text-[#C9A84C]" />
                    <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Brand Brief</h2>
                  </div>
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.3)]">Used in every design generation</p>
                </div>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-3">
                  Write your brand story, visual direction, tone, and key messaging in plain text or Markdown. Agents read this before generating any content.
                </p>
                <textarea
                  value={brief}
                  onChange={e => { setBrief(e.target.value); setBriefSaved(false) }}
                  rows={8}
                  placeholder={`# Brand Brief\n\n## What we do\nTherapia is a mental wellness platform...\n\n## Visual direction\nNavy blue (#001A4D) primary, electric blue (#4169E1) accent...\n\n## Tone\nWarm, professional, never clinical...`}
                  className="w-full bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] focus:border-[rgba(201,168,76,0.4)] rounded-xl px-4 py-3 font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.8)] resize-none outline-none transition-colors leading-relaxed"
                  dir="auto"
                />
                <div className="flex items-center justify-between mt-3">
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.25)]">{brief.length} chars</p>
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
                      } finally {
                        setBriefSaving(false)
                      }
                    }}
                    className="flex items-center gap-2 font-['IBM_Plex_Sans'] text-sm font-semibold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] px-4 py-2 rounded-xl min-h-[40px] disabled:opacity-40 transition-colors"
                  >
                    {briefSaving ? <Loader2 size={13} className="animate-spin" /> : briefSaved ? <Check size={13} /> : null}
                    {briefSaving ? 'Saving...' : briefSaved ? 'Saved ✓' : 'Save Brief'}
                  </button>
                </div>
              </Card>
            </AnimatedContent>
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

function Row({ label, value }: { label: string; value: string | undefined }) {
  if (!value) return null
  return (
    <div className="border-b border-[rgba(255,255,255,0.04)] pb-2 last:border-0">
      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)]">{label}</p>
      <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.8)] mt-0.5">{value}</p>
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
