import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'https://backend-production-37a17.up.railway.app'

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const url = `${BACKEND}/api/${path}${req.nextUrl.search}`
  const contentType = req.headers.get('content-type') || ''

  try {
    let fetchOptions: RequestInit

    if (contentType.includes('multipart/form-data')) {
      // Re-create FormData — lets fetch set the correct multipart boundary automatically
      // Forward raw bytes + content-type (including boundary) for multipart
      const raw = await req.arrayBuffer()
      fetchOptions = {
        method: req.method,
        headers: { 'content-type': contentType },
        body: raw,
      }
    } else if (req.method !== 'GET' && req.method !== 'HEAD') {
      const body = await req.arrayBuffer()
      fetchOptions = {
        method: req.method,
        headers: { 'content-type': contentType || 'application/json' },
        body: body.byteLength > 0 ? body : undefined,
      }
    } else {
      fetchOptions = { method: req.method }
    }

    const res = await fetch(url, fetchOptions)
    const resBody = await res.arrayBuffer()
    const resType = res.headers.get('content-type') || 'application/json'

    return new NextResponse(resBody, {
      status: res.status,
      headers: { 'content-type': resType },
    })
  } catch (err) {
    return NextResponse.json(
      { error: 'Backend unreachable', detail: String(err), backend: BACKEND },
      { status: 502 }
    )
  }
}

export const GET = handler
export const POST = handler
export const PATCH = handler
export const DELETE = handler
