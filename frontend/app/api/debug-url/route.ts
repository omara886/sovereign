import { NextResponse } from 'next/server'
export async function GET() {
  const url = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'https://backend-production-37a17.up.railway.app'
  return new NextResponse(url)
}
