'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Aurora from '@/components/react-bits/Aurora'
import BlurText from '@/components/react-bits/BlurText'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (res.ok) {
        router.push('/')
        router.refresh()
      } else {
        setError('اسم المستخدم أو كلمة المرور غلط')
      }
    } catch {
      setError('في مشكلة — جرب مرة ثانية')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Aurora className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="font-['Cormorant_Garamond'] text-5xl text-[#C9A84C] tracking-widest mb-2">
            <BlurText text="Sovereign" delay={100} />
          </h1>
          <p className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.4)]">
            مركز التسويق الذاتي
          </p>
        </div>

        {/* Card */}
        <div className="rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.15)] to-transparent border border-[rgba(201,168,76,0.15)]">
          <div className="rounded-[18px] bg-[#1E293B] p-8">
            <form onSubmit={submit} className="space-y-5" dir="rtl">
              <div>
                <label className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.6)] block mb-2">
                  اسم المستخدم
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  autoComplete="username"
                  className="w-full bg-[#0A0A0A] border border-[rgba(201,168,76,0.2)] rounded-xl px-4 py-3 font-['IBM_Plex_Sans'] text-[#F8F6F1] text-sm outline-none focus:border-[#C9A84C] transition-colors duration-200"
                  placeholder="omar"
                  required
                />
              </div>

              <div>
                <label className="font-['Cairo'] text-sm text-[rgba(248,246,241,0.6)] block mb-2">
                  كلمة المرور
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="w-full bg-[#0A0A0A] border border-[rgba(201,168,76,0.2)] rounded-xl px-4 py-3 font-['IBM_Plex_Sans'] text-[#F8F6F1] text-sm outline-none focus:border-[#C9A84C] transition-colors duration-200"
                  placeholder="••••••••••"
                  required
                />
              </div>

              {error && (
                <p className="font-['Cairo'] text-sm text-[#EF4444] text-center">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#C9A84C] hover:bg-[#E8C97A] text-[#0A0A0A] font-['Cairo'] font-bold py-3.5 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-base mt-2"
                style={{ transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)' }}
              >
                {loading ? 'جاري الدخول...' : 'دخول'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </Aurora>
  )
}
