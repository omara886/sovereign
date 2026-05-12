'use client'
import { useLayoutEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { BarChart3, CalendarDays, FolderKanban, Inbox, LayoutDashboard, LogOut, Settings, FlaskConical, GitBranch } from 'lucide-react'

function getCurrentWeekMondayHref() {
  const now = new Date()
  const day = now.getDay() || 7
  now.setDate(now.getDate() - day + 1)
  now.setHours(0, 0, 0, 0)
  return `/plans/${now.toISOString().slice(0, 10)}`
}

const NAV_ITEMS = [
  { href: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/projects',  icon: FolderKanban,    label: 'Projects' },
  { href: '/pipeline',  icon: GitBranch,        label: 'Pipeline' },
  { href: getCurrentWeekMondayHref(), icon: CalendarDays, label: 'Plans' },
  { href: '/inbox',     icon: Inbox,            label: 'Inbox' },
  { href: '/analytics', icon: BarChart3,        label: 'Analytics' },
  { href: '/lab',       icon: FlaskConical,     label: 'Lab' },
  { href: '/settings',  icon: Settings,         label: 'Settings' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [inboxCount, setInboxCount] = useState(0)
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' ? window.innerWidth < 768 : false)

  useLayoutEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)

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
    return () => {
      window.clearInterval(interval)
      mq.removeEventListener('change', update)
    }
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
      {!isMobile && (
        <>
      {/* Desktop sidebar — Linear/Notion style */}
      <aside className="hidden md:flex fixed top-0 left-0 h-screen w-56 flex-col bg-white border-r border-gray-200 z-40">
        <div className="px-5 py-4 border-b border-gray-100">
          <span className="text-sm font-bold text-gray-900">Sovereign</span>
          <span className="block text-xs text-gray-400 mt-0.5">Marketing OS</span>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors min-h-[36px] ${
                isActive(href)
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon size={16} className="shrink-0" />
              <span className="flex-1">{label}</span>
              {label === 'Inbox' && inboxCount > 0 && (
                <span className="bg-indigo-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {inboxCount}
                </span>
              )}
            </Link>
          ))}
        </nav>

        <div className="px-3 py-3 border-t border-gray-100">
          <button onClick={logout}
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors w-full min-h-[36px]"
          >
            <LogOut size={16} className="shrink-0" />
            <span className="text-sm">Sign Out</span>
          </button>
        </div>
      </aside>
        </>
      )}

      {isMobile && (
      <nav
        className="mobile-tab-bar"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          background: 'rgba(255,255,255,0.97)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderTop: '1px solid #E5E7EB',
          paddingBottom: 'env(safe-area-inset-bottom)',
          height: 'calc(56px + env(safe-area-inset-bottom))',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', height: 56 }}>
          {NAV_ITEMS.slice(0, 5).map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href}
              className={`relative flex flex-col items-center gap-0.5 flex-1 justify-center transition-colors ${
                isActive(href) ? 'text-indigo-600' : 'text-gray-400'
              }`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                textDecoration: 'none',
                flex: 1,
              }}
            >
              <Icon size={19} />
              <span className="text-[9px] font-medium leading-tight">{label}</span>
              {label === 'Inbox' && inboxCount > 0 && (
                <span className="absolute top-2 right-2 min-w-4 h-4 px-1 rounded-full bg-indigo-600 text-white text-[9px] font-bold flex items-center justify-center">
                  {inboxCount}
                </span>
              )}
            </Link>
          ))}
        </div>
      </nav>
      )}
    </>
  )
}
