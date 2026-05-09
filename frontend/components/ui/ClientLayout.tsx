'use client'
import { usePathname } from 'next/navigation'
import Sidebar from './Sidebar'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isLogin = pathname === '/login'

  if (isLogin) {
    return <>{children}</>
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      {/* Offset for desktop sidebar, no offset on mobile */}
      <main className="flex-1 md:ml-60 min-h-screen w-full overflow-x-hidden">
        {children}
      </main>
    </div>
  )
}
