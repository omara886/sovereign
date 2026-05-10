# SOVEREIGN V4 — Codex Implementation Prompt
# Read every word. Execute in exact order. No shortcuts.
# These are the 7 highest-leverage fixes identified after v3.

---

## CONTEXT (read before touching anything)

Sovereign is live at:
- Frontend: https://frontend-production-9eea5.up.railway.app
- Backend: https://backend-production-37a17.up.railway.app
- Stack: Next.js 14 App Router + FastAPI + PostgreSQL on Railway

Current state after v3:
- Copy Agent writes Gulf Saudi Arabic (Sonnet model, approved examples seeded)
- Localization Agent runs on Sonnet with Gulf vocabulary rules
- Dashboard shows live stats, first-run banner, project cards with badges
- Inbox has swipe gestures, bulk approve, channel colors, rejection reasons
- Project page has 4 tabs (Assets / Memory / Pipeline / Analytics) + setup progress bar
- Images: small logos = base64 (permanent) / large designs = /tmp serve URL (ephemeral)

What is still broken (Codex analysis after v3):
1. Image handling inconsistent — some pages use raw `<img>` causing warnings, no standard path
2. UI/UX density inconsistent — dashboard, inbox, analytics, project page feel like different products
3. Dashboard too tool-like — doesn't tell Omar what to do next clearly enough
4. Mobile 375px needs full audit — several pages not tested at this size
5. Error states missing on critical flows — when backend is slow, UI shows nothing
6. Agent output validation absent — bad AI output reaches approval inbox undetected
7. State modeling fragmented — project readiness inferred from multiple endpoints

---

## TASK 1 — Standardize all image rendering through one component

**Problem:** `<img>` tags are scattered across 4+ files with different error handling. Build warnings appear. No consistent fallback.

**Create one shared component:** `frontend/components/ui/ProjectImage.tsx`

