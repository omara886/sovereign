'use client'
import React from 'react'

interface AuroraProps {
  children?: React.ReactNode
  className?: string
}

export default function Aurora({ children, className = '' }: AuroraProps) {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      {/* Animated aurora gradient layers */}
      <div
        className="pointer-events-none absolute inset-0 z-0"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(201,168,76,0.18) 0%, transparent 70%)',
          animation: 'aurora-pulse 8s ease-in-out infinite alternate',
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-0"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 60% 50% at 80% 20%, rgba(16,185,129,0.07) 0%, transparent 60%)',
          animation: 'aurora-drift 12s ease-in-out infinite alternate-reverse',
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-0"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 50% 40% at 20% 30%, rgba(201,168,76,0.08) 0%, transparent 50%)',
          animation: 'aurora-drift 10s ease-in-out infinite alternate',
        }}
      />
      <style>{`
        @keyframes aurora-pulse {
          0% { opacity: 0.6; transform: scale(1) translateY(0); }
          100% { opacity: 1; transform: scale(1.05) translateY(-4px); }
        }
        @keyframes aurora-drift {
          0% { opacity: 0.4; transform: translateX(-10px) scale(1); }
          100% { opacity: 0.8; transform: translateX(10px) scale(1.08); }
        }
      `}</style>
      <div className="relative z-10">{children}</div>
    </div>
  )
}
