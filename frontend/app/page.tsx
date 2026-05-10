'use client'
import { useState, useEffect, useCallback } from 'react'
import Aurora from '@/components/react-bits/Aurora'
import BlurText from '@/components/react-bits/BlurText'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import CountUp from '@/components/react-bits/CountUp'
import SpotlightCard from '@/components/react-bits/SpotlightCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'
import { CheckCircle, Clock, LayoutDashboard, Loader2, Play, TrendingUp, Zap } from 'lucide-react'

const PROJECTS = [
  { slug: 'therapia', name: 'Therapia', goal: 'App downloads + health assessments' },
  { slug: 'qawwi', name: 'Qawwi', goal: 'B2B leads + demo requests' },
  { slug: 'productbench', name: 'ProductBench', goal: 'Waitlist signups + paying customers' },
  { slug: 'sahmalgo', name: 'SahmAlgo', goal: 'Followers + signups' },
]

const API = '/api/proxy'

type JobStatus = { status: string; step: string; assets_passed_qa?: number; objective?: string; email_sent?: boolean }
type MetricsSummary = {
  published_assets: number
  pending_approvals: number
  total_assets_generated: number
}
type WeeklySummaryItem = {
  name: string
  slug: string
  learnings: string
  top_asset_url: string | null
}

const JOB_KEY = 'sovereign_active_job'

function proxyImg(url: string | null) {
  if (!url) return null
  if (url.startsWith('data:')) return url
  if (url.startsWith('file://') || url.includes('railway.app') || url.includes('localhost:8000')) {
    return `/api/img?url=${encodeURIComponent(url)}`
  }
  return url
}

function splitLearnings(text: string) {
  return text
    .replace(/\r/g, '')
    .split(/\n|•|;|\.\s+/)
    .map(part => part.trim().replace(/^[-*]\s*/, ''))
    .filter(Boolean)
    .slice(0, 3)
}

export default function DashboardPage() {
  const [activeJob, setActiveJob] = useState<{ jobId: string; project: string; mode: string } | null>(null)
  const [jobResult, setJobResult] = useState<JobStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null)
  const [metricsLoading, setMetricsLoading] = useState(true)
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummaryItem[]>([])
  const [weeklySummaryLoading, setWeeklySummaryLoading] = useState(true)

  const loadMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API}/metrics/summary`)
      if (res.ok) {
        setMetrics(await res.json())
      }
    } catch {
      // keep prior data on transient failures
    } finally {
      setMetricsLoading(false)
    }
  }, [])

  const loadWeeklySummary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/metrics/weekly-summary`)
      if (res.ok) {
        const data = await res.json()
        setWeeklySummary(data.projects || [])
      }
    } catch {
      // ignore transient errors
    } finally {
      setWeeklySummaryLoading(false)
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
    const interval = window.setInterval(() => {
      void loadMetrics()
    }, 300000) // 5 minutes — metrics don't change often
    return () => window.clearInterval(interval)
  }, [loadMetrics, loadWeeklySummary])

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

      <div className="max-w-5xl mx-auto px-4 md:px-8 pb-8">

        {/* Stats */}
        <AnimatedContent delay={100}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            {[
              { icon: Clock, label: 'Pending Approvals', value: metrics?.pending_approvals ?? 0 },
              { icon: CheckCircle, label: 'Published This Week', value: metrics?.published_assets ?? 0 },
              { icon: TrendingUp, label: 'Total Assets', value: metrics?.total_assets_generated ?? 0 },
              { icon: LayoutDashboard, label: 'Active Projects', value: PROJECTS.length },
            ].map(({ icon: Icon, label, value }) => (
              <Card key={label}>
                <Icon size={16} className="text-[#C9A84C] mb-2" />
                <p className="font-['IBM_Plex_Mono'] text-2xl text-[#F8F6F1] font-bold">
                  {metricsLoading && !metrics ? <Loader2 size={18} className="animate-spin text-[#C9A84C]" /> : <CountUp end={value} />}
                </p>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1 leading-snug">{label}</p>
              </Card>
            ))}
          </div>
        </AnimatedContent>

        {!metricsLoading && (metrics?.total_assets_generated ?? 0) === 0 && (
          <AnimatedContent delay={150}>
            <div className="mb-6 rounded-xl border border-[rgba(201,168,76,0.2)] bg-[rgba(201,168,76,0.05)] px-5 py-4 flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[#C9A84C] text-[#0A0A0A] flex items-center justify-center font-bold text-sm shrink-0">1</div>
              <div>
                <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-1">Start with Therapia</p>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)]">
                  Upload your logo, generate a weekly plan, approve content, and it publishes automatically.
                </p>
                <Link href="/projects/therapia" className="inline-block mt-2 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] hover:underline">
                  Set up Therapia →
                </Link>
              </div>
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
            {PROJECTS.map((project, i) => (
              <AnimatedContent key={project.slug} delay={250 + i * 60}>
                <SpotlightCard>
                  <Card>
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-['IBM_Plex_Sans'] text-base text-[#F8F6F1] font-semibold">{project.name}</h3>
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-0.5">{project.goal}</p>
                      </div>
                      <Badge variant="success">Active</Badge>
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
            ))}
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

        {!weeklySummaryLoading && weeklySummary.length > 0 && (
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
                          <div className="w-16 h-16 rounded-xl overflow-hidden border border-[rgba(201,168,76,0.1)] shrink-0">
                            <img
                              src={proxyImg(project.top_asset_url) || project.top_asset_url}
                              alt={`${project.name} best asset`}
                              className="w-full h-full object-cover"
                            />
                          </div>
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

        {!weeklySummaryLoading && weeklySummary.length === 0 && (
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
      </div>
    </div>
  )
}
