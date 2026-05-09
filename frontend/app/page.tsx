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
  { slug: 'therapia', nameAr: 'ثيرابيا', nameEn: 'Therapia', goal: 'تنزيلات التطبيق', status: 'active', pending: 0 },
  { slug: 'qawwi', nameAr: 'قوي', nameEn: 'Qawwi', goal: 'عملاء B2B', status: 'active', pending: 0 },
  { slug: 'productbench', nameAr: 'ProductBench', nameEn: 'ProductBench', goal: 'مستخدمين مدفوعين', status: 'active', pending: 0 },
  { slug: 'sahmalgo', nameAr: 'سهم ألجو', nameEn: 'SahmAlgo', goal: 'متابعين', status: 'active', pending: 0 },
]

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Hero */}
      <Aurora className="pt-16 pb-12 px-6 md:px-8">
        <div dir="rtl" className="max-w-5xl mx-auto">
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mb-2">
            الأحد، ٩ مايو ٢٠٢٦
          </p>
          <h1 className="font-['Cormorant_Garamond'] text-4xl md:text-6xl text-[#F8F6F1] mb-2">
            <BlurText text="مرحبا عمر" delay={100} />
          </h1>
          <p className="font-['Cairo'] text-[rgba(248,246,241,0.5)] text-lg mt-2">
            Sovereign جاهز — اختار المشروع أو راجع الموافقات
          </p>
        </div>
      </Aurora>

      <div className="max-w-5xl mx-auto px-6 md:px-8 pb-32 md:pb-12">
        {/* Stats row */}
        <AnimatedContent delay={100}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10" dir="rtl">
            {[
              { icon: Clock, labelAr: 'بانتظار موافقتك', value: 0, suffix: '' },
              { icon: CheckCircle, labelAr: 'نُشر هذا الأسبوع', value: 0, suffix: '' },
              { icon: TrendingUp, labelAr: 'ميزانية مستخدمة', value: 0, prefix: 'SAR ', suffix: '' },
              { icon: LayoutDashboard, labelAr: 'مشاريع نشطة', value: 4, suffix: '' },
            ].map(({ icon: Icon, labelAr, value, prefix, suffix }) => (
              <Card key={labelAr}>
                <Icon size={18} className="text-[#C9A84C] mb-2" />
                <p className="font-['IBM_Plex_Mono'] text-2xl text-[#F8F6F1] font-bold">
                  <CountUp end={value} prefix={prefix} suffix={suffix} />
                </p>
                <p className="font-['Cairo'] text-xs text-[rgba(248,246,241,0.4)] mt-1">{labelAr}</p>
              </Card>
            ))}
          </div>
        </AnimatedContent>

        {/* Project cards */}
        <AnimatedContent delay={200}>
          <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1] mb-4 text-right" dir="rtl">
            المشاريع
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4" dir="rtl">
            {PROJECTS.map((project, i) => (
              <AnimatedContent key={project.slug} delay={250 + i * 80}>
                <SpotlightCard>
                  <Card>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-['Cairo'] text-lg text-[#F8F6F1] font-semibold">{project.nameAr}</h3>
                        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)]">{project.nameEn}</p>
                      </div>
                      <Badge variant={project.status === 'active' ? 'success' : 'warning'}>
                        {project.status === 'active' ? 'نشط' : 'متوقف'}
                      </Badge>
                    </div>
                    <p className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.5)] mb-4">
                      الهدف: {project.goal}
                    </p>
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/projects/${project.slug}`}
                        className="flex-1 text-center font-['Cairo'] text-sm bg-[rgba(201,168,76,0.12)] hover:bg-[rgba(201,168,76,0.2)] text-[#C9A84C] border border-[rgba(201,168,76,0.2)] rounded-xl py-2 transition-all duration-300"
                        style={{ transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)' }}
                      >
                        راجع المشروع
                      </Link>
                      {project.pending > 0 && (
                        <Link
                          href="/inbox"
                          className="font-['Cairo'] text-sm bg-[#C9A84C] text-[#0A0A0A] rounded-xl py-2 px-4 font-semibold"
                        >
                          وافق ({project.pending})
                        </Link>
                      )}
                    </div>
                  </Card>
                </SpotlightCard>
              </AnimatedContent>
            ))}
          </div>
        </AnimatedContent>

        {/* Quick approvals preview */}
        <AnimatedContent delay={450}>
          <div className="mt-10" dir="rtl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]">الموافقات المعلقة</h2>
              <Link href="/inbox" className="font-['Cairo'] text-sm text-[#C9A84C] hover:underline">
                عرض الكل ←
              </Link>
            </div>
            <Card>
              <p className="font-['Cairo'] text-[rgba(248,246,241,0.4)] text-center py-4">
                ما في موافقات معلقة — كل شي تمام ✅
              </p>
            </Card>
          </div>
        </AnimatedContent>
      </div>
    </div>
  )
}
