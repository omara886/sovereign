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
  const pointerId = useRef<number | null>(null)
  const startX = useRef(0)

  const reset = () => {
    setDragX(0)
    setDragging(false)
    pointerId.current = null
  }

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return
    pointerId.current = event.pointerId
    startX.current = event.clientX
    setDragging(false)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerId.current !== event.pointerId) return
    const deltaX = event.clientX - startX.current
    if (!dragging && Math.abs(deltaX) < 6) return
    setDragging(true)
    setDragX(Math.max(-140, Math.min(140, deltaX)))
  }

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerId.current !== event.pointerId) return
    const deltaX = dragX
    if (deltaX > 100) {
      onSwipeRight()
    } else if (deltaX < -100) {
      onSwipeLeft()
    }
    reset()
  }

  const handlePointerCancel = () => reset()

  const dragPercent = Math.min(1, Math.abs(dragX) / 120)

  return (
    <div
      className="relative touch-pan-y select-none"
      style={{
        transform: `translateX(${dragX}px) rotate(${dragX / 24}deg)`,
        transition: dragging ? 'none' : 'transform 180ms ease-out',
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
    >
      <div
        className="absolute inset-y-0 left-4 flex items-center text-[#10B981] pointer-events-none"
        style={{ opacity: dragX > 0 ? dragPercent : 0 }}
      >
        <div className="flex items-center gap-2 rounded-full bg-[rgba(16,185,129,0.14)] border border-[rgba(16,185,129,0.25)] px-3 py-2">
          <Check size={18} />
          <span className="font-['IBM_Plex_Sans'] text-xs font-semibold">Approve</span>
        </div>
      </div>
      <div
        className="absolute inset-y-0 right-4 flex items-center text-[#EF4444] pointer-events-none"
        style={{ opacity: dragX < 0 ? dragPercent : 0 }}
      >
        <div className="flex items-center gap-2 rounded-full bg-[rgba(239,68,68,0.14)] border border-[rgba(239,68,68,0.25)] px-3 py-2">
          <ThumbsDown size={18} />
          <span className="font-['IBM_Plex_Sans'] text-xs font-semibold">Reject</span>
        </div>
      </div>
      <div className="relative">{children}</div>
    </div>
  )
}
