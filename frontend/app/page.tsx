'use client'
import { useState, useEffect, useCallback } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import CountUp from '@/components/react-bits/CountUp'
import SpotlightCard from '@/components/react-bits/SpotlightCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'
import { ProjectImage } from '@/components/ui/ProjectImage'
import Link from 'next/link'
import { CheckCircle, Clock, LayoutDashboard, Loader2, Play, TrendingUp, Zap } from 'lucide-react'

const API = '/api/proxy'

type MetricsSummary = {
  published_assets: number
  pending_approvals: number
  total_assets_generated: number
}
type JobStatus = {
  status: string
  step: string
  agent?: string
  data_sources?: string[]
  decisions?: string[]
  assets_passed_qa?: number
  objective?: string
}
type ProjectSummary = {
  id: string
  slug: string
  name: string
  primary_goal: string
  status: string
}
type ProjectStatus = {
  project_id: string
  slug: string
  name: string
  has_logo: boolean
  has_memory?: boolean
  has_plan: boolean
  plan_status: string | null
  plan_id: string | null
  pending_approvals: number
  published_assets: number
  next_action: string
}
type WeeklySummaryItem = {
  name: string
  slug: string
  learnings: string
  top_asset_url: string | null
}

const JOB_KEY = 'sovereign_active_job'

// Human-readable labels for internal enums
const GOAL_LABELS: Record<string, string> = {
  app_downloads_and_health_assessments_completed: 'App downloads + health assessments',
  leads_and_demo_requests: 'Leads & demo requests',
  waitlist_and_paying_customers: 'Waitlist & paying customers',
  followers_and_signups: 'Followers & signups',
}


const PLAN_STATUS_LABELS: Record<string, string> = {
  pending_approval: 'Awaiting plan approval',
  approved: 'Plan approved',
  executing: 'Generating content',
  done: 'Complete',
}

function splitLearnings(text: string) {
  return text
    .replace(/\r/g, '')
    .split(/\n|•|;|\.\s+/)
    .map(part => part.trim().replace(/^[-*]\s*/, ''))
    .filter(Boolean)
    .slice(0, 3)
}

function CommandBar({
  pendingApprovals,
  totalGenerated,
  loading,
  pipelineRunning,
}: {
  pendingApprovals: number
  totalGenerated: number
  loading: boolean
  pipelineRunning: boolean
}) {
  if (loading) return null

  if (pipelineRunning) {
    return (
      <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-lg bg-indigo-50 border border-indigo-200">
        <Loader2 size={15} className="text-indigo-600 animate-spin shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-indigo-900">Pipeline is running</p>
          <p className="text-xs text-indigo-600 mt-0.5">Generating content — check the Lab for live progress</p>
        </div>
        <Link href="/lab" className="shrink-0 text-xs font-semibold text-indigo-700 border border-indigo-300 px-3 py-2 rounded-lg hover:bg-indigo-100 transition-colors">
          View Live →
        </Link>
      </div>
    )
  }

  if (pendingApprovals > 0) {
    return (
      <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-lg bg-amber-50 border border-amber-200">
        <div className="w-7 h-7 rounded-full bg-amber-500 text-white text-xs font-bold flex items-center justify-center shrink-0">
          {pendingApprovals}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-amber-900">
            {pendingApprovals} item{pendingApprovals > 1 ? 's' : ''} waiting for your approval
          </p>
          <p className="text-xs text-amber-700 mt-0.5">Review each creative, check the safety checklist, then approve to publish</p>
        </div>
        <Link href="/inbox" className="shrink-0 text-xs font-semibold text-white bg-amber-500 hover:bg-amber-600 px-3 py-2 rounded-lg transition-colors min-h-[36px] flex items-center">
          Review Now →
        </Link>
      </div>
    )
  }

  if (totalGenerated === 0) {
    return (
      <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-lg bg-indigo-50 border border-indigo-200">
        <div className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center shrink-0">1</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-indigo-900">Set up Therapia to get started</p>
          <p className="text-xs text-indigo-600 mt-0.5">Write brand brief → run pipeline → approve content → publishes automatically</p>
        </div>
        <Link href="/projects/therapia" className="shrink-0 text-xs font-semibold text-indigo-700 border border-indigo-300 px-3 py-2 rounded-lg hover:bg-indigo-100 transition-colors">
          Set Up →
        </Link>
      </div>
    )
  }

  return (
    <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-lg bg-emerald-50 border border-emerald-200">
      <CheckCircle size={16} className="text-emerald-500 shrink-0" />
      <p className="text-sm text-emerald-800">All clear — no actions needed right now</p>
      <Link href="/pipeline" className="ml-auto shrink-0 text-xs text-emerald-700 border border-emerald-300 px-3 py-2 rounded-lg hover:bg-emerald-100 transition-colors">
        View Pipeline →
      </Link>
    </div>
  )
}

