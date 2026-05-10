import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url')
  if (!url) return new NextResponse('missing url', { status: 400 })

  // Only proxy backend URLs — block arbitrary external URLs
  const BACKEND = process.env.BACKEND_URL || 'https://backend-production-37a17.up.railway.app'
  if (!url.startsWith(BACKEND) && !url.startsWith('https://backend-production-37a17')) {
    return new NextResponse('forbidden', { status: 403 })
  }

  try {
    const res = await fetch(url)
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
