import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'https://sovereign-backend.railway.app'

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const url = `${BACKEND}/api/${path}${req.nextUrl.search}`

  // Forward content-type so multipart/form-data (file uploads) and JSON both work
  const contentType = req.headers.get('content-type') || ''
  const forwardHeaders: Record<string, string> = {}
  if (contentType) forwardHeaders['content-type'] = contentType

  let body: ArrayBuffer | undefined
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    try { body = await req.arrayBuffer() } catch { /* no body */ }
  }

  try {
    const res = await fetch(url, {
      method: req.method,
      headers: forwardHeaders,
      body: body && body.byteLength > 0 ? body : undefined,
    })

    const resContentType = res.headers.get('content-type') || 'application/json'
    const resBody = await res.arrayBuffer()

    return new NextResponse(resBody, {
      status: res.status,
      headers: { 'content-type': resContentType },
    })
  } catch (err) {
    return NextResponse.json(
      { error: 'Backend unreachable', detail: String(err) },
      { status: 502 }
    )
  }
}

export const GET = handler
export const POST = handler
export const PATCH = handler
export const DELETE = handler
