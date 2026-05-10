import { NextRequest, NextResponse } from 'next/server'

// Backend URL — server-side only, not exposed to browser
const BACKEND = process.env.BACKEND_URL || 'https://sovereign-backend.railway.app'

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const url = `${BACKEND}/api/${path}${req.nextUrl.search}`

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }

  let body: string | undefined
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    try { body = await req.text() } catch { body = undefined }
  }

  try {
    const res = await fetch(url, {
      method: req.method,
      headers,
      body,
    })
    const data = await res.text()
    return new NextResponse(data, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err) {
    return NextResponse.json({ error: 'Backend unreachable', detail: String(err) }, { status: 502 })
  }
}

export const GET = handler
export const POST = handler
export const PATCH = handler
export const DELETE = handler
