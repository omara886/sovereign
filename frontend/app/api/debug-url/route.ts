import { NextResponse } from 'next/server'
export async function GET() {
  return new NextResponse(process.env.BACKEND_URL || 'NOT SET — using default')
}