export default function DashboardPage() {
  const [activeJob, setActiveJob] = useState<{ jobId: string; project: string; mode: string } | null>(null)
  const [jobResult, setJobResult] = useState<JobStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(true)
  const [metricsError, setMetricsError] = useState('')
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [projectStatuses, setProjectStatuses] = useState<Record<string, ProjectStatus>>({})
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummaryItem[]>([])
  const [weeklySummaryLoading, setWeeklySummaryLoading] = useState(true)
  const [weeklySummaryError, setWeeklySummaryError] = useState('')

  const loadMetrics = useCallback(async () => {
    setMetricsError('')
    try {
      const res = await fetch(`${API}/metrics/summary`)
      if (res.ok) {
        setMetrics(await res.json())
      } else {
        throw new Error(`HTTP ${res.status}`)
      }
    } catch {
      setMetricsError('Could not load dashboard metrics')
    } finally {
      setMetricsLoading(false)
    }
  }, [])

  const loadWeeklySummary = useCallback(async () => {
    setWeeklySummaryError('')
    try {
      const res = await fetch(`${API}/metrics/weekly-summary`)
      if (res.ok) {
        const data = await res.json()
        setWeeklySummary(data.projects || [])
      } else {
        throw new Error(`HTTP ${res.status}`)
      }
    } catch {
      setWeeklySummaryError('Could not load weekly insights')
    } finally {
      setWeeklySummaryLoading(false)
    }
  }, [])

  const loadProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API}/projects`)
      if (!res.ok) return
      const data: Array<{ id: string; slug: string; name: string; primary_goal: string; status: string }> = await res.json()
      setProjects(data)
      const statuses = await Promise.all(data.map(async project => {
        const statusRes = await fetch(`${API}/projects/${project.slug}/status`)
        const statusData = statusRes.ok ? await statusRes.json() : null
        return [project.slug, statusData] as const
      }))
      setProjectStatuses(statuses.reduce<Record<string, ProjectStatus>>((acc, [slug, statusData]) => {
        if (!statusData) return acc
        acc[slug] = statusData
        return acc
      }, {}))
    } catch {
      // keep the previous project snapshot on transient failures
    } finally {
      setProjectsLoading(false)
    }
  }, [])

  // Restore in-progress job on mount (survives page navigation)
  useEffect(() => {
    try {
      const saved = localStorage.getItem(JOB_KEY)
      if (saved) {
        const job = JSON.parse(saved)
        setActiveJob(job)
        pollStatus(job.jobId)
      }
    } catch { /* ignore */ }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void loadMetrics()
    void loadWeeklySummary()
    void loadProjects()
    const interval = window.setInterval(() => {
      void loadMetrics()
      void loadProjects()
    }, 300000) // 5 minutes — metrics don't change often
    return () => window.clearInterval(interval)
  }, [loadMetrics, loadProjects, loadWeeklySummary])

  const triggerPipeline = async (slug: string, mode: 'plan' | 'run') => {
    setJobResult(null)
    setActiveJob({ jobId: '', project: slug, mode })
    try {
      const res = await fetch(`${API}/pipeline/${mode}/${slug}`, { method: 'POST' })
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      const job = { jobId: data.job_id, project: slug, mode }
      setActiveJob(job)
      localStorage.setItem(JOB_KEY, JSON.stringify(job))
      pollStatus(data.job_id)
    } catch (e) {
      setJobResult({ status: 'error', step: `Could not start pipeline: ${e}` })
      setActiveJob(null)
    }
  }

  const pollStatus = (jobId: string) => {
    setPolling(true)
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/pipeline/status/${jobId}`)
        if (!res.ok) { clearInterval(interval); setPolling(false); return }
        const data: JobStatus = await res.json()
        setJobResult(data)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(interval)
          setPolling(false)
          setActiveJob(null)
          localStorage.removeItem(JOB_KEY)
        }
      } catch {
        clearInterval(interval)
        setPolling(false)
      }
    }, 5000) // 5s — pipeline takes 2-3 min total, no need to check every 3s
  }

  // Show status bar as soon as button is clicked (activeJob set), not just when polling starts
  const isRunning = polling || (activeJob !== null && !jobResult)
  const totalGenerated = metrics?.total_assets_generated ?? 0
  const pendingApprovals = metrics?.pending_approvals ?? 0
  const isNewUser = !metricsLoading && totalGenerated === 0

  return (
    <div className="min-h-screen bg-[#0D1117]">
      {/* Page header — clean, no aurora on light theme */}
      <div className="bg-white border-b border-white/[0.08] pt-[calc(3rem+env(safe-area-inset-top))] pb-5 px-6">
        <div className="max-w-5xl mx-auto">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Sovereign</p>
          <h1 className="text-2xl font-bold text-gray-900">Command Center</h1>
          <p className="text-sm text-gray-500 mt-0.5">Autonomous marketing OS for Therapia, Qawwi, ProductBench, SahmAlgo</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 pb-[7rem] pt-5">
        {metricsError ? (
          <FetchError message={metricsError} onRetry={loadMetrics} />
        ) : null}

        {/* What needs Omar — command bar */}
        <CommandBar
          pendingApprovals={pendingApprovals}
          totalGenerated={totalGenerated}
          loading={metricsLoading}
          pipelineRunning={isRunning}
        />

        {!isNewUser && (
          <AnimatedContent delay={100}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
              {[
                { icon: Clock, label: 'Pending Approvals', value: pendingApprovals, accent: pendingApprovals > 0 ? '#C9A84C' : 'rgba(201,168,76,0.75)' },
                { icon: CheckCircle, label: 'Published This Week', value: metrics?.published_assets ?? 0, accent: (metrics?.published_assets ?? 0) > 0 ? '#10B981' : '#F8F6F1' },
                { icon: TrendingUp, label: 'Total Assets', value: totalGenerated, accent: '#F8F6F1' },
                { icon: LayoutDashboard, label: 'Active Projects', value: projects.length, accent: '#C9A84C' },
              ].map(({ icon: Icon, label, value, accent }, index) => (
                <Card
                  key={label}
                  className={`relative overflow-hidden border ${index === 0 ? 'border-[rgba(201,168,76,0.18)]' : 'border-[rgba(255,255,255,0.06)]'} ${index >= 2 ? 'hidden md:block' : ''}`}
                >
                  <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[rgba(201,168,76,0.18)] to-transparent" />
                  <Icon size={16} className="mb-2" style={{ color: accent }} />
                  <p className="font-['IBM_Plex_Mono'] text-3xl md:text-[2.1rem] font-bold tracking-tight" style={{ color: accent }}>
                    {(index === 3 && projectsLoading) || (index < 3 && metricsLoading && !metrics)
                      ? <Loader2 size={20} className="animate-spin text-[#C9A84C]" />
                      : <CountUp end={value} />}
                  </p>
                  <p className="font-['IBM_Plex_Sans'] text-[10px] uppercase tracking-[0.18em] text-[rgba(248,246,241,0.45)] mt-2 leading-snug">{label}</p>
                </Card>
              ))}
            </div>
          </AnimatedContent>
        )}

        {/* Pipeline status — shows what agent is running + what data it's reading */}
        {(isRunning || jobResult) && (
          <AnimatedContent delay={0}>
            <div className={`mb-6 rounded-xl border overflow-hidden ${
              jobResult?.status === 'error' ? 'border-[rgba(239,68,68,0.2)]'
              : jobResult?.status === 'done' ? 'border-[rgba(16,185,129,0.2)]'
              : 'border-[rgba(201,168,76,0.2)]'
            }`}>
              {/* Main status row */}
              <div className={`flex items-center gap-3 px-4 py-3 ${
                jobResult?.status === 'error' ? 'bg-[rgba(239,68,68,0.08)]'
                : jobResult?.status === 'done' ? 'bg-[rgba(16,185,129,0.08)]'
                : 'bg-[rgba(201,168,76,0.06)]'
              }`}>
                {isRunning && <Loader2 size={16} className="text-[#C9A84C] animate-spin shrink-0" />}
                {jobResult?.status === 'done' && <CheckCircle size={16} className="text-[#10B981] shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {jobResult?.agent && (
                      <span className="font-['IBM_Plex_Mono'] text-[10px] text-[#C9A84C] bg-[rgba(201,168,76,0.1)] px-2 py-0.5 rounded-full shrink-0">
                        {jobResult.agent}
                      </span>
                    )}
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] truncate">
                      {jobResult?.step || 'Initializing...'}
                    </p>
                  </div>
                </div>
                {jobResult?.status === 'done' && (
                  <Link href="/inbox" className="shrink-0 font-['IBM_Plex_Sans'] text-xs font-bold text-[#0A0A0A] bg-[#C9A84C] px-3 py-2 rounded-lg min-h-[36px] flex items-center">
                    Review →
                  </Link>
                )}
              </div>
              {/* Data sources + decisions */}
              {isRunning && jobResult && ((jobResult.data_sources ?? []).length > 0 || (jobResult.decisions ?? []).length > 0) && (
                <div className="px-4 py-2 bg-[rgba(0,0,0,0.2)] flex flex-wrap gap-2">
                  {jobResult.data_sources?.map((s: string) => (
                    <span key={s} className="font-['IBM_Plex_Mono'] text-[9px] text-[rgba(248,246,241,0.4)] bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.06)] px-2 py-0.5 rounded">
                      📂 {s}
                    </span>
                  ))}
                  {jobResult.decisions?.map((d: string) => (
                    <span key={d} className="font-['IBM_Plex_Mono'] text-[9px] text-[rgba(201,168,76,0.6)] bg-[rgba(201,168,76,0.06)] border border-[rgba(201,168,76,0.1)] px-2 py-0.5 rounded">
                      ✓ {d}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </AnimatedContent>
        )}

        {/* Projects */}
        <AnimatedContent delay={200}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">Projects</h2>
            <Link href="/inbox" className="inline-flex items-center justify-center min-h-[44px] font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] hover:underline px-2">
              Inbox →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projectsLoading && projects.length === 0 ? Array.from({ length: 4 }).map((_, i) => (
              <AnimatedContent key={`project-skeleton-${i}`} delay={250 + i * 40}>
                <Card className="min-h-[178px] border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.02)] animate-pulse">
                  <div className="h-4 w-24 rounded-full bg-[rgba(255,255,255,0.06)] mb-3" />
                  <div className="h-3 w-40 rounded-full bg-[rgba(255,255,255,0.06)] mb-2" />
                  <div className="h-3 w-32 rounded-full bg-[rgba(255,255,255,0.06)] mb-6" />
                  <div className="grid grid-cols-2 gap-2">
                    <div className="h-10 rounded-xl bg-[rgba(255,255,255,0.05)]" />
                    <div className="h-10 rounded-xl bg-[rgba(255,255,255,0.05)]" />
                  </div>
                </Card>
              </AnimatedContent>
            )) : projects.map((project, i) => {
              const projectIsRunning = activeJob?.project === project.slug && isRunning
              const status = projectStatuses[project.slug]
              const statusBadge = projectIsRunning ? (
                <Badge variant="gold" className="gap-1">
                  <Loader2 size={10} className="animate-spin" />
                  Running
                </Badge>
              ) : (status?.pending_approvals ?? 0) > 0 ? (
                <Badge variant="gold">{status?.pending_approvals} pending</Badge>
              ) : !status?.has_logo ? (
                <Badge variant="default">Needs logo</Badge>
              ) : !status?.has_plan ? (
                <Badge variant="default">Not started</Badge>
              ) : status?.plan_status === 'approved' || status?.plan_status === 'executing' ? (
                <Badge variant="success">Ready</Badge>
              ) : (
                <Badge variant="default">{PLAN_STATUS_LABELS[status?.plan_status ?? ''] ?? status?.plan_status ?? project.status}</Badge>
              )
              const cardTone = projectIsRunning
                ? 'border-[rgba(201,168,76,0.22)] bg-[linear-gradient(180deg,rgba(201,168,76,0.08),rgba(255,255,255,0.02))]'
                : (status?.pending_approvals ?? 0) > 0
                ? 'border-[rgba(201,168,76,0.18)] bg-[linear-gradient(180deg,rgba(201,168,76,0.06),rgba(255,255,255,0.02))]'
                : !status?.has_plan
                ? 'border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)]'
                : 'border-[rgba(16,185,129,0.14)] bg-[linear-gradient(180deg,rgba(16,185,129,0.05),rgba(255,255,255,0.02))]'
              const helperText = projectIsRunning
                ? 'Pipeline is running now'
                : (status?.pending_approvals ?? 0) > 0
                ? 'Needs review in Inbox'
                : !status?.has_logo
                ? 'Upload logo first'
                : !status?.has_plan
                ? 'Upload assets to begin'
                : 'Plan ready and waiting'
              const nextAction = {
                upload_logo: { label: 'Upload Logo →', href: `/projects/${project.slug}`, primary: false },
                generate_plan: { label: 'Generate Plan →', href: `/projects/${project.slug}?tab=Pipeline`, primary: false },
                approve_plan: { label: 'Approve Plan →', href: `/projects/${project.slug}?tab=Pipeline`, primary: true },
                review_inbox: { label: `Review Inbox (${status?.pending_approvals ?? 0})`, href: '/inbox', primary: true },
                running: { label: 'Generating...', href: `/projects/${project.slug}`, primary: false },
                complete: { label: 'View Project →', href: `/projects/${project.slug}`, primary: false },
              }[status?.next_action ?? 'complete'] || { label: 'View Project →', href: `/projects/${project.slug}`, primary: false }

              return (
                <AnimatedContent key={project.slug} delay={250 + i * 60}>
                <SpotlightCard>
                  <Card className={`relative overflow-hidden ${cardTone}`}>
                    <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[rgba(201,168,76,0.24)] to-transparent" />
                    <div className="flex items-start justify-between mb-2 gap-3">
                      <div>
                        <h3 className="font-['IBM_Plex_Sans'] text-base text-[#F8F6F1] font-semibold">{project.name}</h3>
                        <p className="text-xs text-gray-500 mt-0.5">{GOAL_LABELS[project.primary_goal] ?? project.primary_goal}</p>
                        <p className="font-['IBM_Plex_Sans'] text-[11px] text-[rgba(248,246,241,0.55)] mt-2">{helperText}</p>
                      </div>
                      {statusBadge}
                    </div>

                    <div className="mt-4 space-y-2">
                      <Link
                        href={nextAction.href}
                        className={`w-full flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm rounded-xl py-3 min-h-[48px] transition-all duration-200 ${nextAction.primary ? 'bg-[#C9A84C] hover:bg-[#E8C97A] text-[#0A0A0A] font-bold' : 'bg-[rgba(201,168,76,0.08)] hover:bg-[rgba(201,168,76,0.15)] text-[#C9A84C] border border-[rgba(201,168,76,0.2)]'}`}
                      >
                        {nextAction.label}
                      </Link>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => triggerPipeline(project.slug, 'plan')}
                          disabled={!!isRunning}
                          className="flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-xs bg-[rgba(201,168,76,0.08)] hover:bg-[rgba(201,168,76,0.15)] text-[#C9A84C] border border-[rgba(201,168,76,0.2)] rounded-xl py-2.5 transition-all duration-200 disabled:opacity-40 min-h-[44px]"
                        >
                          <Play size={13} />
                          Weekly Plan
                        </button>
                        <button
                          onClick={() => triggerPipeline(project.slug, 'run')}
                          disabled={!!isRunning}
                          className="flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-xs bg-[#C9A84C] hover:bg-[#E8C97A] text-[#0A0A0A] rounded-xl py-2.5 font-bold transition-all duration-200 disabled:opacity-40 min-h-[44px]"
                        >
                          <Zap size={13} />
                          Full Pipeline
                        </button>
                      </div>
                    </div>
                  </Card>
                </SpotlightCard>
              </AnimatedContent>
              )
            })}
          </div>
        </AnimatedContent>

        {/* Legend */}
        <AnimatedContent delay={500}>
          <Card className="mt-6">
            <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] leading-relaxed">
              <span className="text-[#C9A84C] font-medium">Weekly Plan</span> — Strategy Agent generates this week&apos;s marketing plan (30 sec) &nbsp;·&nbsp;
              <span className="text-[#C9A84C] font-medium">Full Pipeline</span> — Plan + Copy + Design + QA + sends to Inbox for approval (2-3 min)
            </p>
          </Card>
        </AnimatedContent>

        {!weeklySummaryLoading && !weeklySummaryError && weeklySummary.length > 0 && (
          <AnimatedContent delay={600}>
            <Card className="mt-6">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">This Week&apos;s Insights</h2>
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                    Learning loops from the latest performance review.
                  </p>
                </div>
                <Badge variant="gold">Weekly Summary</Badge>
              </div>

              <div className="space-y-4">
                {weeklySummary.map(project => {
                  const bullets = splitLearnings(project.learnings)
                  return (
                    <Card key={project.slug}>
                      <div className="flex items-start gap-3">
                        {project.top_asset_url ? (
                          <ProjectImage
                            url={project.top_asset_url}
                            alt={`${project.name} best asset`}
                            className="w-16 h-16 rounded-xl overflow-hidden border border-[rgba(201,168,76,0.1)] shrink-0"
                          />
                        ) : (
                          <div className="w-16 h-16 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] shrink-0" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-3 mb-2">
                            <h3 className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-semibold">{project.name}</h3>
                            <Badge variant="channel">Best asset</Badge>
                          </div>
                          <ul className="space-y-1">
                            {bullets.map((bullet, index) => (
                              <li key={`${project.slug}-${index}`} className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.7)] leading-relaxed flex gap-2">
                                <span className="text-[#C9A84C]">•</span>
                                <span>{bullet}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            </Card>
          </AnimatedContent>
        )}

        {!weeklySummaryLoading && !weeklySummaryError && weeklySummary.length === 0 && (
          <AnimatedContent delay={600}>
            <Card className="mt-6">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">This Week&apos;s Insights</h2>
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                    After you approve and publish content, metrics and learnings appear here automatically.
                  </p>
                </div>
                <Badge variant="default">Waiting</Badge>
              </div>
              <Link href="/inbox" className="inline-flex items-center font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] rounded-xl px-4 py-2 min-h-[44px] hover:bg-[rgba(201,168,76,0.08)] transition-all">
                Go to Inbox →
              </Link>
            </Card>
          </AnimatedContent>
        )}

        {weeklySummaryError && (
          <AnimatedContent delay={600}>
            <div className="mt-6">
              <FetchError message={weeklySummaryError} onRetry={loadWeeklySummary} />
            </div>
          </AnimatedContent>
        )}
      </div>
    </div>
  )
}
