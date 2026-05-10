'use client'

import { useRef, useState } from 'react'
import { Check, ThumbsDown } from 'lucide-react'

type SwipeActionsProps = {
  children: React.ReactNode
  onSwipeRight: () => void
  onSwipeLeft: () => void
}

export function SwipeActions({ children, onSwipeRight, onSwipeLeft }: SwipeActionsProps) {
  const [dragX, setDragX] = useState(0)
  const [dragging, setDragging] = useState(false)
  const captured = useRef(false)
  const startX = useRef(0)
  const divRef = useRef<HTMLDivElement>(null)

  const reset = () => {
    setDragX(0)
    setDragging(false)
    captured.current = false
  }

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return
    startX.current = event.clientX
    captured.current = false
    setDragging(false)
    // DO NOT setPointerCapture here — that blocks button clicks
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const deltaX = event.clientX - startX.current
    if (!captured.current && Math.abs(deltaX) < 8) return
    // Only capture after confirmed horizontal drag
    if (!captured.current) {
      try { event.currentTarget.setPointerCapture(event.pointerId) } catch { /* ignore */ }
      captured.current = true
      setDragging(true)
    }
    setDragX(Math.max(-140, Math.min(140, deltaX)))
  }

  const handlePointerUp = () => {
    if (dragX > 100) onSwipeRight()
    else if (dragX < -100) onSwipeLeft()
    reset()
  }

  const dragPercent = Math.min(1, Math.abs(dragX) / 120)

  return (
    <div
      ref={divRef}
      className="relative touch-pan-y select-none"
      style={{
        transform: dragging ? `translateX(${dragX}px) rotate(${dragX / 28}deg)` : 'none',
        transition: dragging ? 'none' : 'transform 200ms ease-out',
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={reset}
    >
      {/* Swipe indicators — only visible when dragging */}
      {dragging && dragX > 0 && (
        <div className="absolute inset-y-0 left-4 flex items-center text-[#10B981] pointer-events-none" style={{ opacity: dragPercent }}>
          <div className="flex items-center gap-2 rounded-full bg-[rgba(16,185,129,0.14)] border border-[rgba(16,185,129,0.25)] px-3 py-2">
            <Check size={18} />
            <span className="font-['IBM_Plex_Sans'] text-xs font-semibold">Approve</span>
          </div>
        </div>
      )}
      {dragging && dragX < 0 && (
        <div className="absolute inset-y-0 right-4 flex items-center text-[#EF4444] pointer-events-none" style={{ opacity: dragPercent }}>
          <div className="flex items-center gap-2 rounded-full bg-[rgba(239,68,68,0.14)] border border-[rgba(239,68,68,0.25)] px-3 py-2">
            <ThumbsDown size={18} />
            <span className="font-['IBM_Plex_Sans'] text-xs font-semibold">Reject</span>
          </div>
        </div>
      )}
      <div className="relative">{children}</div>
    </div>
  )
}
