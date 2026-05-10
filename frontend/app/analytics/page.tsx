import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { BarChart3 } from 'lucide-react'

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-12 pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">Analytics</h1>
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mt-1">
            Performance metrics across all projects.
          </p>
        </div>
      </div>
      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8">
        <AnimatedContent delay={100}>
          <Card>
            <div className="flex flex-col items-center py-16 gap-4">
              <BarChart3 size={40} className="text-[rgba(201,168,76,0.3)]" />
              <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] text-center max-w-xs">
                Analytics populate after your first published posts. Run the pipeline on a project to get started.
              </p>
            </div>
          </Card>
        </AnimatedContent>
      </div>
    </div>
  )
}