```tsx
'use client'
import { useState } from 'react'
import { ImageOff } from 'lucide-react'

interface ProjectImageProps {
  url: string | null | undefined
  alt?: string
  className?: string
  fallbackSize?: number
}

function resolveUrl(url: string): string {
  if (url.startsWith('data:')) return url
  if (url.startsWith('file://') || url.includes('railway.app') || url.includes('localhost'))
    return `/api/img?url=${encodeURIComponent(url)}`
  return url
}

export function ProjectImage({ url, alt = '', className = '', fallbackSize = 20 }: ProjectImageProps) {
  const [broken, setBroken] = useState(false)
  const src = url ? resolveUrl(url) : null

  if (!src || broken) {
    return (
      <div className={`flex items-center justify-center bg-[#0A0A0A] border border-[rgba(255,255,255,0.06)] ${className}`}>
        <ImageOff size={fallbackSize} className="text-[rgba(248,246,241,0.1)]" />
      </div>
    )
  }

  // Use <img> with explicit alt. Next.js warns about unoptimized images —
  // we suppress via next.config.ts unoptimized: true for external URLs.
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      className={`object-cover ${className}`}
      onError={() => setBroken(true)}
    />
  )
}
```

**Update `frontend/next.config.ts`** to suppress the `<img>` warning for data URLs and external images:
```ts
const nextConfig = {
  images: {
    unoptimized: true,
  },
  eslint: {
    // We handle image optimization ourselves via ProjectImage component
    ignoreDuringBuilds: false,
  },
}
export default nextConfig
```

**Replace ALL occurrences** of `<img src=...>` and `<Thumb ...>` and `<ProjectAssetThumb ...>` across these files with `<ProjectImage>`:
- `frontend/app/inbox/page.tsx` — thumbnail in card + modal preview
- `frontend/app/projects/[id]/page.tsx` — uploaded assets grid
- `frontend/app/analytics/page.tsx` — asset thumbnails
- `frontend/app/page.tsx` — weekly summary top_asset_url

Do a global search: `grep -rn "<img " frontend/app/ frontend/components/` — every result must be replaced or suppressed.

**Success test:** `npm run build` — zero `no-img-element` warnings in output. Every image shows either the image OR a clean `ImageOff` icon — never a broken `?` icon.

---

## TASK 2 — Dashboard: operational journey, not a tools grid

**Problem:** Dashboard shows 4 stat tiles + 4 project cards. It doesn't answer "what should Omar do right now?"

**File:** `frontend/app/page.tsx`

**Add a "Today's Focus" section** that replaces the current stats row for new users. Shows the single most important action:

```tsx
function TodaysFocus({ pendingApprovals, totalGenerated, loading }: {
  pendingApprovals: number; totalGenerated: number; loading: boolean
}) {
  if (loading) return null

  // Priority 1: pending approvals need action
  if (pendingApprovals > 0) return (
    <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(201,168,76,0.08)] border border-[rgba(201,168,76,0.2)]">
      <div className="w-10 h-10 rounded-full bg-[#C9A84C] text-[#0A0A0A] font-bold text-sm flex items-center justify-center shrink-0">
        {pendingApprovals}
      </div>
      <div className="flex-1">
        <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">
          {pendingApprovals} asset{pendingApprovals > 1 ? 's' : ''} waiting for your approval
        </p>
        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">
          Review and approve to schedule publishing
        </p>
      </div>
      <Link href="/inbox" className="shrink-0 font-['IBM_Plex_Sans'] text-sm font-bold text-[#0A0A0A] bg-[#C9A84C] px-4 py-2 rounded-xl min-h-[44px] flex items-center hover:bg-[#E8C97A] transition-colors">
        Review →
      </Link>
    </div>
  )

  // Priority 2: nothing generated yet — guide to first action
  if (totalGenerated === 0) return (
    <div className="mb-6 flex items-center gap-4 px-5 py-4 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.07)]">
      <div className="w-10 h-10 rounded-full bg-[rgba(201,168,76,0.15)] border border-[rgba(201,168,76,0.3)] text-[#C9A84C] font-bold text-sm flex items-center justify-center shrink-0">1</div>
      <div className="flex-1">
        <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1]">Start with Therapia</p>
        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.45)] mt-0.5">Upload logo → generate plan → approve → publishes automatically</p>
      </div>
      <Link href="/projects/therapia" className="shrink-0 font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] px-4 py-2 rounded-xl min-h-[44px] flex items-center hover:bg-[rgba(201,168,76,0.08)] transition-colors">
        Set up →
      </Link>
    </div>
  )

  // All good — system is running
  return (
    <div className="mb-6 flex items-center gap-3 px-5 py-3 rounded-xl bg-[rgba(16,185,129,0.06)] border border-[rgba(16,185,129,0.15)]">
      <div className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
      <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.6)]">
        System running — next plan generates Monday 8AM Riyadh
      </p>
    </div>
  )
}
```

**Place `<TodaysFocus>` at the very top of the page content**, before the stats row. It is the first thing Omar sees.

**Also update the stats row** — collapse to 2 stats on mobile (most important only):
```tsx
// Mobile: show only "Pending Approvals" and "Published" (2 cols)
// Desktop: show all 4
<div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
```

**Success test:** 
- When `pending_approvals > 0` → gold banner with count + "Review →" appears at top
- When `total_assets_generated === 0` → "Start with Therapia" banner appears
- When everything fine → green pulse dot appears

---

## TASK 3 — Full 375px mobile audit across all routes

**Test every route at 375px.** Fix every issue found.

**Method:** For each page, check:
1. No horizontal scroll (`overflow-x: hidden` on body — already set, but verify)
2. Content visible above bottom tab bar (72px clearance)
3. All tap targets ≥ 44px
4. Text not truncated or overlapping
5. Cards don't clip

**Routes to audit:**
- `/` Dashboard
- `/projects` Project list
- `/projects/therapia` — all 4 tabs (Assets, Memory, Pipeline, Analytics)
- `/inbox` with cards
- `/plans/2026-05-12` Week view
- `/analytics`
- `/settings`

**Common fixes needed:**
1. Project page tabs — on 375px, 4 tabs with text overflow → tabs should scroll horizontally or use smaller text
2. Memory tab — `funnel_goals` table may overflow → add `overflow-x: auto` wrapper
3. Plans page — project plan sections may be too wide → ensure `max-w-3xl mx-auto px-4`
4. Analytics page — 3-column grid on mobile is too cramped → change to 1-col on mobile:
   ```tsx
   <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
   ```

**Success test:** Open each route on a 375px viewport. Zero horizontal scroll. All content readable. All buttons tappable.

---

## TASK 4 — Error states on all critical fetches

**Problem:** When backend is slow or down, pages show nothing — no spinner, no error, no retry button.

**Add a reusable error component:** `frontend/components/ui/FetchError.tsx`

```tsx
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
          <button onClick={onRetry}
            className="flex items-center gap-2 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] border border-[rgba(201,168,76,0.25)] px-3 py-2 rounded-xl hover:bg-[rgba(201,168,76,0.08)] transition-colors min-h-[44px]">
            <RefreshCw size={12} /> Try again
          </button>
        )}
      </div>
    </Card>
  )
}
```

**Add `<FetchError>` to these pages** wherever there is currently a bare error string or empty div:
- `frontend/app/inbox/page.tsx` — when fetch fails
- `frontend/app/projects/[id]/page.tsx` — when plan fetch fails, when uploads fail
- `frontend/app/plans/[week]/page.tsx` — when plans fetch fails
- `frontend/app/analytics/page.tsx` — when summary fetch fails
- `frontend/app/page.tsx` — when metrics fetch fails

Pattern:
```tsx
{error && <FetchError message={error} onRetry={fetchData} />}
```

**Success test:** Temporarily point API to wrong URL → every page shows "Could not load data" + "Try again" button instead of blank page.

---

## TASK 5 — Agent output validation: reject bad outputs before inbox

**Problem:** If an agent produces output with forbidden words, empty copy, or very short content, it still goes to the approval inbox. Omar then has to reject it manually.

**File:** `backend/app/agents/qa.py`

**Add validation rules to QA Agent system prompt:**
```python
# Add to POLICY QA section:
COPY_VALIDATION = """
COPY VALIDATION (blocks before approval inbox):
- copy_ar must be ≥ 30 characters (not empty or placeholder)
- copy_en must be ≥ 30 characters (not empty or placeholder)
- copy_ar must NOT contain: يا صديقي, حبيبي, ازيك, تفضّل, عزيزي المستخدم
- copy_ar must NOT contain any word from project constraints.excluded_topics
- copy_en must NOT contain: unlock, leverage, empower, discover the power, journey to, revolutionize
- copy_en must NOT start with: Are you, Do you, Have you, Discover, Unlock
- CTA must NOT be generic: "Click here", "Learn more", "اضغط هنا", "اعرف أكثر"
If ANY of these fail: qa_score = 0, qa_passed = False, required_fixes lists the specific violation.
"""
```

**Also add to `backend/app/routers/pipeline.py`** — validate copy before creating asset:
```python
def _validate_copy(copy_ar: str, copy_en: str) -> list[str]:
    """Quick pre-QA validation. Returns list of issues (empty = ok)."""
    issues = []
    if len(copy_ar.strip()) < 30:
        issues.append("Arabic copy too short or empty")
    if len(copy_en.strip()) < 30:
        issues.append("English copy too short or empty")
    forbidden_ar = ["يا صديقي", "حبيبي", "ازيك", "تفضّل"]
    forbidden_en = ["unlock the", "leverage", "revolutionize", "Are you tired", "Do you want"]
    for f in forbidden_ar:
        if f in copy_ar:
            issues.append(f"Forbidden Arabic phrase: {f}")
    for f in forbidden_en:
        if f.lower() in copy_en.lower():
            issues.append(f"Forbidden English phrase: {f}")
    return issues
