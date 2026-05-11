'use client'
import { useState, useEffect, useCallback } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { RefreshCw, ChevronDown, ChevronUp, Flag, CheckCircle, Loader2, AlertTriangle, Clock } from 'lucide-react'

const API = '/api/proxy'

type JobStatus = 'running' | 'done' | 'error'
interface Job { id: string; project_name: string; mode: string; status: JobStatus; step: string; steps_count: number; started_at: number; ended_at: number | null; error: string | null }
interface StepEntry { ts: number; step: string; agent: string; data_sources: string[]; decisions: string[] }
interface Report { ts: number; step_name: string; issue: string; category: string }
interface JobDetail { id: string; steps_history: StepEntry[]; error: string | null; reports: Report[] }

const CATEGORIES = ['wrong-content', 'bad-image', 'wrong-arabic', 'agent-error', 'other']

function dur(start: number, end: number | null) {
  const s = Math.round((end ?? Date.now() / 1000) - start)
  return s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`
}

function StepRow({ step, index, jobId, onReport }: { step: StepEntry; index: number; jobId: string; onReport: () => void }) {
  const [open, setOpen] = useState(false)
  const [issue, setIssue] = useState('')
  const [cat, setCat] = useState('other')
  const [done, setDone] = useState(false)

  const submit = async () => {
    await fetch(`${API}/pipeline/jobs/${jobId}/report`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step_index: index, step_name: step.step, issue, category: cat }),
    })
    setDone(true); setOpen(false); onReport()
  }

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3 space-y-2 bg-[var(--color-background)]">
      <div className="flex items-start gap-3">
        <span className="font-['Geist_Mono'] text-[10px] text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] px-1.5 py-0.5 rounded-full mt-0.5 shrink-0">{index+1}</span>
        <div className="flex-1 min-w-0">
          {step.agent && <span className="font-['Geist'] text-[10px] font-semibold text-[var(--color-accent)] bg-[var(--color-accent-tint)] px-2 py-0.5 rounded-full mr-2">{step.agent}</span>}
          <p className="font-['Geist'] text-sm text-[var(--color-text-primary)] mt-1">{step.step}</p>
          {(step.data_sources.length > 0 || step.decisions.length > 0) && (
            <div className="flex flex-wrap gap-1 mt-2">
              {step.data_sources.map(s => <span key={s} className="font-['Geist_Mono'] text-[9px] text-[var(--color-text-muted)] border border-[var(--color-border)] px-1.5 py-0.5 rounded bg-[var(--color-surface)]">📂 {s}</span>)}
              {step.decisions.map(d => <span key={d} className="font-['Geist_Mono'] text-[9px] text-[var(--color-accent)] bg-[var(--color-accent-tint)] border border-[var(--color-accent-soft)] px-1.5 py-0.5 rounded">✓ {d}</span>)}
            </div>
          )}
        </div>
        {done
          ? <span className="font-['Geist'] text-xs text-[var(--color-success)] shrink-0">Reported</span>
          : <button onClick={() => setOpen(!open)} className="shrink-0 flex items-center gap-1 font-['Geist'] text-xs text-[var(--color-text-muted)] hover:text-[var(--color-error)] border border-[var(--color-border)] rounded-[var(--radius-sm)] px-2 py-1 transition-colors min-h-[32px]"><Flag size={10}/> Report</button>
        }
      </div>
      {open && (
        <div className="pt-2 border-t border-[var(--color-border-subtle)] space-y-2">
          <select value={cat} onChange={e => setCat(e.target.value)} className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-sm)] px-3 py-2 font-['Geist'] text-xs text-[var(--color-text-primary)] outline-none">
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <textarea value={issue} onChange={e => setIssue(e.target.value)} placeholder="What went wrong?" rows={2}
            className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-sm)] px-3 py-2 font-['Geist'] text-xs text-[var(--color-text-primary)] outline-none resize-none focus:border-[var(--color-accent)]"/>
          <div className="flex gap-2">
            <button onClick={() => setOpen(false)} className="flex-1 font-['Geist'] text-xs text-[var(--color-text-muted)] border border-[var(--color-border)] rounded-[var(--radius-sm)] py-1.5">Cancel</button>
            <button onClick={submit} disabled={!issue} className="flex-1 font-['Geist'] text-xs font-medium text-[var(--color-on-accent)] bg-[var(--color-accent)] rounded-[var(--radius-sm)] py-1.5 disabled:opacity-40">Submit</button>
          </div>
        </div>
      )}
    </div>
  )
}

function JobRow({ job }: { job: Job }) {
  const [open, setOpen] = useState(job.status === 'running')
  const [detail, setDetail] = useState<JobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [reports, setReports] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await fetch(`${API}/pipeline/jobs/${job.id}/detail`); if (r.ok) setDetail(await r.json()) }
    finally { setLoading(false) }
  }, [job.id])

  useEffect(() => { if (open && !detail) load() }, [open, detail, load])
  useEffect(() => {
    if (job.status !== 'running' || !open) return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [job.status, open, load])

  const Icon = job.status === 'done' ? CheckCircle : job.status === 'error' ? AlertTriangle : Loader2
  const iconColor = job.status === 'done' ? 'text-[var(--color-success)]' : job.status === 'error' ? 'text-[var(--color-error)]' : 'text-[var(--color-accent)]'

  return (
    <div className="border border-[var(--color-border)] rounded-[var(--radius-lg)] overflow-hidden">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-surface-hover)] transition-colors text-left">
        <Icon size={15} className={`${iconColor} ${job.status==='running'?'animate-spin':''} shrink-0`}/>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="font-['Geist'] text-sm font-semibold text-[var(--color-text-primary)]">{job.project_name||'—'}</span>
            <span className="font-['Geist'] text-xs text-[var(--color-text-muted)] bg-[var(--color-surface-hover)] px-2 py-0.5 rounded-full">{job.mode}</span>
            {reports > 0 && <span className="font-['Geist'] text-xs text-[var(--color-error)] bg-[rgba(239,68,68,0.1)] px-2 py-0.5 rounded-full">{reports} report{reports>1?'s':''}</span>}
          </div>
          <p className="font-['Geist'] text-xs text-[var(--color-text-muted)] truncate">{job.step}</p>
        </div>
        <div className="text-right shrink-0 mr-2">
          <p className="font-['Geist_Mono'] text-xs text-[var(--color-text-muted)]">{job.steps_count} steps</p>
          <p className="font-['Geist_Mono'] text-xs text-[var(--color-text-muted)]">{dur(job.started_at, job.ended_at)}</p>
        </div>
        {loading ? <Loader2 size={13} className="animate-spin text-[var(--color-text-muted)] shrink-0"/> : open ? <ChevronUp size={13} className="text-[var(--color-text-muted)] shrink-0"/> : <ChevronDown size={13} className="text-[var(--color-text-muted)] shrink-0"/>}
      </button>

      {open && detail && (
        <div className="border-t border-[var(--color-border)] bg-[var(--color-background-secondary)] p-4 space-y-2">
          {detail.error && (
            <div className="flex gap-2 p-3 bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[var(--radius-md)]">
              <AlertTriangle size={13} className="text-[var(--color-error)] mt-0.5 shrink-0"/>
              <p className="font-['Geist_Mono'] text-xs text-[var(--color-error)] break-all">{detail.error}</p>
            </div>
          )}
          {detail.steps_history.length === 0 && !detail.error && (
            <p className="font-['Geist'] text-xs text-[var(--color-text-muted)] text-center py-6">Waiting for steps...</p>
          )}
          {detail.steps_history.map((s, i) => (
            <StepRow key={i} step={s} index={i} jobId={job.id} onReport={() => setReports(r => r+1)}/>
          ))}
          {detail.reports.length > 0 && (
            <div className="pt-3 border-t border-[var(--color-border-subtle)]">
              <p className="font-['Geist'] text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Reports</p>
              {detail.reports.map((r, i) => (
                <div key={i} className="flex gap-2 p-2 bg-[rgba(239,68,68,0.05)] border border-[var(--color-border-subtle)] rounded-[var(--radius-sm)] mb-1">
                  <Flag size={10} className="text-[var(--color-error)] mt-0.5 shrink-0"/>
                  <div><span className="font-['Geist_Mono'] text-[9px] text-[var(--color-error)] mr-2">{r.category}</span><span className="font-['Geist'] text-xs text-[var(--color-text-secondary)]">{r.issue}</span></div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function LabPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try { const r = await fetch(`${API}/pipeline/jobs`); if (r.ok) setJobs(await r.json()); else setErr('Could not load') }
    catch { setErr('Backend unreachable') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-[var(--color-background)]">
      <div className="pt-12 pb-6 px-4 md:px-8 border-b border-[var(--color-border)]">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-['Fraunces'] text-3xl text-[var(--color-text-primary)]">Lab</h1>
            <p className="font-['Geist'] text-sm text-[var(--color-text-muted)] mt-1">Every pipeline run — agents, API calls, data sources. Report any step.</p>
          </div>
          <button onClick={load} className="text-[var(--color-text-muted)] hover:text-[var(--color-accent)] p-2 min-h-[44px] flex items-center justify-center transition-colors"><RefreshCw size={18}/></button>
        </div>
      </div>
      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8 space-y-3">
        {err && <Card><p className="font-['Geist'] text-sm text-[var(--color-error)] text-center py-4">{err}</p></Card>}
        {loading && <Card><p className="font-['Geist'] text-sm text-[var(--color-text-muted)] text-center py-10">Loading...</p></Card>}
        {!loading && jobs.length === 0 && (
          <AnimatedContent delay={100}><Card>
            <div className="flex flex-col items-center py-16 gap-3">
              <Clock size={28} className="text-[var(--color-text-muted)]"/>
              <p className="font-['Geist'] text-sm font-semibold text-[var(--color-text-primary)]">No runs yet</p>
              <p className="font-['Geist'] text-xs text-[var(--color-text-muted)] text-center max-w-xs">Run Full Pipeline on a project — every step appears here with agents, sources, and decisions.</p>
            </div>
          </Card></AnimatedContent>
        )}
        {jobs.map((j, i) => <AnimatedContent key={j.id} delay={i*40}><JobRow job={j}/></AnimatedContent>)}
      </div>
    </div>
  )
}
