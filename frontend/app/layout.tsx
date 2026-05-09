import './globals.css'
import Sidebar from '@/components/ui/Sidebar'

export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="ar"><body><div className="md:flex"><Sidebar/><main className="flex-1 p-6">{children}</main></div></body></html>}
