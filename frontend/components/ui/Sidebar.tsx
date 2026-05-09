'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, FolderKanban, Inbox, LayoutDashboard, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, labelAr: 'لوحة القيادة', labelEn: 'Dashboard' },
  { href: '/projects', icon: FolderKanban, labelAr: 'المشاريع', labelEn: 'Projects' },
  { href: '/inbox', icon: Inbox, labelAr: 'الموافقة', labelEn: 'Inbox' },
  { href: '/analytics', icon: BarChart3, labelAr: 'التحليلات', labelEn: 'Analytics' },
  { href: '/settings', icon: Settings, labelAr: 'الإعدادات', labelEn: 'Settings' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex fixed top-0 left-0 h-screen w-60 flex-col bg-[#0A0A0A] border-r border-[rgba(201,168,76,0.1)] z-40">
        {/* Logo */}
        <div className="p-6 border-b border-[rgba(201,168,76,0.1)]">
          <span className="font-['Cormorant_Garamond'] text-xl text-[#C9A84C] tracking-widest uppercase">
            Sovereign
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1" dir="rtl">
          {NAV_ITEMS.map(({ href, icon: Icon, labelAr, labelEn }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href))
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                  active
                    ? 'bg-[rgba(201,168,76,0.12)] text-[#C9A84C]'
                    : 'text-[rgba(248,246,241,0.5)] hover:text-[#F8F6F1] hover:bg-[rgba(255,255,255,0.04)]'
                }`}
              >
                <Icon size={18} className="shrink-0" />
                <div className="flex flex-col leading-none">
                  <span className="font-['Cairo'] text-sm">{labelAr}</span>
                  <span className="text-[10px] opacity-50 font-['IBM_Plex_Sans']">{labelEn}</span>
                </div>
                {active && (
                  <span className="mr-auto w-1.5 h-1.5 rounded-full bg-[#C9A84C]" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-[rgba(201,168,76,0.1)]">
          <p className="font-['Cairo'] text-xs text-[rgba(248,246,241,0.3)] text-right">
            عمر الأمران
          </p>
        </div>
      </aside>

      {/* Mobile bottom tab bar */}
      <nav
        className="fixed bottom-4 left-4 right-4 md:hidden z-40 flex items-center justify-around bg-[rgba(30,41,59,0.9)] backdrop-blur-xl border border-[rgba(201,168,76,0.15)] rounded-2xl px-2 py-2 shadow-2xl"
        dir="rtl"
      >
        {NAV_ITEMS.slice(0, 4).map(({ href, icon: Icon, labelAr }) => {
          const active = pathname === href || (href !== '/' && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center gap-1 px-3 py-1 rounded-xl min-w-[44px] min-h-[44px] justify-center transition-all duration-200 ${
                active ? 'text-[#C9A84C]' : 'text-[rgba(248,246,241,0.4)]'
              }`}
            >
              <Icon size={20} />
              <span className="font-['Cairo'] text-[10px]">{labelAr}</span>
            </Link>
          )
        })}
      </nav>
    </>
  )
}
