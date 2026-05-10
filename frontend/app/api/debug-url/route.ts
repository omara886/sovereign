import { NextResponse } from 'next/server'
export async function GET() {
  const url = process.env.BACKEND_URL || 'https://backend-production-37a17.up.railway.app (hardcoded default)'
  return new NextResponse(url)
}
