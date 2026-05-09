import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const { username, password } = await req.json()

  const validUser = process.env.AUTH_USERNAME || 'omar'
  const validPass = process.env.AUTH_PASSWORD || 'Sovereign!2026'

  if (username === validUser && password === validPass) {
    const res = NextResponse.json({ ok: true })
    res.cookies.set('sovereign_session', 'authenticated', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 30, // 30 days
      path: '/',
    })
    return res
  }

  return NextResponse.json({ ok: false }, { status: 401 })
}
