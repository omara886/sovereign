'use client'
import { useEffect, useRef, useState } from 'react'

interface CountUpProps {
  end: number
  duration?: number
  prefix?: string
  suffix?: string
  decimals?: number
  className?: string
}

export default function CountUp({
  end,
  duration = 1800,
  prefix = '',
  suffix = '',
  decimals = 0,
  className = '',
}: CountUpProps) {
  const [value, setValue] = useState(0)
  const rafRef = useRef<number | null>(null)
  const startRef = useRef<number | null>(null)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const elRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const el = elRef.current
    if (!el) return

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        observerRef.current?.disconnect()
        startRef.current = null

        const step = (ts: number) => {
          if (!startRef.current) startRef.current = ts
          const progress = Math.min((ts - startRef.current) / duration, 1)
          // ease-out-expo
          const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
          setValue(end * ease)
          if (progress < 1) rafRef.current = requestAnimationFrame(step)
          else setValue(end)
        }
        rafRef.current = requestAnimationFrame(step)
      },
      { threshold: 0.3 }
    )
    observerRef.current.observe(el)

    return () => {
      observerRef.current?.disconnect()
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [end, duration])

  const formatted = decimals > 0
    ? value.toFixed(decimals)
    : Math.round(value).toLocaleString('en-US')

  return (
    <span ref={elRef} className={className}>
      {prefix}{formatted}{suffix}
    </span>
  )
}
