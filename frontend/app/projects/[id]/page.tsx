'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Upload, Image, Type, Palette, FileText, Check, Loader2, Brain, Zap, Play } from 'lucide-react'

const API = '/api/proxy'

const FILE_TYPES = [
  { key: 'logo', label: 'Logo', icon: Image, accept: 'image/png,image/jpeg,image/webp,image/svg+xml', hint: 'PNG, SVG, WebP' },
  { key: 'screenshot', label: 'App Screenshots', icon: FileText, accept: 'image/png,image/jpeg', hint: 'PNG, JPG' },
  { key: 'font', label: 'Arabic Font', icon: Type, accept: '.ttf,.otf,.woff,.woff2', hint: 'TTF, OTF, WOFF' },
  { key: 'color_palette', label: 'Brand Colors', icon: Palette, accept: 'image/png,image/jpeg,application/pdf', hint: 'Image or PDF' },
  { key: 'other', label: 'Other', icon: FileText, accept: '*/*', hint: 'Any file · Max 10MB' },
]

const TABS = ['Assets', 'Memory', 'Pipeline']

export default function ProjectPage() {
  const params = useParams()
  const slug = params.id as string
  const projectName = slug.charAt(0).toUpperCase() + slug.slice(1)

  const [tab, setTab] = useState('Assets')
  const [activeType, setActiveType] = useState('logo')
  const [uploads, setUploads] = useState<Array<{ type: string; url: string; name: string }>>([])
  const [memory, setMemory] = useState<Record<string, unknown> | null>(null)
  const [brand, setBrand] = useState<Record<string, unknown> | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadDone, setUploadDone] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [jobStatus, setJobStatus] = useState<Record<string, unknown> | null>(null)
  const [running, setRunning] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    try {
      const [uRes, mRes, bRes] = await Promise.all([
        fetch(`${API}/uploads/${slug}`),
        fetch(`${API}/projects/${slug}/memory`),
        fetch(`${API}/projects/${slug}/brand`),
      ])
      if (uRes.ok) { const d = await uRes.json(); setUploads(d.files || []) }
      if (mRes.ok) setMemory(await mRes.json())
      if (bRes.ok) setBrand(await bRes.json())
    } catch { /* silent */ }
  }, [slug])

  useEffect(() => { load() }, [load])

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
      setTimeout(() => setUploadDone(false), 3000)
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
                className={`shrink-0 font-['IBM_Plex_Sans'] text-sm px-4 py-2.5 border-b-2 transition-all duration-200 ${
                  tab === t
                    ? 'border-[#C9A84C] text-[#C9A84C]'
                    : 'border-transparent text-[rgba(248,246,241,0.4)] hover:text-[#F8F6F1]'
                }`}
              >{t}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8">

        {/* ── ASSETS TAB ── */}
        {tab === 'Assets' && (
          <div className="space-y-6">
            <AnimatedContent delay={0}>
              {/* Type selector */}
                <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4">
                  {FILE_TYPES.map(({ key, label, icon: Icon }) => (
                    <button key={key} onClick={() => setActiveType(key)}
                    className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-['IBM_Plex_Sans'] transition-all min-h-[40px] ${
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
                  <p className="font-['IBM_Plex_Sans'] text-sm text-[#EF4444] text-center pb-4">{uploadError}</p>
                )}
              </Card>
            </AnimatedContent>

            {/* Uploaded files */}
            {uploads.length > 0 && (
              <AnimatedContent delay={100}>
                <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.4)] uppercase tracking-wider mb-3">
                  Uploaded Assets ({uploads.length})
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {uploads.map((file, i) => (
                    <Card key={i}>
                      <div className="aspect-square rounded-xl bg-[#0A0A0A] overflow-hidden flex items-center justify-center mb-2">
                        {file.type !== 'font' ? (
                          <img src={file.url} alt={file.name}
                            className="w-full h-full object-contain p-2"
                            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                        ) : <Type size={28} className="text-[#C9A84C]" />}
                      </div>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.6)] truncate">{file.name}</p>
                      <Badge variant="gold" className="mt-1 text-[10px]">{file.type}</Badge>
                    </Card>
                  ))}
                </div>
              </AnimatedContent>
            )}

            {uploads.length === 0 && !uploading && (
              <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.2)] text-center py-4">
                No assets yet. Upload your logo first — the AI uses it in every generated design.
              </p>
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
                      {Object.entries((memory.funnel_goals as Record<string, unknown>) || {}).map(([stage, data]) => {
                        const d = data as Record<string, unknown>
                        return (
                          <div key={stage} className="flex justify-between items-center py-1 border-b border-[rgba(255,255,255,0.04)] last:border-0">
                            <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] capitalize">{stage}</span>
                            <span className="font-['IBM_Plex_Mono'] text-xs text-[#C9A84C]">
                              {String(d.current ?? 0)} / {String(d.target ?? '?')} {String(d.metric ?? '')}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.3)]">Loading...</p>}
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
                  <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1]">{String(jobStatus.step)}</p>
                </div>
              )}

              <Card>
                <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-1">Weekly Plan</h2>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-4">
                  Strategy Agent analyzes your memory + assets and creates this week&apos;s marketing plan.
                </p>
                <button onClick={() => runPipeline('plan')} disabled={running}
                  className="w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] bg-[rgba(201,168,76,0.08)] hover:bg-[rgba(201,168,76,0.15)] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
                >
                  {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                  Generate Weekly Plan
                </button>
              </Card>
            </AnimatedContent>

            <AnimatedContent delay={100}>
              <Card>
                <h2 className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-1">Full Pipeline</h2>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mb-4">
                  Plan + Copy + Design + QA → assets appear in Inbox for approval. Uses your uploaded logo, font, and screenshots.
                </p>
                <button onClick={() => runPipeline('run')} disabled={running}
                  className="w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] rounded-xl py-3 min-h-[48px] transition-all disabled:opacity-40"
                >
                  {running ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                  Run Full Pipeline (~3 min)
                </button>
              </Card>
            </AnimatedContent>

            <AnimatedContent delay={200}>
              <div className="rounded-xl bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] px-4 py-3">
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] leading-relaxed">
                  The AI reads your uploaded logo, font, screenshots, ICP, and brand voice before generating anything. Upload assets first for best results.
                </p>
              </div>
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
