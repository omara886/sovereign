'use client'

import { useState } from 'react'
import { ImageOff } from 'lucide-react'

interface ProjectImageProps {
  url: string | null | undefined
  alt?: string
  className?: string
  fallbackSize?: number
}

function resolveUrl(url: string): string {
  if (url.startsWith('data:')) return url
  if (url.startsWith('file://') || url.includes('railway.app') || url.includes('localhost')) {
    return `/api/img?url=${encodeURIComponent(url)}`
  }
  return url
}

export function ProjectImage({ url, alt = '', className = '', fallbackSize = 20 }: ProjectImageProps) {
  const [broken, setBroken] = useState(false)
  const src = url ? resolveUrl(url) : null

  if (!src || broken) {
    return (
      <div className={`flex items-center justify-center bg-[#0A0A0A] border border-[rgba(255,255,255,0.06)] ${className}`}>
        <ImageOff size={fallbackSize} className="text-[rgba(248,246,241,0.1)]" />
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
