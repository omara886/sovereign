import React from 'react'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'gold' | 'channel'

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  default: 'bg-[rgba(255,255,255,0.06)] text-[rgba(248,246,241,0.7)] border-[rgba(255,255,255,0.1)]',
  success: 'bg-[rgba(16,185,129,0.1)] text-[#10B981] border-[rgba(16,185,129,0.25)]',
  warning: 'bg-[rgba(245,158,11,0.1)] text-[#F59E0B] border-[rgba(245,158,11,0.25)]',
  danger: 'bg-[rgba(239,68,68,0.1)] text-[#EF4444] border-[rgba(239,68,68,0.25)]',
  gold: 'bg-[rgba(201,168,76,0.12)] text-[#C9A84C] border-[rgba(201,168,76,0.25)]',
  channel: 'bg-[rgba(201,168,76,0.08)] text-[rgba(248,246,241,0.6)] border-[rgba(201,168,76,0.15)]',
}

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center font-['IBM_Plex_Sans'] text-xs px-2.5 py-0.5 rounded-full border ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