```

Call `_validate_copy()` after Copy Agent generates, before Design Agent runs. If issues found, skip the asset and log the rejection.

**Success test:** Feed the QA Agent a copy with "يا صديقي" → qa_score = 0, qa_passed = False, required_fixes lists "Forbidden Arabic phrase: يا صديقي".

---

## TASK 6 — Single project status endpoint

**Problem:** Frontend infers project readiness from 3+ different endpoints (uploads, memory, plans, approvals). This causes race conditions and inconsistent UI.

**Add to `backend/app/routers/projects.py`:**

```python
@router.get("/{project_ref}/status")
async def get_project_status(project_ref: str, db: AsyncSession = Depends(get_db)):
    """Single endpoint that aggregates project readiness state."""
    from sqlalchemy import func
    from app.models.brand_memory import BrandMemory
    from app.models.project_memory import ProjectMemory
    from app.models.weekly_plan import WeeklyPlan
    from app.models.asset import Asset
    from app.models.approval import Approval

    # Resolve project
    project = (await db.execute(select(Project).where(Project.slug == project_ref))).scalar_one_or_none()
    if not project:
        # Try as UUID
        try:
            from uuid import UUID
            project = await db.get(Project, project_ref)
        except Exception:
            pass
    if not project:
        raise HTTPException(404, "project not found")

    pid = project.id

    # Parallel counts
    has_brand = bool((await db.execute(select(BrandMemory).where(BrandMemory.project_id == pid))).scalar_one_or_none())
    has_uploads = False
    if has_brand:
        bm = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == pid))).scalar_one()
        has_uploads = bool(bm.logo_url)

    latest_plan = (await db.execute(
        select(WeeklyPlan).where(WeeklyPlan.project_id == pid).order_by(WeeklyPlan.week_start.desc()).limit(1)
    )).scalar_one_or_none()

    pending_approvals = await db.scalar(
        select(func.count(Approval.id))
        .join(Asset, Asset.id == Approval.asset_id)
        .where(Asset.project_id == pid, Approval.decision.is_(None))
    ) or 0

    published = await db.scalar(
        select(func.count(Asset.id)).where(Asset.project_id == pid, Asset.status == "published")
    ) or 0

    return {
        "project_id": str(pid),
        "slug": project.slug,
        "name": project.name,
        "has_logo": has_uploads,
        "has_plan": latest_plan is not None,
        "plan_status": latest_plan.status if latest_plan else None,
        "plan_id": str(latest_plan.id) if latest_plan else None,
        "pending_approvals": pending_approvals,
        "published_assets": published,
        # What should the user do next?
        "next_action": (
            "upload_logo" if not has_uploads else
            "generate_plan" if not latest_plan else
            "approve_plan" if latest_plan and latest_plan.status == "pending_approval" else
            "review_inbox" if pending_approvals > 0 else
            "running" if latest_plan and latest_plan.status in ("approved", "executing") else
            "complete"
        ),
    }
