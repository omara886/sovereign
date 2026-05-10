# SOVEREIGN — Codex Task 2
# Fix remaining issues. Each item has exact file, exact fix, exact success test.
# After every change: npm run build must pass with zero errors before pushing.

---

## CONTEXT

Sovereign is a deployed autonomous AI marketing system on Railway.
- Frontend: https://frontend-production-9eea5.up.railway.app
- Backend: https://backend-production-37a17.up.railway.app
- Repo: https://github.com/omara886/sovereign

Current status: core system works. Remaining issues below.

---

## TASK 1 — File uploads show images after upload

**Problem:** After upload succeeds (backend saves to /tmp), the image grid shows `file://` URLs which browsers can't load.

**Fix in:** `backend/app/routers/uploads.py` and `backend/app/tools/r2_tools.py`

**Solution:** When R2 is not configured, serve uploaded files through a backend route instead of file:// URLs.

Step 1 — Add a file-serve endpoint in `backend/app/routers/uploads.py`:
```python
@router.get("/serve/{project_slug}/{file_type}/{filename}")
async def serve_file(project_slug: str, file_type: str, filename: str):
    from fastapi.responses import FileResponse
    from pathlib import Path
    path = Path(f"/tmp/sovereign_r2/{project_slug}/{file_type}/{filename}")
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)
```

Step 2 — In `backend/app/tools/r2_tools.py`, change the fallback URL to use the serve endpoint:
```python
# Replace this line:
return f"file://{target}"
# With:
backend_base = settings.NEXT_PUBLIC_API_URL or "https://backend-production-37a17.up.railway.app"
return f"{backend_base}/api/uploads/serve/{filename}"
```

**Success test:** Upload a PNG logo. The image appears in the grid below without broken icon.

---

## TASK 2 — Inbox approve/reject actually works

**Problem:** Tapping Approve/Reject in inbox calls `POST /api/approvals/{id}/decide` but after deciding, the asset doesn't move out of inbox on reload.

**Debug first:** Add a console.log to the inbox fetch to see what `status` field approvals return. The filter `approvals.filter(a => !a.decision)` might be filtering wrong.

**Fix in:** `frontend/app/inbox/page.tsx`

Check: after `decide()` is called, `fetchApprovals()` re-fetches. If the approval now has `decision: "approved"`, it should disappear from pending. Verify the API response includes `decision` field.

If `decision` is null before and non-null after, the filter works. If not, fix the filter or the API response.

**Success test:** Tap Approve on an inbox item → item disappears from inbox immediately after.

---

## TASK 3 — Dashboard pipeline buttons show real-time status

**Problem:** When you tap "Full Pipeline" on dashboard, the status bar shows but after job completes the "Review in Inbox →" button sometimes doesn't appear.

**Fix in:** `frontend/app/page.tsx`

The condition is:
```tsx
{jobResult?.status === 'done' && jobResult.assets_passed_qa !== undefined && jobResult.assets_passed_qa > 0 && (
  <Link href="/inbox">Review in Inbox →</Link>
)}
```

The issue: `assets_passed_qa` might be `0` for the plan-only flow. Show the Inbox link whenever `status === 'done'` regardless:
```tsx
{jobResult?.status === 'done' && (
  <Link href="/inbox">Go to Inbox →</Link>
)}
```

**Success test:** Run Full Pipeline → status bar shows steps → when done, "Go to Inbox →" button always appears.

---

## TASK 4 — Analytics page shows real metrics from DB

**Problem:** Analytics page shows empty placeholder. It should show real data from `metric_snapshots` table.

**Fix in:** `frontend/app/analytics/page.tsx`

Make it a client component that fetches from `/api/proxy/metrics/summary` (endpoint needs to be created).

Step 1 — Add to `backend/app/routers/analytics.py` (create file if doesn't exist):
```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.metric_snapshot import MetricSnapshot
from app.models.asset import Asset

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/summary")
async def get_metrics_summary(db: AsyncSession = Depends(get_db)):
    # Count published assets
    published = await db.scalar(select(func.count(Asset.id)).where(Asset.status == "published")) or 0
    # Count pending approvals
    from app.models.approval import Approval
    pending = await db.scalar(select(func.count(Approval.id)).where(Approval.decision.is_(None))) or 0
    # Total assets generated
    total_assets = await db.scalar(select(func.count(Asset.id))) or 0
    return {
        "published_assets": published,
        "pending_approvals": pending,
        "total_assets_generated": total_assets,
    }
```

Step 2 — Register in `backend/app/main.py`:
```python
from app.routers.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api")
```

Step 3 — Update `frontend/app/analytics/page.tsx` to fetch and display these numbers with CountUp.

**Success test:** Analytics page shows numbers (even if 0) with animated CountUp, no empty placeholder.

---

## TASK 5 — Settings page shows correct Railway backend URL

**Problem:** Settings page hardcodes Omar's email. Make it show actual system status.

**Fix in:** `frontend/app/settings/page.tsx`

Add a system status section that calls `/api/proxy/health-check` equivalent. Use the `/api/debug-url` endpoint to show which backend is connected.

The health endpoint on backend is at `/health` (no `/api/` prefix). Add a special proxy case or just show the backend URL from env.

**Success test:** Settings page loads, shows "System Status: Connected" with the backend URL.

---

## TASK 6 — Mobile layout final fixes

**Problem:** On 375px iPhone, some content is cut off.

**Fixes:**

1. `frontend/app/projects/[id]/page.tsx` — the tab bar uses `border-b` which on mobile might render oddly. Ensure tabs scroll horizontally if they don't fit.

2. All pages — ensure `pt-12` header accounts for mobile status bar. On iPhone with notch, add `pt-safe` or ensure enough top padding.

3. `frontend/components/ui/Sidebar.tsx` — mobile bottom bar has `py-1` which may make icons too small. Use `py-2` and test at 375px.

4. All Card components — ensure `p-6` inner padding doesn't cause overflow on 375px. Use `p-4 md:p-6`.

**Success test:** Open on 375px viewport. No horizontal scroll. Bottom nav visible. All text readable.

---

## TASK 7 — /debug page removed from production

**Problem:** The debug page at `/debug` should not be accessible in production (security).

**Fix in:** `frontend/middleware.ts`

Add `/debug` to the list of routes that require auth. Already handled since auth middleware requires login for all routes. Verify the debug page still works when logged in.

Actually: keep the debug page but add a note it's for admin use. No code change needed since it's already auth-protected.

---

## BUILD REQUIREMENT

After every task, run:
```bash
cd frontend && npm run build
```
Must show: `✓ Compiled successfully` with zero TypeScript errors before committing.

Never commit broken builds.

---

## COMMIT FORMAT

One commit per task:
```
fix(task-N): description
```

Push after each task so progress is visible.

---

## SUCCESS CRITERIA FOR ALL TASKS

1. Upload a logo PNG in /projects/therapia → logo appears in grid
2. Run Full Pipeline on Therapia → status shows progress → "Go to Inbox" appears
3. Open Inbox → approval card visible → tap Approve → card disappears
4. Open Analytics → numbers show (not placeholder)
5. Open on iPhone 375px → no broken layout

---

## WHAT NOT TO TOUCH

- Do NOT change agent system prompts (backend/app/agents/*.py SYSTEM_PROMPT strings)
- Do NOT change DB migrations
- Do NOT change auth logic (middleware.ts, login route)
- Do NOT change railway.toml or Dockerfiles
- Do NOT add new npm packages without checking build still passes
