import Link from 'next/link'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import SpotlightCard from '@/components/react-bits/SpotlightCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ArrowRight } from 'lucide-react'

const PROJECTS = [
  { slug: 'therapia', name: 'Therapia', model: 'B2C', goal: 'App downloads + health assessments', priority: 1 },
  { slug: 'qawwi', name: 'Qawwi', model: 'B2B', goal: 'Leads + demo requests', priority: 2 },
  { slug: 'productbench', name: 'ProductBench', model: 'SaaS', goal: 'Waitlist + paying customers', priority: 3 },
  { slug: 'sahmalgo', name: 'SahmAlgo', model: 'B2C', goal: 'Followers + signups', priority: 4 },
]

export default function ProjectsPage() {
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
        {PROJECTS.map((p, i) => (
          <AnimatedContent key={p.slug} delay={i * 80}>
            <SpotlightCard>
              <Card>
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="font-['IBM_Plex_Sans'] text-base font-semibold text-[#F8F6F1]">{p.name}</h2>
                      <Badge variant="gold">{p.model}</Badge>
                      <Badge variant="success">Active</Badge>
                    </div>
                    <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)]">{p.goal}</p>
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