```

**Use this in the frontend** on the dashboard and project page instead of inferring from multiple calls:
```tsx
// In app/page.tsx — for each project card, fetch /api/proxy/projects/{slug}/status
// Replace the hardcoded PROJECTS array with live data
// Show next_action as the primary CTA on each card
```

Project card CTA mapping:
```tsx
const ACTION_LABELS: Record<string, { label: string; href: string; variant: 'primary' | 'ghost' }> = {
  upload_logo:    { label: 'Upload Logo →',      href: `/projects/{slug}`,         variant: 'ghost' },
  generate_plan:  { label: 'Generate Plan →',    href: `/projects/{slug}?tab=pipeline`, variant: 'ghost' },
  approve_plan:   { label: 'Approve Plan →',     href: `/projects/{slug}?tab=pipeline`, variant: 'primary' },
  review_inbox:   { label: 'Review Inbox ({n})', href: '/inbox',                   variant: 'primary' },
  running:        { label: 'Generating...',       href: `/projects/{slug}`,         variant: 'ghost' },
  complete:       { label: 'View Project →',      href: `/projects/{slug}`,         variant: 'ghost' },
}
```

**Success test:** `curl https://backend-production-37a17.up.railway.app/api/projects/therapia/status` → returns JSON with `next_action` field.

