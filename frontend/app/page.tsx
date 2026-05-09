import Aurora from '@/components/react-bits/Aurora'
import BlurText from '@/components/react-bits/BlurText'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import CountUp from '@/components/react-bits/CountUp'
import SpotlightCard from '@/components/react-bits/SpotlightCard'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'
import { CheckCircle, Clock, LayoutDashboard, TrendingUp } from 'lucide-react'

const PROJECTS = [
  { slug: 'therapia', nameEn: 'Therapia', goal: 'App downloads + assessments', status: 'active', pending: 0 },
  { slug: 'qawwi', nameEn: 'Qawwi', goal: 'B2B leads + demo requests', status: 'active', pending: 0 },
  { slug: 'productbench', nameEn: 'ProductBench', goal: 'Paying customers', status: 'active', pending: 0 },
  { slug: 'sahmalgo', nameEn: 'SahmAlgo', goal: 'Followers + signups', status: 'active', pending: 0 },
]

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Aurora className="pt-14 pb-10 px-4 md:px-8">
        <div className="max-w-5xl mx-auto">
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mb-2">
            Sovereign — Week of May 10, 2026
          </p>
          <h1 className="font-['Cormorant_Garamond'] text-4xl md:text-6xl text-[#F8F6F1] mb-2">
            <BlurText text="Welcome back, Omar" delay={100} />
          </h1>
          <p className="font-['IBM_Plex_Sans'] text-[rgba(248,246,241,0.5)] text-base mt-2">
            Your marketing runs autonomously. Approve, reject, and review.
          </p>
        </div>
      </Aurora>

      <div className="max-w-5xl mx-auto px-4 md:px-8 pb-8">
        {/* Stats */}
        <AnimatedContent delay={100}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            {[
              { icon: Clock, label: 'Pending Approvals', value: 0 },
              { icon: CheckCircle, label: 'Published This Week', value: 0 },
              { icon: TrendingUp, label: 'Budget Used (SAR)', value: 0 },
              { icon: LayoutDashboard, label: 'Active Projects', value: 4 },
            ].map(({ icon: Icon, label, value }) => (
              <Card key={label}>
                <Icon size={16} className="text-[#C9A84C] mb-2" />
                <p className="font-['IBM_Plex_Mono'] text-2xl text-[#F8F6F1] font-bold">
                  <CountUp end={value} />
                </p>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1 leading-snug">{label}</p>
              </Card>
            ))}
          </div>
        </AnimatedContent>

        {/* Projects */}
        <AnimatedContent delay={200}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">Projects</h2>
            <Link href="/inbox" className="font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] hover:underline">
              View Inbox →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {PROJECTS.map((project, i) => (
              <AnimatedContent key={project.slug} delay={250 + i * 60}>
                <SpotlightCard>
                  <Card>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-['IBM_Plex_Sans'] text-base text-[#F8F6F1] font-semibold">{project.nameEn}</h3>
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-0.5">{project.goal}</p>
                      </div>
                      <Badge variant="success">Active</Badge>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <Link href={`/projects/${project.slug}`}
                        className="flex-1 text-center font-['IBM_Plex_Sans'] text-sm bg-[rgba(201,168,76,0.08)] hover:bg-[rgba(201,168,76,0.15)] text-[#C9A84C] border border-[rgba(201,168,76,0.2)] rounded-xl py-2.5 transition-all duration-200 min-h-[44px] flex items-center justify-center"
                      >
                        View Project
                      </Link>
                      {project.pending > 0 && (
                        <Link href="/inbox"
                          className="font-['IBM_Plex_Sans'] text-sm bg-[#C9A84C] text-[#0A0A0A] rounded-xl py-2.5 px-4 font-semibold min-h-[44px] flex items-center"
                        >
                          Approve ({project.pending})
                        </Link>
                      )}
                    </div>
                  </Card>
                </SpotlightCard>
              </AnimatedContent>
            ))}
          </div>
        </AnimatedContent>

        {/* Quick approvals */}
        <AnimatedContent delay={450}>
          <div className="mt-8">
            <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1] mb-4">Pending Approvals</h2>
            <Card>
              <div className="flex flex-col items-center py-10 gap-3">
                <CheckCircle size={32} className="text-[#10B981]" />
                <p className="font-['IBM_Plex_Sans'] text-[rgba(248,246,241,0.4)] text-center text-sm">
                  No pending approvals — you&apos;re all caught up.
                </p>
              </div>
            </Card>
          </div>
        </AnimatedContent>
      </div>
    </div>
  )
}
