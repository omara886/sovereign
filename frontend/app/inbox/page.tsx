'use client'
import { useState } from 'react'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Check, Inbox } from 'lucide-react'

const FILTER_PROJECTS = ['الكل', 'Therapia', 'Qawwi', 'ProductBench', 'Sahmalgo']
const FILTER_TYPES = ['كل المحتوى', 'خطط أسبوعية', 'Instagram', 'LinkedIn', 'X']

export default function InboxPage() {
  const [activeProject, setActiveProject] = useState('الكل')
  const [activeType, setActiveType] = useState('كل المحتوى')

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-32 md:pb-12">
      {/* Header */}
      <div className="pt-12 pb-6 px-6 md:px-8 border-b border-[rgba(201,168,76,0.1)]" dir="rtl">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-1">
            <Inbox size={24} className="text-[#C9A84C]" />
            <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">صندوق الموافقة</h1>
            <span className="font-['IBM_Plex_Mono'] text-sm text-[#C9A84C] bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.2)] px-2.5 py-0.5 rounded-full">
              0
            </span>
          </div>
          <p className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.4)]">
            وافق أو ارفض — كل قرارك يُحفظ ويُعلّم النظام
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 md:px-8 pt-6">
        {/* Project filter tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-3" dir="rtl">
          {FILTER_PROJECTS.map((p) => (
            <button
              key={p}
              onClick={() => setActiveProject(p)}
              className={`shrink-0 font-['Cairo'] text-sm px-4 py-1.5 rounded-full border transition-all duration-200 ${
                activeProject === p
                  ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]'
                  : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)] hover:text-[#F8F6F1]'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Type filter pills */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-6" dir="rtl">
          {FILTER_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setActiveType(t)}
              className={`shrink-0 font-['Cairo'] text-xs px-3 py-1 rounded-lg border transition-all duration-200 ${
                activeType === t
                  ? 'border-[rgba(201,168,76,0.3)] text-[#C9A84C] bg-[rgba(201,168,76,0.08)]'
                  : 'border-[rgba(255,255,255,0.06)] text-[rgba(248,246,241,0.35)]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Empty state */}
        <AnimatedContent delay={100}>
          <Card>
            <div className="flex flex-col items-center py-16 gap-4" dir="rtl">
              <div className="w-16 h-16 rounded-2xl bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] flex items-center justify-center">
                <Check size={32} className="text-[#10B981]" />
              </div>
              <h2 className="font-['Cairo'] text-xl text-[#F8F6F1] font-semibold">كل شي تمام</h2>
              <p className="font-['Cairo'] text-[rgba(248,246,241,0.4)] text-center max-w-xs">
                ما في موافقات معلقة. لما تُولّد الخطة الأسبوعية وتوافق عليها، المحتوى يظهر هنا.
              </p>
              <p className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.25)]">
                الخطة الأسبوعية تُنشأ كل إثنين الساعة ٨ صباحاً بتوقيت الرياض
              </p>
            </div>
          </Card>
        </AnimatedContent>
      </div>
    </div>
  )
}
