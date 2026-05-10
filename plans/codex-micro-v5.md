# CODEX MICRO PLAN — V5
# Read all. Execute sequentially. One commit per task.
# npm run build MUST pass before every commit. Zero errors.

---

## CONTEXT
Frontend: https://frontend-production-9eea5.up.railway.app
Backend: https://backend-production-37a17.up.railway.app
Stack: Next.js 14 + FastAPI + PostgreSQL on Railway

---

## TASK 1 — Images: one standard component everywhere
**Files:** frontend/components/ui/ProjectImage.tsx (CREATE), then replace all <img> tags

Create this exact component:
```tsx
'use client'
import { useState } from 'react'
import { ImageOff } from 'lucide-react'
function fix(url: string | null) {
  if (!url) return null
  if (url.startsWith('data:')) return url
  if (url.includes('sovereign-backend.railway.app')) url = url.replace('sovereign-backend', 'backend-production-37a17')
  if (url.startsWith('file://')) return null
  if (url.includes('railway.app') || url.includes('localhost')) return `/api/img?url=${encodeURIComponent(url)}`
  return url
}
export function ProjectImage({ url, alt='', className='' }: { url?: string|null; alt?: string; className?: string }) {
  const [err, setErr] = useState(false)
  const src = fix(url ?? null)
  if (!src || err) return <div className={`flex items-center justify-center bg-[#0A0A0A] ${className}`}><ImageOff size={18} className="text-[rgba(248,246,241,0.1)]"/></div>
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} onError={() => setErr(true)} />
}
```

Then grep: `grep -rn "<img " frontend/app/ frontend/components/`
Replace EVERY result with `<ProjectImage>`. Remove all `proxyImg`, `Thumb`, `ProjectAssetThumb` functions.

Success: `npm run build` — zero `no-img-element` warnings.

---

## TASK 2 — Dashboard: Today's Focus banner
**File:** frontend/app/page.tsx

After the Aurora section, before stats, add:
```tsx
{/* TodaysFocus — shows most important action */}
{!metricsLoading && metrics.pending_approvals > 0 && (
  <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(201,168,76,0.08)] border border-[rgba(201,168,76,0.2)]">
    <div className="w-10 h-10 rounded-full bg-[#C9A84C] text-[#0A0A0A] font-bold text-sm flex items-center justify-center shrink-0">{metrics.pending_approvals}</div>
    <div className="flex-1 min-w-0">
      <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">{metrics.pending_approvals} asset{metrics.pending_approvals>1?'s':''} waiting for approval</p>
      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">Review and approve to schedule publishing</p>
    </div>
    <Link href="/inbox" className="shrink-0 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] px-4 py-2.5 rounded-xl min-h-[44px] flex items-center hover:bg-[#E8C97A] transition-colors">Review →</Link>
  </div>
)}
{!metricsLoading && metrics.pending_approvals === 0 && metrics.total_assets_generated === 0 && (
  <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)]">
    <div className="w-10 h-10 rounded-full bg-[rgba(201,168,76,0.15)] border border-[rgba(201,168,76,0.3)] text-[#C9A84C] font-bold flex items-center justify-center shrink-0 text-sm">1</div>
    <div className="flex-1 min-w-0">
      <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Start with Therapia</p>
      <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">Upload logo → generate plan → approve content → publishes automatically</p>
    </div>
    <Link href="/projects/therapia" className="shrink-0 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] border border-[rgba(201,168,76,0.3)] px-4 py-2.5 rounded-xl min-h-[44px] flex items-center hover:bg-[rgba(201,168,76,0.08)] transition-colors">Set up →</Link>
  </div>
)}
```

Success: dashboard shows gold banner when pending > 0, setup banner when nothing generated.

---

## TASK 3 — Backend: project status endpoint
**File:** backend/app/routers/projects.py — ADD at the bottom

```python
@router.get("/{project_ref}/status")
async def project_status(project_ref: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from app.models.brand_memory import BrandMemory
    from app.models.project_memory import ProjectMemory as PM
    from app.models.weekly_plan import WeeklyPlan
    from app.models.asset import Asset
    from app.models.approval import Approval

    proj = (await db.execute(select(Project).where(Project.slug == project_ref))).scalar_one_or_none()
    if not proj:
        try:
            from uuid import UUID; UUID(project_ref)
            proj = await db.get(Project, project_ref)
        except Exception:
            pass
    if not proj:
        raise HTTPException(404, "not found")

    pid = proj.id
    bm = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == pid))).scalar_one_or_none()
    plan = (await db.execute(select(WeeklyPlan).where(WeeklyPlan.project_id == pid).order_by(WeeklyPlan.week_start.desc()).limit(1))).scalar_one_or_none()
    pending = await db.scalar(select(func.count(Approval.id)).join(Asset, Asset.id == Approval.asset_id).where(Asset.project_id == pid, Approval.decision.is_(None))) or 0
    published = await db.scalar(select(func.count(Asset.id)).where(Asset.project_id == pid, Asset.status == "published")) or 0

    next_action = (
        "upload_logo" if not (bm and bm.logo_url) else
        "generate_plan" if not plan else
        "approve_plan" if plan.status == "pending_approval" else
        "review_inbox" if pending > 0 else
        "running" if plan.status in ("approved", "executing") else
        "complete"
    )
    return {
        "slug": proj.slug, "name": proj.name,
        "has_logo": bool(bm and bm.logo_url),
        "plan_status": plan.status if plan else None,
        "pending_approvals": pending, "published_assets": published,
        "next_action": next_action,
    }
