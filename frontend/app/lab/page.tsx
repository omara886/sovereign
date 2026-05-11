'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import {
  Activity, AlertTriangle, CheckCircle, ChevronDown, ChevronUp,
  Clock, Flag, Loader2, Play, RefreshCw, ThumbsDown, ThumbsUp, Zap
} from 'lucide-react'

const API = '/api/proxy'

type PipelineStatus = 'idle' | 'running' | 'done' | 'error'
type AgentStatus = 'idle' | 'running' | 'done' | 'error'

interface AgentCard {
  key: string
  name: string
  icon: string
  status: AgentStatus
  last_output: string
  time_taken: string
  error: string | null
}

interface LogEntry {
  ts: number
  agent: string
  step: string
  sources: string[]
  decisions: string[]
}

interface PendingApproval {
  id: string
  asset_id: string | null
  copy_ar: string | null
  copy_en: string | null
  channel: string | null
  thumbnail_url: string | null
}

interface Health {
  fal_key_set: boolean
  r2_configured: boolean
  anthropic_key_set: boolean
  thmanyah_font_exists: boolean
  db_tables: boolean
}

interface LabStatus {
  pipeline_status: PipelineStatus
  last_run: string | null
  last_run_project: string
  agents: AgentCard[]
  recent_logs: LogEntry[]
  health: Health
  pending_approvals: PendingApproval[]
  jobs_today: number
}

const STATUS_COLORS: Record<AgentStatus, string> = {
  idle: 'border-[rgba(255,255,255,0.06)] text-[rgba(248,246,241,0.25)]',
  running: 'border-[rgba(201,168,76,0.5)] text-[#C9A84C]',
  done: 'border-[rgba(16,185,129,0.4)] text-[#10B981]',
  error: 'border-[rgba(239,68,68,0.4)] text-[#EF4444]',
}

const STATUS_BG: Record<AgentStatus, string> = {
  idle: 'bg-[rgba(255,255,255,0.02)]',
  running: 'bg-[rgba(201,168,76,0.06)]',
  done: 'bg-[rgba(16,185,129,0.05)]',
  error: 'bg-[rgba(239,68,68,0.06)]',
}

