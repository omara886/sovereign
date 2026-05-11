import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'approve' | 'reject'
export type ButtonSize    = 'sm' | 'md' | 'lg'

const VARIANT: Record<ButtonVariant, string> = {
  primary:   'bg-[var(--color-accent)] text-[var(--color-on-accent)] hover:bg-[var(--color-accent-hover)] shadow-[var(--shadow-soft)]',
  secondary: 'bg-[var(--color-surface)] text-[var(--color-text-primary)] border border-[var(--color-border)] hover:bg-[var(--color-surface-hover)]',
  ghost:     'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]',
  approve:   'bg-[var(--color-accent-soft)] text-[var(--color-success)] border border-[rgba(16,185,129,0.3)] hover:bg-[rgba(16,185,129,0.18)]',
  reject:    'bg-[rgba(239,68,68,0.1)] text-[var(--color-error)] border border-[rgba(239,68,68,0.3)] hover:bg-[rgba(239,68,68,0.18)]',
}

const SIZE: Record<ButtonSize, string> = {
  sm: 'h-[var(--size-control-sm)] px-[var(--space-3)] text-[var(--font-size-body-sm)]',
  md: 'h-[var(--size-control-md)] px-[var(--space-4)] text-[var(--font-size-body-sm)]',
  lg: 'h-[var(--size-control-lg)] px-[var(--space-6)] text-[var(--font-size-body)]',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  children: ReactNode
}

/** open-codesign Button pattern — token-based. */
export function Button({ variant = 'primary', size = 'md', className = '', children, ...rest }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] font-medium transition-[var(--transition-fast)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:opacity-50 disabled:pointer-events-none font-[var(--font-sans)] ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