---

## TASK 7 — UI consistency pass: one visual system

**Problem:** Dashboard cards, inbox cards, project page, and analytics all have slightly different spacing, font sizes, and border radii. They feel like different products.

**The standard (enforce on every card and section):**
```
Card outer: rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.08)] to-transparent border border-[rgba(201,168,76,0.12)]
Card inner: rounded-[18px] bg-[#1E293B] p-4 md:p-6
Section heading: font-['Cormorant_Garamond'] text-2xl text-[#F8F6F1]
Sub-heading: font-['IBM_Plex_Sans'] text-xs font-semibold uppercase tracking-wider text-[rgba(248,246,241,0.4)]
Body text: font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.7)]
Data/numbers: font-['IBM_Plex_Mono'] text-[#F8F6F1]
Gold accent: text-[#C9A84C] or bg-[#C9A84C]
Page top padding: pt-12 (consistent on all pages)
Section spacing: mb-6 between major sections
```

**Audit and fix these files:**
1. `frontend/app/analytics/page.tsx` — metric tiles use ad-hoc styles, not Card component
2. `frontend/app/plans/[week]/page.tsx` — plan cards may use different border style
3. `frontend/app/settings/page.tsx` — verify consistent with the rest
4. `frontend/app/projects/[id]/page.tsx` — Memory tab row styling is ad-hoc
5. `frontend/app/page.tsx` — weekly summary card at bottom

For each file: replace inline `bg-[rgba(255,255,255,0.03)]` border styles with the standard Card component.

---

## COMMIT FORMAT

```
fix(task-1): standardize all images through ProjectImage component
fix(task-2): dashboard shows Today's Focus with pending approval CTA
fix(task-3): full 375px mobile audit — all routes pass
fix(task-4): FetchError component on all data fetches with retry button  
fix(task-5): copy validation blocks forbidden phrases before inbox
fix(task-6): /api/projects/{slug}/status endpoint + dashboard live project cards
fix(task-7): visual system consistency pass across all pages
```

---

## SUCCESS CRITERIA — THE REAL TEST

1. Open site on iPhone 375px. Zero horizontal scroll. All pages readable.
2. `npm run build` — zero TypeScript errors, zero `no-img-element` warnings.
3. Dashboard → if there are pending approvals, gold banner is the FIRST thing visible.
4. Dashboard → project cards show the correct next action for each project.
5. All empty states have a "Try again" or "Do this next" button.
6. Run pipeline → if Arabic output contains "يا صديقي" → QA blocks it, does not reach inbox.
7. `curl /api/projects/therapia/status` → returns `next_action` field.
8. All cards across all pages use the same double-bezel Card component style.

---

## FOR CODEX — RULES

- Backend tasks: 1 (ProjectImage is frontend, skip), 5 (QA validation), 6 (status endpoint) = Tasks 5 and 6
- Frontend tasks: 1, 2, 3, 4, 7 = Tasks 1, 2, 3, 4, 7
- Do NOT change database schema or run migrations.
- Do NOT modify auth, railway.toml, or Dockerfiles.
- Do NOT add new npm packages without checking bundle impact first.
- After EVERY step: run `npm run build` (frontend) or `python -c "from app.routers.projects import router"` (backend). Zero errors before commit.
- Task 3 (mobile audit) requires manually reviewing each route at 375px viewport in Playwright — do not skip this.
