'use client'
import Link from 'next/link'
export default function Sidebar(){return <aside className="w-60 min-h-screen bg-black/60 p-4 hidden md:block"><nav className="space-y-2 ar"><Link href="/">لوحة القيادة</Link><br/><Link href="/inbox">صندوق الموافقة</Link><br/><Link href="/analytics">التحليلات</Link></nav></aside>}
