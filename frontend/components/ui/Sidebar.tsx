'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { BarChart3, CalendarDays, FolderKanban, Inbox, LayoutDashboard, LogOut, Settings } from 'lucide-react'

function getCurrentWeekMondayHref() {
  const now = new Date()
  const day = now.getDay() || 7
  now.setDate(now.getDate() - day + 1)
  now.setHours(0, 0, 0, 0)
  return `/plans/${now.toISOString().slice(0, 10)}`
}

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/projects', icon: FolderKanban, label: 'Projects' },
  { href: getCurrentWeekMondayHref(), icon: CalendarDays, label: 'Plans' },
  { href: '/inbox', icon: Inbox, label: 'Inbox' },
  { href: '/analytics', icon: BarChart3, label: 'Analytics' },
  { href: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [inboxCount, setInboxCount] = useState(0)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/proxy/approvals?status=pending')
        if (res.ok) {
          const data = await res.json()
          setInboxCount(Array.isArray(data) ? data.length : 0)
        }
      } catch {
        // keep the previous count on transient failures
      }
    }
    void load()
    const interval = window.setInterval(() => {
      void load()
    }, 120000) // 2 minutes — no need to hammer the server
    return () => window.clearInterval(interval)
  }, [])

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/login')
    router.refresh()
  }

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href)

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex fixed top-0 left-0 h-screen w-60 flex-col bg-[#0A0A0A] border-r border-[rgba(201,168,76,0.1)] z-40">
        <div className="p-6 border-b border-[rgba(201,168,76,0.1)]">
          <span className="font-['Cormorant_Garamond'] text-xl text-[#C9A84C] tracking-widest uppercase">
            Sovereign
          </span>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {NAV_ITEMS.map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href}
              className={`flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 ${
                isActive(href)
                  ? 'bg-[rgba(201,168,76,0.12)] text-[#C9A84C]'
                  : 'text-[rgba(248,246,241,0.5)] hover:text-[#F8F6F1] hover:bg-[rgba(255,255,255,0.04)]'
              }`}
            >
              <Icon size={18} className="shrink-0" />
              <span className="font-['IBM_Plex_Sans'] text-sm">{label}</span>
              {label === 'Inbox' && inboxCount > 0 && (
                <span className="ml-auto min-w-5 h-5 px-1 rounded-full bg-[#EF4444] text-white text-[10px] font-bold flex items-center justify-center">
                  {inboxCount}
                </span>
              )}
              {isActive(href) && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#C9A84C]" />}
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t border-[rgba(201,168,76,0.1)]">
          <button onClick={logout}
            className="flex items-center gap-3 px-3 py-3 rounded-xl w-full text-[rgba(248,246,241,0.4)] hover:text-[#EF4444] hover:bg-[rgba(239,68,68,0.05)] transition-all duration-200"
          >
            <LogOut size={16} className="shrink-0" />
            <span className="font-['IBM_Plex_Sans'] text-sm">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Mobile bottom tab bar */}
      <nav className="mobile-tab-bar fixed bottom-0 left-0 right-0 md:hidden z-50 bg-[rgba(10,10,10,0.97)] backdrop-blur-xl border-t border-[rgba(201,168,76,0.12)]">
        <div className="flex items-center px-1 pt-2">
          {NAV_ITEMS.slice(0, 5).map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href}
              className={`relative flex flex-col items-center gap-0.5 px-2 py-2 rounded-lg flex-1 min-h-[52px] justify-center transition-colors duration-200 ${
                isActive(href) ? 'text-[#C9A84C]' : 'text-[rgba(248,246,241,0.35)]'
              }`}
            >
              <Icon size={20} />
              <span className="font-['IBM_Plex_Sans'] text-[9px] leading-tight text-center">{label}</span>
              {label === 'Inbox' && inboxCount > 0 && (
                <span className="absolute top-1 right-2 min-w-4 h-4 px-1 rounded-full bg-[#EF4444] text-white text-[9px] font-bold flex items-center justify-center">
                  {inboxCount}
                </span>
              )}
            </Link>
          ))}
        </div>
      </nav>
    </>
  )
}
