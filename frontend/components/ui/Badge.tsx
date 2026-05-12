import React from 'react'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'indigo' | 'purple' | 'gold' | 'channel'

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-600 border-gray-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger:  'bg-red-50 text-red-600 border-red-200',
  indigo:  'bg-indigo-50 text-indigo-700 border-indigo-200',
  purple:  'bg-purple-50 text-purple-700 border-purple-200',
  gold:    'bg-amber-50 text-amber-700 border-amber-200',
  channel: 'bg-gray-100 text-gray-500 border-gray-200',
}

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  className?: string
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center font-sans text-xs font-medium px-2 py-0.5 rounded-full border ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
