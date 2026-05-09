import React from 'react'

type ButtonVariant = 'primary' | 'ghost' | 'danger' | 'approve' | 'reject'

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-[#C9A84C] text-[#0A0A0A] hover:bg-[#E8C97A] font-semibold',
  ghost: 'bg-[rgba(201,168,76,0.08)] text-[#C9A84C] border border-[rgba(201,168,76,0.2)] hover:bg-[rgba(201,168,76,0.15)]',
  danger: 'bg-[rgba(239,68,68,0.1)] text-[#EF4444] border border-[rgba(239,68,68,0.2)] hover:bg-[rgba(239,68,68,0.2)]',
  approve: 'bg-[rgba(16,185,129,0.1)] text-[#10B981] border border-[rgba(16,185,129,0.25)] hover:bg-[rgba(16,185,129,0.2)] font-semibold',
  reject: 'bg-[rgba(239,68,68,0.1)] text-[#EF4444] border border-[rgba(239,68,68,0.25)] hover:bg-[rgba(239,68,68,0.2)] font-semibold',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  children: React.ReactNode
}

export function Button({ children, variant = 'primary', className = '', ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 font-['Cairo'] text-sm px-4 py-2 rounded-xl transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed ${
        VARIANT_CLASSES[variant]
      } ${className}`}
      style={{ transition: 'all 0.3s cubic-bezier(0.4,0,0.2,1)', ...props.style }}
    >
      {children}
    </button>
  )
}
