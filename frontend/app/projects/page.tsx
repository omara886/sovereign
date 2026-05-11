'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import SpotlightCard from '@/components/react-bits/SpotlightCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { FetchError } from '@/components/ui/FetchError'
import { ArrowRight, Loader2 } from 'lucide-react'

const API = '/api/proxy'

type Project = {
  id: string
  slug: string
  name: string
  business_model: string
  primary_goal: string
  status: string
  priority: number
}

const MODEL_LABELS: Record<string, string> = {
  b2c: 'B2C', b2b: 'B2B', saas: 'SaaS', marketplace: 'Marketplace',
}

const GOAL_LABELS: Record<string, string> = {
  app_downloads_and_health_assessments_completed: 'App downloads + health assessments',
  leads_and_demo_requests: 'Leads + demo requests',
  waitlist_and_paying_customers: 'Waitlist + paying customers',
  followers_and_signups: 'Followers + signups',
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    fetch(`${API}/projects`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then((data: Project[]) => setProjects([...data].sort((a, b) => (a.priority || 99) - (b.priority || 99))))
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-[calc(3rem+env(safe-area-inset-top))] pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Projects</h1>
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mt-1">
            Upload assets, review brand memory, trigger pipeline per project.
          </p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8 space-y-4">
        {loading && (
          <div className="flex items-center gap-3 py-8 text-[rgba(248,246,241,0.4)]">
            <Loader2 size={18} className="animate-spin text-[#C9A84C]" />
            <span className="font-['IBM_Plex_Sans'] text-sm">Loading projects...</span>
          </div>
        )}

        {error && !loading && <FetchError message={error} onRetry={load} />}

        {!loading && !error && projects.length === 0 && (
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] py-8 text-center">
            No projects yet.
          </p>
        )}

        {projects.map((p, i) => (
          <AnimatedContent key={p.id} delay={i * 80}>
            <SpotlightCard>
              <Card>
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="font-['IBM_Plex_Sans'] text-base font-semibold text-[#F8F6F1]">{p.name}</h2>
                      <Badge variant="gold">{MODEL_LABELS[p.business_model] ?? p.business_model}</Badge>
                      <Badge variant={p.status === 'active' ? 'success' : 'default'}>{p.status}</Badge>
                    </div>
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)]">
                      {GOAL_LABELS[p.primary_goal] ?? p.primary_goal}
                    </p>
                  </div>
                  <Link href={`/projects/${p.slug}`}
                    className="flex items-center gap-1 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] hover:text-[#E8C97A] transition-colors ml-4 shrink-0 min-h-[44px] px-2"
                  >
                    Open <ArrowRight size={16} />
                  </Link>
                </div>
              </Card>
            </SpotlightCard>
          </AnimatedContent>
        ))}
      </div>
    </div>
  )
}
