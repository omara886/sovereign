'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ChevronLeft, ChevronRight, Loader2, CalendarDays } from 'lucide-react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'

const API = '/api/proxy'


type Plan = {
  id: string
  project_id: string
  week_start: string
  objective: string
  funnel_focus: string
  tactics: Array<Record<string, unknown>>
  total_budget_estimate: number | string
  rationale: string
  risk_flags: string[]
  status: string
}

type ProjectRecord = { id: string; slug: string; name: string }

function getMonday(dateInput: string) {
  const date = new Date(dateInput)
  if (Number.isNaN(date.getTime())) return getCurrentMonday()
  const day = date.getDay() || 7
  date.setDate(date.getDate() - day + 1)
  date.setHours(0, 0, 0, 0)
  return date
}

function getCurrentMonday() {
  const now = new Date()
  const day = now.getDay() || 7
  now.setDate(now.getDate() - day + 1)
  now.setHours(0, 0, 0, 0)
  return now
}

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10)
}

function formatLabel(date: Date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function PlanWeekPage() {
  const params = useParams()
  const router = useRouter()
  const weekParam = params.week as string

  const weekStart = useMemo(() => getMonday(`${weekParam}T00:00:00`), [weekParam])
  const weekIso = useMemo(() => isoDate(weekStart), [weekStart])
  const prevWeek = useMemo(() => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() - 7)
    return isoDate(d)
  }, [weekStart])
  const nextWeek = useMemo(() => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + 7)
    return isoDate(d)
  }, [weekStart])

  const [plans, setPlans] = useState<Plan[]>([])
  const [projects, setProjects] = useState<ProjectRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [plansRes, projectsRes] = await Promise.all([
        fetch(`${API}/plans?week_start=${weekIso}`),
        fetch(`${API}/projects`),
      ])
      if (plansRes.ok) setPlans(await plansRes.json())
      else throw new Error(`Plans HTTP ${plansRes.status}`)
      if (projectsRes.ok) setProjects(await projectsRes.json())
      else throw new Error(`Projects HTTP ${projectsRes.status}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not load weekly plans')
    } finally {
      setLoading(false)
    }
  }, [weekIso])

  useEffect(() => {
    void load()
  }, [load])

  const totalBudget = plans.reduce((sum, plan) => sum + Number(plan.total_budget_estimate || 0), 0)
  const plansByProject = useMemo(() => {
    const map = new Map<string, Plan>()
    plans.forEach(plan => map.set(plan.project_id, plan))
    return map
  }, [plans])

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-5xl mx-auto flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2 text-[rgba(248,246,241,0.45)]">
              <CalendarDays size={16} className="text-[#C9A84C]" />
              <span className="font-['IBM_Plex_Sans'] text-xs uppercase tracking-[0.18em]">Weekly Plans</span>
            </div>
            <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">{formatLabel(weekStart)}</h1>
          </div>
          <div className="flex items-stretch gap-2 w-full sm:w-auto">
            <button
              onClick={() => router.push(`/plans/${prevWeek}`)}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.7)] border border-[rgba(255,255,255,0.08)] rounded-xl px-3 py-2.5 min-h-[44px]"
            >
              <ChevronLeft size={16} /> Previous
            </button>
            <button
              onClick={() => router.push(`/plans/${nextWeek}`)}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.7)] border border-[rgba(255,255,255,0.08)] rounded-xl px-3 py-2.5 min-h-[44px]"
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 md:px-8 pt-6 pb-[7rem] space-y-4">
        {error ? (
          <FetchError message={error} onRetry={load} />
        ) : loading ? (
          <Card>
            <div className="flex items-center gap-2 text-[rgba(248,246,241,0.45)] font-['IBM_Plex_Sans'] text-sm py-6">
              <Loader2 size={16} className="animate-spin text-[#C9A84C]" />
              Loading weekly plans...
            </div>
          </Card>
        ) : (
          projects.map((project, index) => {
            const plan = plansByProject.get(project.id)
            return (
              <AnimatedContent key={project.slug} delay={index * 60}>
                <Card>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h2 className="font-['IBM_Plex_Sans'] text-base text-[#F8F6F1] font-semibold">{project.name}</h2>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-1">{project.slug}</p>
                    </div>
                    {plan ? <Badge variant={plan.status === 'approved' ? 'success' : 'gold'}>{plan.status}</Badge> : <Badge variant="default">No plan</Badge>}
                  </div>

                  {plan ? (
                    <div className="space-y-3">
                      <p className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1] leading-tight">{plan.objective}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="gold">{plan.funnel_focus}</Badge>
                        <Badge variant="channel">{plan.tactics.length} tactics</Badge>
                        <Badge variant="default">SAR {Number(plan.total_budget_estimate || 0).toLocaleString('en-US')}</Badge>
                      </div>
                      <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.65)] leading-relaxed">{plan.rationale}</p>
                      <div className="space-y-2">
                        {plan.tactics.map((tactic, tacticIndex) => (
                          <Card key={String(tactic.id ?? tacticIndex)}>
                            <div className="flex flex-wrap items-center gap-2 mb-2">
                              <Badge variant="channel">{String(tactic.channel ?? 'channel')}</Badge>
                              <Badge variant="default">{String(tactic.asset_type ?? 'asset')}</Badge>
                            </div>
                            <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1]">{String(tactic.rationale_simple ?? tactic.rationale ?? 'Tactic details')}</p>
                            <p className="font-['IBM_Plex_Mono'] text-xs text-[rgba(248,246,241,0.45)] mt-2">
                              SAR {Number(tactic.budget_estimate_sar || 0).toLocaleString('en-US')}
                            </p>
                          </Card>
                        ))}
                      </div>
                      {plan.risk_flags.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {plan.risk_flags.map((flag, flagIndex) => (
                            <Badge key={`${flag}-${flagIndex}`} variant="warning">{flag}</Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-[rgba(201,168,76,0.18)] bg-[rgba(201,168,76,0.04)] px-4 py-4">
                      <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">No plans generated yet</p>
                      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-1">
                        Run Weekly Plan from the dashboard for {project.name}.
                      </p>
                    </div>
                  )}
                </Card>
              </AnimatedContent>
            )
          })
        )}

        <AnimatedContent delay={300}>
          <Card>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-['IBM_Plex_Sans'] text-xs uppercase tracking-[0.18em] text-[rgba(248,246,241,0.35)]">Budget Summary</p>
                <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] mt-1">Total SAR planned across all projects</p>
              </div>
              <p className="font-['IBM_Plex_Mono'] text-2xl text-[#C9A84C]">SAR {totalBudget.toLocaleString('en-US')}</p>
            </div>
            <div className="mt-3">
              <Link href="/" className="font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] hover:underline">
                Back to Dashboard
              </Link>
            </div>
          </Card>
        </AnimatedContent>
      </div>
    </div>
  )
}
