import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url')
  if (!url) return new NextResponse('missing url', { status: 400 })

  // Only proxy backend URLs — block arbitrary external URLs
  const allowed = [
    process.env.BACKEND_URL || 'https://backend-production-37a17.up.railway.app',
    'https://backend-production-37a17.up.railway.app',
    'https://sovereign-backend.railway.app',
    'http://localhost:8000',
  ]
  if (!allowed.some(b => url.startsWith(b)) && !url.startsWith('file://')) {
    return new NextResponse('forbidden', { status: 403 })
  }

  // file:// URLs can't be fetched — return 404
  if (url.startsWith('file://')) {
    return new NextResponse('file not accessible', { status: 404 })
  }

  // Rewrite old/wrong backend URL to the correct one
  const resolvedUrl = url.replace('sovereign-backend.railway.app', 'backend-production-37a17.up.railway.app')

  try {
    const res = await fetch(resolvedUrl)
    if (!res.ok) return new NextResponse('not found', { status: 404 })
    const blob = await res.arrayBuffer()
    const contentType = res.headers.get('content-type') || 'image/png'
    return new NextResponse(blob, {
      headers: {
        'content-type': contentType,
        'cache-control': 'public, max-age=3600',
      },
    })
  } catch {
    return new NextResponse('error', { status: 502 })
  }
}
