import type { HTMLAttributes, ReactNode } from 'react'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean
  children: ReactNode
  className?: string
}

/** open-codesign Card pattern — token-based, never hardcoded. */
export function Card({ elevated = false, className = '', children, ...rest }: CardProps) {
  const shadow = elevated ? 'shadow-[var(--shadow-card)]' : 'shadow-[var(--shadow-soft)]'
  return (
    <div
      className={`bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-xl)] ${shadow} p-[var(--space-6)] ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}
