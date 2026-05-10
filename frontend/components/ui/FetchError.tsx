import { RefreshCw } from 'lucide-react'

import { Card } from './Card'

export function FetchError({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <Card>
      <div className="flex flex-col items-center py-10 gap-3 text-center">
        <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.5)]">
          {message || 'Could not load data'}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-2 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] border border-[rgba(201,168,76,0.25)] px-3 py-2 rounded-xl hover:bg-[rgba(201,168,76,0.08)] transition-colors min-h-[44px]"
          >
            <RefreshCw size={12} /> Try again
          </button>
        )}
      </div>
    </Card>
  )
}
