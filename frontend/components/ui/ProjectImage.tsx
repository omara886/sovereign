'use client'

import { useState } from 'react'
import { ImageOff } from 'lucide-react'

interface ProjectImageProps {
  url: string | null | undefined
  alt?: string
  className?: string
}

function fix(url: string | null): string | null {
  if (!url) return null
  if (url.startsWith('data:')) return url
  if (url.includes('sovereign-backend.railway.app')) url = url.replace('sovereign-backend', 'backend-production-37a17')
  if (url.startsWith('file://')) return null
  if (url.includes('railway.app') || url.includes('localhost')) {
    return `/api/img?url=${encodeURIComponent(url)}`
  }
  return url
}

export function ProjectImage({ url, alt = '', className = '' }: ProjectImageProps) {
  const [broken, setBroken] = useState(false)
  const src = fix(url ?? null)

  if (!src || broken) {
    return (
      <div className={`flex items-center justify-center bg-[#0A0A0A] ${className}`}>
        <ImageOff size={18} className="text-[rgba(248,246,241,0.1)]" />
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      className={`object-cover ${className}`}
      onError={() => setBroken(true)}
    />
  )
}
