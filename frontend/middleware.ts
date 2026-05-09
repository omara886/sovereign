import { NextRequest, NextResponse } from 'next/server'

export function middleware(req: NextRequest) {
  const session = req.cookies.get('sovereign_session')
  const { pathname } = req.nextUrl

  // Public paths — no auth needed
  if (pathname.startsWith('/login') || pathname.startsWith('/api/auth')) {
    // If already logged in, redirect to dashboard
    if (session?.value === 'authenticated' && pathname === '/login') {
      return NextResponse.redirect(new URL('/', req.url))
    }
    return NextResponse.next()
  }

  // All other paths require auth
  if (!session || session.value !== 'authenticated') {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
