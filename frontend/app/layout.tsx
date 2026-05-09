import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/ui/Sidebar'

export const metadata: Metadata = {
  title: 'Sovereign — مركز التسويق الذاتي',
  description: 'Autonomous AI Marketing Command Center',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body className="bg-[#0A0A0A] text-[#F8F6F1] antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          {/* Main content — offset for desktop sidebar */}
          <main className="flex-1 md:ml-60 min-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