```

Register: already in router — no main.py change needed since projects_router includes it.

Success: `curl https://backend-production-37a17.up.railway.app/api/projects/therapia/status` → JSON with next_action field.

---

## TASK 4 — Dashboard: live project cards from API
**File:** frontend/app/page.tsx

Replace hardcoded `PROJECTS` array with live fetch:
1. Add state: `const [projectStatuses, setProjectStatuses] = useState<Record<string,ProjectStatus>>({})`
2. On load, fetch `/api/proxy/projects/therapia/status`, `/api/proxy/projects/qawwi/status`, etc. in parallel
3. Map `next_action` to card CTA:
   - `upload_logo` → "Upload Logo →" → /projects/{slug}
   - `generate_plan` → "Generate Plan →" → /projects/{slug}  
   - `approve_plan` → "Approve Plan →" (gold, prominent) → /projects/{slug}
   - `review_inbox` → "Review Inbox (N) →" (gold) → /inbox
   - `running` → "Generating..." (spinner, disabled)
   - `complete` → "View Project →" → /projects/{slug}

Do NOT change the card layout — just replace the static button with the dynamic CTA.

Success: Each project card shows the correct next action based on real DB state.

---

## TASK 5 — Mobile 375px audit — fix only what's broken
Open each route in Playwright at 375px. List ONLY broken things, fix ONLY those.

Check list per route:
- `/` — does TodaysFocus banner wrap cleanly?
- `/projects/therapia` — do 4 tabs fit? If not: make tab bar scroll-x or reduce label size to text-xs
- `/inbox` — are approve/reject buttons full width and ≥56px tall on mobile?
- `/plans/2026-05-12` — does the week header fit on one line?
- `/analytics` — are tiles 1-column on mobile?

Fix ONLY overflow, truncation, or unreadable text. Do NOT redesign anything.

Success: zero horizontal scroll on any route at 375px.

---

## TASK 6 — FetchError component for all data fetches
**File:** frontend/components/ui/FetchError.tsx (CREATE)

```tsx
import { RefreshCw } from 'lucide-react'
import { Card } from './Card'
export function FetchError({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <Card><div className="flex flex-col items-center py-10 gap-3">
      <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.5)]">{message || 'Could not load data'}</p>
      {onRetry && <button onClick={onRetry} className="flex items-center gap-2 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] border border-[rgba(201,168,76,0.25)] px-3 py-2 rounded-xl min-h-[44px] hover:bg-[rgba(201,168,76,0.08)] transition-colors"><RefreshCw size={12}/> Try again</button>}
    </div></Card>
  )
}
```

Add to: inbox, plans/[week], analytics, projects/[id], dashboard — replace bare error strings with `<FetchError message={error} onRetry={reload} />`.

Success: every page shows "Try again" button when backend is unreachable.

---

## COMMIT FORMAT
```
fix(task-1): standardize images through ProjectImage component
fix(task-2): dashboard Today's Focus banner
fix(task-3): project status API endpoint
fix(task-4): dashboard live project cards
fix(task-5): mobile 375px overflow fixes
fix(task-6): FetchError component on all data fetches
```

## RULES FOR CODEX
- Backend tasks: 3 only
- Frontend tasks: 1, 2, 4, 5, 6
- One commit per task after npm run build passes
- Do NOT touch: auth, railway.toml, Dockerfiles, migrations, agent system prompts
- Do NOT add npm packages
- Report: commit hash + PASS/FAIL per task
