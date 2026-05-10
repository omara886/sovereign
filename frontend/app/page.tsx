'use client'
import { useState, useEffect, useCallback } from 'react'
import Aurora from '@/components/react-bits/Aurora'
import BlurText from '@/components/react-bits/BlurText'
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

type JobStatus = { status: string; step: string; assets_passed_qa?: number; objective?: string; email_sent?: boolean }
type MetricsSummary = {
  published_assets: number
  pending_approvals: number
  total_assets_generated: number
}
type ProjectSummary = {
  id: string
  slug: string
  name: string
  primary_goal: string
  status: string
  pendingApprovals: number
  hasPlan: boolean
}
type WeeklySummaryItem = {
  name: string
  slug: string
  learnings: string
  top_asset_url: string | null
}

const JOB_KEY = 'sovereign_active_job'

function splitLearnings(text: string) {
  return text
    .replace(/\r/g, '')
    .split(/\n|•|;|\.\s+/)
    .map(part => part.trim().replace(/^[-*]\s*/, ''))
    .filter(Boolean)
    .slice(0, 3)
}

function TodaysFocus({
  pendingApprovals,
  totalGenerated,
  loading,
}: {
  pendingApprovals: number
  totalGenerated: number
  loading: boolean
}) {
  if (loading) return null

  if (pendingApprovals > 0) {
    return (
      <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(201,168,76,0.08)] border border-[rgba(201,168,76,0.2)]">
        <div className="w-10 h-10 rounded-full bg-[#C9A84C] text-[#0A0A0A] font-bold text-sm flex items-center justify-center shrink-0">
          {pendingApprovals}
        </div>
        <div className="flex-1">
          <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">
            {pendingApprovals} asset{pendingApprovals > 1 ? 's' : ''} waiting for your approval
          </p>
          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">
            Review and approve to schedule publishing
          </p>
        </div>
        <Link href="/inbox" className="shrink-0 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] px-4 py-2 rounded-xl min-h-[44px] flex items-center hover:bg-[#E8C97A] transition-colors">
          Review →
        </Link>
      </div>
    )
  }

  if (totalGenerated === 0) {
    return (
      <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.07)]">
        <div className="w-10 h-10 rounded-full bg-[rgba(201,168,76,0.15)] border border-[rgba(201,168,76,0.3)] text-[#C9A84C] font-bold text-sm flex items-center justify-center shrink-0">
          1
        </div>
        <div className="flex-1">
          <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Start with Therapia</p>
          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">Upload logo → generate plan → approve → publishes automatically</p>
        </div>
        <Link href="/projects/therapia" className="shrink-0 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] px-4 py-2 rounded-xl min-h-[44px] flex items-center hover:bg-[rgba(201,168,76,0.08)] transition-colors">
          Set up →
        </Link>
      </div>
    )
  }

  return (
    <div className="mb-6 flex items-center gap-3 px-5 py-3 rounded-xl bg-[rgba(16,185,129,0.06)] border border-[rgba(16,185,129,0.15)]">
      <div className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
      <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">
        System running — next plan generates Monday 8AM Riyadh
      </p>
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
      const enriched = await Promise.all(data.map(async project => {
        const [approvalsRes, planRes] = await Promise.all([
          fetch(`${API}/approvals?status=pending&project_id=${project.id}`),
          fetch(`${API}/plans/current/${project.slug}`),
        ])
        const approvals = approvalsRes.ok ? await approvalsRes.json() : []
        return {
          ...project,
          pendingApprovals: Array.isArray(approvals) ? approvals.length : 0,
          hasPlan: planRes.ok,
        }
      }))
      setProjects(enriched)
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
    <div className="min-h-screen bg-[#0A0A0A]">
      <Aurora className="pt-[calc(3.5rem+env(safe-area-inset-top))] pb-10 px-4 md:px-8">
        <div className="max-w-5xl mx-auto">
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mb-2">Sovereign</p>
          <h1 className="font-['Cormorant_Garamond'] text-4xl md:text-6xl text-[#F8F6F1] mb-2">
            <BlurText text="Welcome back, Omar" delay={100} />
          </h1>
          <p className="font-['IBM_Plex_Sans'] text-[rgba(248,246,241,0.5)] text-base mt-2">
            Your autonomous marketing command center.
          </p>
        </div>
      </Aurora>

      <div className="max-w-5xl mx-auto px-4 md:px-8 pb-[7rem]">
        {metricsError ? (
          <AnimatedContent delay={80}>
            <FetchError message={metricsError} onRetry={loadMetrics} />
          </AnimatedContent>
        ) : null}

        <TodaysFocus pendingApprovals={pendingApprovals} totalGenerated={totalGenerated} loading={metricsLoading} />

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

        {/* Job status bar */}
        {(isRunning || jobResult) && (
          <AnimatedContent delay={0}>
            <div className={`mb-6 rounded-xl px-5 py-4 border flex items-center gap-3 ${
              jobResult?.status === 'error'
                ? 'bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.2)]'
                : jobResult?.status === 'done'
                ? 'bg-[rgba(16,185,129,0.08)] border-[rgba(16,185,129,0.2)]'
                : 'bg-[rgba(201,168,76,0.08)] border-[rgba(201,168,76,0.2)]'
            }`}>
              {isRunning && <Loader2 size={18} className="text-[#C9A84C] animate-spin shrink-0" />}
              {jobResult?.status === 'done' && <CheckCircle size={18} className="text-[#10B981] shrink-0" />}
              <div className="flex-1 min-w-0">
                <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">
                  {jobResult?.step || 'Starting...'}
                </p>
                {jobResult?.status === 'done' && jobResult.objective && (
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-0.5 line-clamp-1">
                    {jobResult.objective}
                  </p>
                )}
              </div>
              {jobResult?.status === 'done' && (
                <Link href="/inbox"
                  className="shrink-0 font-['IBM_Plex_Sans'] text-sm bg-[#C9A84C] text-[#0A0A0A] px-4 py-2 rounded-xl font-bold min-h-[44px] flex items-center"
                >
                  Go to Inbox →
                </Link>
              )}
            </div>
          </AnimatedContent>
        )}

        {/* Projects */}
        <AnimatedContent delay={200}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">Projects</h2>
            <Link href="/inbox" className="font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] hover:underline">
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
              const statusBadge = projectIsRunning ? (
                <Badge variant="gold" className="gap-1">
                  <Loader2 size={10} className="animate-spin" />
                  Running
                </Badge>
              ) : project.pendingApprovals > 0 ? (
                <Badge variant="gold">{project.pendingApprovals} pending</Badge>
              ) : !project.hasPlan ? (
                <Badge variant="default">Not started</Badge>
              ) : project.status === 'active' ? (
                <Badge variant="success">Ready</Badge>
              ) : (
                <Badge variant="default">{project.status}</Badge>
              )
              const cardTone = projectIsRunning
                ? 'border-[rgba(201,168,76,0.22)] bg-[linear-gradient(180deg,rgba(201,168,76,0.08),rgba(255,255,255,0.02))]'
                : project.pendingApprovals > 0
                ? 'border-[rgba(201,168,76,0.18)] bg-[linear-gradient(180deg,rgba(201,168,76,0.06),rgba(255,255,255,0.02))]'
                : !project.hasPlan
                ? 'border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.02)]'
                : 'border-[rgba(16,185,129,0.14)] bg-[linear-gradient(180deg,rgba(16,185,129,0.05),rgba(255,255,255,0.02))]'
              const helperText = projectIsRunning
                ? 'Pipeline is running now'
                : project.pendingApprovals > 0
                ? 'Needs review in Inbox'
                : !project.hasPlan
                ? 'Upload assets to begin'
                : 'Plan ready and waiting'

              return (
                <AnimatedContent key={project.slug} delay={250 + i * 60}>
                <SpotlightCard>
                  <Card className={`relative overflow-hidden ${cardTone}`}>
                    <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[rgba(201,168,76,0.24)] to-transparent" />
                    <div className="flex items-start justify-between mb-2 gap-3">
                      <div>
                        <h3 className="font-['IBM_Plex_Sans'] text-base text-[#F8F6F1] font-semibold">{project.name}</h3>
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-0.5">{project.primary_goal}</p>
                        <p className="font-['IBM_Plex_Sans'] text-[11px] text-[rgba(248,246,241,0.55)] mt-2">{helperText}</p>
                      </div>
                      {statusBadge}
                    </div>

                    {/* Action buttons */}
                    <div className="grid grid-cols-2 gap-2 mt-4">
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
                  </Card>
                </SpotlightCard>
              </AnimatedContent>
              )
            })}
          </div>
        </AnimatedContent>

        {/* Legend */}
        <AnimatedContent delay={500}>
          <div className="mt-6 rounded-xl bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] px-5 py-4">
            <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] leading-relaxed">
              <span className="text-[#C9A84C] font-medium">Weekly Plan</span> — Strategy Agent generates this week&apos;s marketing plan (30 sec) &nbsp;·&nbsp;
              <span className="text-[#C9A84C] font-medium">Full Pipeline</span> — Plan + Copy + Design + QA + sends to Inbox for approval (2-3 min)
            </p>
          </div>
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
                    <div key={project.slug} className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.015)] p-4">
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
                    </div>
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
