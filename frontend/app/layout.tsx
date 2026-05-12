import type { Metadata } from 'next'
import './globals.css'
import ClientLayout from '@/components/ui/ClientLayout'

export const metadata: Metadata = {
  title: 'Sovereign',
  description: 'Autonomous AI Marketing Command Center',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#FAFAFA] text-gray-900 antialiased overflow-x-hidden">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