function formatTs(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatRelative(iso: string | null) {
  if (!iso) return 'Never'
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

function AgentStatusCard({ agent }: { agent: AgentCard }) {
  const isRunning = agent.status === 'running'
  return (
    <div className={`rounded-[18px] p-[2px] ${isRunning ? 'shadow-[0_0_18px_rgba(201,168,76,0.2)]' : ''}`}
      style={{
        background: isRunning
          ? 'linear-gradient(135deg, rgba(201,168,76,0.3), rgba(10,10,10,0.1))'
          : 'linear-gradient(135deg, rgba(255,255,255,0.05), transparent)'
      }}>
      <div className={`rounded-[16px] px-4 py-3.5 ${STATUS_BG[agent.status]} border ${STATUS_COLORS[agent.status]}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base leading-none">{agent.icon}</span>
          <span className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.7)] flex-1">{agent.name}</span>
          {isRunning && <Loader2 size={12} className="animate-spin text-[#C9A84C] shrink-0" />}
          {agent.status === 'done' && <CheckCircle size={12} className="text-[#10B981] shrink-0" />}
          {agent.status === 'error' && <AlertTriangle size={12} className="text-[#EF4444] shrink-0" />}
        </div>

        {agent.status !== 'idle' && agent.last_output && (
          <p className="font-['IBM_Plex_Sans'] text-[11px] text-[rgba(248,246,241,0.45)] leading-snug line-clamp-2">
            {agent.last_output}
          </p>
        )}

        {agent.status === 'idle' && (
          <p className="font-['IBM_Plex_Sans'] text-[11px] text-[rgba(248,246,241,0.2)]">Waiting...</p>
        )}

        {agent.time_taken && (
          <p className="font-['IBM_Plex_Mono'] text-[10px] text-[rgba(248,246,241,0.3)] mt-1.5">{agent.time_taken}</p>
        )}

        {agent.error && (
          <p className="font-['IBM_Plex_Sans'] text-[10px] text-[#EF4444] mt-1.5 break-all line-clamp-2">{agent.error}</p>
        )}

        {isRunning && (
          <div className="mt-2 h-0.5 rounded-full bg-[rgba(201,168,76,0.15)] overflow-hidden">
            <div className="h-full bg-[#C9A84C] rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
        )}
      </div>
    </div>
  )
}

function HealthCheck({ label, passing }: { label: string; passing: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${passing ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`} />
      <span className={`font-['IBM_Plex_Sans'] text-xs ${passing ? 'text-[rgba(248,246,241,0.5)]' : 'text-[#EF4444]'}`}>
        {label}
      </span>
    </div>
  )
}

function ApprovalCard({ approval, onDecision }: { approval: PendingApproval; onDecision: () => void }) {
  const [deciding, setDeciding] = useState<'approve' | 'reject' | null>(null)
  const [done, setDone] = useState(false)

  const decide = async (decision: 'approve' | 'reject') => {
    setDeciding(decision)
    try {
      await fetch(`${API}/approvals/${approval.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      })
      setDone(true)
      onDecision()
    } finally {
      setDeciding(null)
    }
  }

  if (done) return null

  return (
    <div className="rounded-[14px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), transparent)' }}>
      <div className="rounded-[12px] bg-[#1E293B] p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Badge variant="gold">{approval.channel ?? 'asset'}</Badge>
        </div>
        {approval.copy_ar && (
          <p dir="rtl" className="font-['Cairo'] text-sm text-[#F8F6F1] leading-relaxed">{approval.copy_ar}</p>
        )}
        {approval.copy_en && (
          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)]">{approval.copy_en}</p>
        )}
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => decide('approve')}
            disabled={!!deciding}
            className="flex-1 flex items-center justify-center gap-1 font-['IBM_Plex_Sans'] text-xs font-semibold text-[#0A0A0A] bg-[#C9A84C] rounded-xl py-2 min-h-[36px] disabled:opacity-40 transition-colors"
          >
            {deciding === 'approve' ? <Loader2 size={12} className="animate-spin" /> : <ThumbsUp size={12} />}
            Approve
          </button>
          <button
            onClick={() => decide('reject')}
            disabled={!!deciding}
            className="flex-1 flex items-center justify-center gap-1 font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)] border border-[rgba(255,255,255,0.08)] rounded-xl py-2 min-h-[36px] disabled:opacity-40"
          >
            {deciding === 'reject' ? <Loader2 size={12} className="animate-spin" /> : <ThumbsDown size={12} />}
            Reject
          </button>
        </div>
      </div>
    </div>
  )
}

function LogFeed({ logs }: { logs: LogEntry[] }) {
  const [showAll, setShowAll] = useState(false)
  const displayed = showAll ? logs : logs.slice(-8)

  if (logs.length === 0) return (
    <p className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.2)] text-center py-6">No activity yet</p>
  )

  return (
    <div className="space-y-1">
      {!showAll && logs.length > 8 && (
        <button onClick={() => setShowAll(true)} className="w-full font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] py-1 hover:text-[#C9A84C] transition-colors">
          Show {logs.length - 8} earlier entries ↑
        </button>
      )}
      {displayed.map((log, i) => (
        <div key={i} className="flex gap-2 items-start py-1 border-b border-[rgba(255,255,255,0.04)] last:border-0">
          <span className="font-['IBM_Plex_Mono'] text-[10px] text-[rgba(248,246,241,0.25)] shrink-0 mt-0.5">{formatTs(log.ts)}</span>
          {log.agent && (
            <span className="font-['IBM_Plex_Sans'] text-[10px] font-semibold text-[#C9A84C] bg-[rgba(201,168,76,0.1)] px-1.5 py-0.5 rounded shrink-0">{log.agent}</span>
          )}
          <span className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.6)] flex-1 leading-snug">{log.step}</span>
        </div>
      ))}
    </div>
  )
}

export default function LabPage() {
  const [status, setStatus] = useState<LabStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showOldJobs, setShowOldJobs] = useState(false)
  const [oldJobs, setOldJobs] = useState<unknown[]>([])
  const refreshRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/pipeline/lab/status`)
      if (r.ok) {
        setStatus(await r.json())
        setError('')
      } else {
        setError(`Backend ${r.status}`)
      }
    } catch {
      setError('Backend unreachable')
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-refresh: every 5s if running, every 30s if idle
  useEffect(() => {
    load()
    const interval = setInterval(() => {
      load()
    }, status?.pipeline_status === 'running' ? 5000 : 30000)
    refreshRef.current = interval
    return () => clearInterval(interval)
  }, [load, status?.pipeline_status])

  const loadOldJobs = useCallback(async () => {
    const r = await fetch(`${API}/pipeline/jobs`)
    if (r.ok) setOldJobs(await r.json())
    setShowOldJobs(true)
  }, [])

  const pipelineColor = {
    idle: 'text-[rgba(248,246,241,0.4)]',
    running: 'text-[#C9A84C]',
    done: 'text-[#10B981]',
    error: 'text-[#EF4444]',
  }[status?.pipeline_status ?? 'idle']

  const PipelineIcon = status?.pipeline_status === 'running' ? Activity :
    status?.pipeline_status === 'done' ? CheckCircle :
    status?.pipeline_status === 'error' ? AlertTriangle : Clock

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Header */}
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-5 px-4 md:px-6 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap size={20} className="text-[#C9A84C]" />
            <h1 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">Control Room</h1>
          </div>
          <div className="flex items-center gap-3">
            {status && (
              <div className={`flex items-center gap-1.5 font-['IBM_Plex_Sans'] text-xs ${pipelineColor}`}>
                <PipelineIcon size={13} className={status.pipeline_status === 'running' ? 'animate-pulse' : ''} />
                <span className="capitalize">{status.pipeline_status}</span>
                {status.last_run && (
                  <span className="text-[rgba(248,246,241,0.3)]">· {formatRelative(status.last_run)}</span>
                )}
              </div>
            )}
            <button onClick={load} className="text-[rgba(248,246,241,0.35)] hover:text-[#C9A84C] p-2 min-h-[44px] transition-colors">
              <RefreshCw size={15} />
            </button>
          </div>
        </div>
      </div>

      {loading && !status && (
        <div className="flex items-center justify-center py-24 gap-2 text-[rgba(248,246,241,0.3)]">
          <Loader2 size={16} className="animate-spin text-[#C9A84C]" />
          <span className="font-['IBM_Plex_Sans'] text-sm">Loading...</span>
        </div>
      )}

      {error && !status && (
        <div className="max-w-6xl mx-auto px-4 md:px-6 pt-8">
          <Card>
            <p className="font-['IBM_Plex_Sans'] text-sm text-[#EF4444] text-center py-6">{error}</p>
          </Card>
        </div>
      )}

      {status && (
        <div className="max-w-6xl mx-auto px-4 md:px-6 pt-5 pb-[7rem]">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-5">

            {/* LEFT: Agents + logs */}
            <div className="space-y-5">

              {/* Stats row */}
              <AnimatedContent delay={0}>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Runs today', value: String(status.jobs_today) },
                    { label: 'Pending review', value: String(status.pending_approvals.length) },
                    { label: 'Health', value: `${Object.values(status.health).filter(Boolean).length}/${Object.keys(status.health).length}` },
                  ].map((stat, i) => (
                    <div key={i} className="rounded-[18px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.12), transparent)' }}>
                      <div className="rounded-[16px] bg-[#1E293B] px-4 py-3 text-center">
                        <p className="font-['IBM_Plex_Mono'] text-xl font-bold text-[#C9A84C]">{stat.value}</p>
                        <p className="font-['IBM_Plex_Sans'] text-[11px] text-[rgba(248,246,241,0.4)] mt-0.5">{stat.label}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </AnimatedContent>

              {/* Agent cards grid */}
              <AnimatedContent delay={60}>
                <div className="rounded-[20px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), transparent)' }}>
                  <div className="rounded-[18px] bg-[#0A0A0A] p-4">
                    <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.35)] uppercase tracking-[0.18em] mb-3">Agent Pipeline</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {status.agents.map((agent, i) => (
                        <AnimatedContent key={agent.key} delay={i * 40}>
                          <AgentStatusCard agent={agent} />
                        </AnimatedContent>
                      ))}
                    </div>
                  </div>
                </div>
              </AnimatedContent>

              {/* Live log feed */}
              <AnimatedContent delay={120}>
                <div className="rounded-[20px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.06), transparent)' }}>
                  <div className="rounded-[18px] bg-[#0A0A0A] p-4">
                    <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.35)] uppercase tracking-[0.18em] mb-3">
                      Live Log
                      {status.last_run_project && (
                        <span className="text-[#C9A84C] normal-case ml-2">— {status.last_run_project}</span>
                      )}
                    </p>
                    <LogFeed logs={status.recent_logs} />
                  </div>
                </div>
              </AnimatedContent>

              {/* Past runs */}
              <AnimatedContent delay={160}>
                <button
                  onClick={showOldJobs ? () => setShowOldJobs(false) : loadOldJobs}
                  className="flex items-center gap-2 font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)] hover:text-[#C9A84C] transition-colors"
                >
                  {showOldJobs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showOldJobs ? 'Hide' : 'Show'} past pipeline runs
                </button>
                {showOldJobs && (oldJobs as {id: string; project_name: string; status: string; step: string; steps_count: number; started_at: number; ended_at: number | null}[]).map(j => (
                  <div key={j.id} className="border border-[rgba(255,255,255,0.06)] rounded-[14px] px-4 py-3 mt-2 flex items-center gap-3">
                    {j.status === 'done' ? <CheckCircle size={13} className="text-[#10B981] shrink-0" /> :
                     j.status === 'error' ? <AlertTriangle size={13} className="text-[#EF4444] shrink-0" /> :
                     <Loader2 size={13} className="animate-spin text-[#C9A84C] shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">{j.project_name || '—'}</p>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] truncate">{j.step}</p>
                    </div>
                    <span className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.3)] shrink-0">{j.steps_count} steps</span>
                  </div>
                ))}
              </AnimatedContent>
            </div>

            {/* RIGHT: Health + Approvals */}
            <div className="space-y-4">

              {/* Health checks */}
              <AnimatedContent delay={80}>
                <div className="rounded-[20px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), transparent)' }}>
                  <div className="rounded-[18px] bg-[#1E293B] p-4">
                    <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.35)] uppercase tracking-[0.18em] mb-3">System Health</p>
                    <div className="space-y-2">
                      <HealthCheck label="Database connected" passing={status.health.db_tables} />
                      <HealthCheck label="fal.ai API key" passing={status.health.fal_key_set} />
                      <HealthCheck label="Anthropic key" passing={status.health.anthropic_key_set} />
                      <HealthCheck label="R2 storage" passing={status.health.r2_configured} />
                      <HealthCheck label="Thmanyah font" passing={status.health.thmanyah_font_exists} />
                    </div>

                    {!status.health.fal_key_set && (
                      <div className="mt-3 pt-3 border-t border-[rgba(255,255,255,0.06)]">
                        <p className="font-['IBM_Plex_Sans'] text-[11px] text-[#EF4444]">
                          FAL_KEY missing → designs use fallback card. Add to Railway Variables.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </AnimatedContent>

              {/* Pending approvals */}
              <AnimatedContent delay={120}>
                <div className="rounded-[20px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), transparent)' }}>
                  <div className="rounded-[18px] bg-[#1E293B] p-4">
                    <div className="flex items-center justify-between mb-3">
                      <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.35)] uppercase tracking-[0.18em]">Pending Approval</p>
                      {status.pending_approvals.length > 0 && (
                        <Link href="/inbox" className="font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] hover:text-[#E8C97A] transition-colors">
                          View all →
                        </Link>
                      )}
                    </div>

                    {status.pending_approvals.length === 0 ? (
                      <div className="text-center py-6">
                        <CheckCircle size={20} className="text-[#10B981] mx-auto mb-2 opacity-60" />
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.35)]">Nothing pending</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {status.pending_approvals.slice(0, 3).map(a => (
                          <ApprovalCard key={a.id} approval={a} onDecision={load} />
                        ))}
                        {status.pending_approvals.length > 3 && (
                          <Link href="/inbox" className="block text-center font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] py-2 hover:text-[#C9A84C] transition-colors">
                            +{status.pending_approvals.length - 3} more in Inbox
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </AnimatedContent>

              {/* Quick run buttons */}
              <AnimatedContent delay={160}>
                <div className="rounded-[20px] p-[2px]" style={{ background: 'linear-gradient(135deg, rgba(201,168,76,0.1), transparent)' }}>
                  <div className="rounded-[18px] bg-[#1E293B] p-4">
                    <p className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.35)] uppercase tracking-[0.18em] mb-3">Quick Actions</p>
                    <Link
                      href="/projects"
                      className="flex items-center gap-2 w-full font-['IBM_Plex_Sans'] text-sm font-semibold text-[#0A0A0A] bg-[#C9A84C] hover:bg-[#E8C97A] px-4 py-3 rounded-xl min-h-[44px] transition-colors"
                    >
                      <Play size={14} /> Run Pipeline
                    </Link>
                    <Link
                      href="/inbox"
                      className="flex items-center gap-2 mt-2 w-full font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)] border border-[rgba(255,255,255,0.08)] px-4 py-3 rounded-xl min-h-[44px] transition-colors hover:border-[rgba(201,168,76,0.3)]"
                    >
                      <Flag size={14} /> Review Inbox
                    </Link>
                  </div>
                </div>
              </AnimatedContent>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
