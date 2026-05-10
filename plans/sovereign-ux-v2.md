# Sovereign UX v2 — Blueprint
# Generated: 2026-05-10
# 5 sprints, 14 steps, direct-mode (no branching needed — single dev)

---

## INVARIANTS (check after every step)
- [ ] `npm run build` passes zero TypeScript errors
- [ ] No `console.log` in committed code
- [ ] All routes return 200 (no 404s)
- [ ] Mobile 375px: no horizontal scroll, content visible above tab bar
- [ ] Design: dark #0A0A0A, gold #C9A84C, double-bezel cards, IBM Plex Sans/Cairo/Cormorant

---

## DEPENDENCY GRAPH

```
Step 1 (backend: plan API) → Step 2 (frontend: Pipeline tab plan view)
Step 2 → Step 3 (plan approval flow)
Step 3 → Step 4 (full week view /plans/[week])
Step 4 → Step 5 (post-approval asset status)
Step 5 → Step 6 (bulk approve)
Step 6 → Step 7 (live dashboard stats)
Step 7 → Step 8 (swipe gestures)
Step 8 → Step 9 (inbox badge count)
Step 9 → Step 10 (analytics tab real data)
Step 10 → Step 11 (asset performance metrics)
Step 11 → Step 12 (weekly summary report)

Step 1 and Step 7 can run in parallel (independent).
Steps 8, 9 can run in parallel after Step 7.
```

---

## SPRINT 1 — Plan Visibility

### Step 1 — Backend: plans API accepts project slug + returns current week plan

**Context:** The `/api/plans` endpoint currently only accepts `project_id` (UUID). The frontend needs to query by slug. Also need an endpoint to get the current week's plan specifically.

**Files to touch:**
- `backend/app/routers/plans.py`

**Tasks:**
1. Update `GET /api/plans` to accept `project_slug` query param in addition to `project_id`
   - Look up project by slug → get UUID → query plans
2. Add `GET /api/plans/current/{project_slug}` — returns the most recent plan for this week or last plan created
3. Ensure plan response includes all `tactics` JSONB data (not truncated)

**Implementation:**
```python
@router.get("/plans/current/{project_slug}")
async def get_current_plan(project_slug: str, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "project not found")
    plan = (await db.execute(
        select(WeeklyPlan)
        .where(WeeklyPlan.project_id == project.id)
        .order_by(WeeklyPlan.week_start.desc())
        .limit(1)
    )).scalar_one_or_none()
    return plan  # 404 if no plan yet
```

**Verification:** `curl https://backend-production-37a17.up.railway.app/api/plans/current/therapia` → returns plan JSON or 404

---

### Step 2 — Frontend: Pipeline tab shows current plan

**Context:** Project page `/projects/[id]` has a Pipeline tab with only two buttons. It should show the current week's plan when one exists.

**Files to touch:**
- `frontend/app/projects/[id]/page.tsx`

**Tasks:**
1. In the Pipeline tab, fetch `GET /api/proxy/plans/current/{slug}` on tab open
2. If plan exists, show:
   - Objective (large text, prominent)
   - Funnel focus badge (awareness/consideration/conversion/retention)
   - Rationale (2-3 sentence explanation)
   - Tactics list: each tactic shows channel, asset_type, rationale_simple, budget_estimate_sar
   - Status badge: draft / pending_approval / approved / executing / done
   - Risk flags (yellow warning list if any)
3. If status=`pending_approval`: show prominent "Approve Plan" button
4. If status=`draft`: show "Plan ready — approve to start generating"
5. If status=`approved` or `executing`: show "Generating assets..." with asset count
6. If no plan: show the existing generate buttons (current behavior)

**Key component to add:**
```tsx
function PlanView({ plan }: { plan: Plan }) {
  return (
    <div>
      <h2>{plan.objective}</h2>
      <Badge>{plan.funnel_focus}</Badge>
      <p>{plan.rationale}</p>
      {plan.tactics.map(t => <TacticRow key={t.id} tactic={t} />)}
      {plan.status === 'pending_approval' && <ApprovePlanButton planId={plan.id} />}
    </div>
  )
}
```

**Verification:** Navigate to /projects/therapia → Pipeline tab → plan displays if one exists, buttons show if none

---

### Step 3 — Frontend: Plan approval flow inline

**Context:** When Omar approves a plan from the Pipeline tab, the system should start generating assets and show progress inline — no need to navigate away.

**Files to touch:**
- `frontend/app/projects/[id]/page.tsx`
- `frontend/app/api/proxy/[...path]/route.ts` (already working)

**Tasks:**
1. "Approve Plan" button calls `POST /api/proxy/approvals` with `weekly_plan_id`
2. After approval, immediately show status: "Generating copy and designs for [N] tactics..."
3. Poll `GET /api/proxy/approvals?project_id=...&status=pending` every 5s
4. When assets appear in approvals, show: "N assets ready for review → Go to Inbox"
5. Show spinner while generating (can take 2-3 min)

**Verification:** Approve a plan → see "Generating..." → eventually see "3 assets ready → Go to Inbox"

---

## SPRINT 2 — Full Week View

### Step 4 — Frontend: /plans/[week] real implementation

**Context:** `/plans/[week]` currently returns a stub page. Implement it as a full cross-project week view.

**Files to touch:**
- `frontend/app/plans/[week]/page.tsx`

**Tasks:**
1. Fetch all plans for the given week: `GET /api/proxy/plans?week_start={week}`
2. Show one section per project (Therapia, Qawwi, etc.)
3. Each section: project name, plan status, objective, tactic count, budget
4. Budget summary footer: total SAR planned across all projects
5. Empty state if no plans exist for that week: "No plans generated yet — run Weekly Plan from the dashboard"
6. Week navigation: ← previous week / next week →

**URL format:** `/plans/2026-05-11` (ISO date of Monday)

**Sidebar nav "Plans" link:** Update to `/plans/2026-05-11` (current week's Monday)

**Verification:** Navigate to /plans/2026-05-11 → sees Therapia plan with correct data

---

## SPRINT 3 — Asset Approval Flow Polish

### Step 5 — Frontend: Post-approval confirmation + publish status

**Context:** After Omar approves an asset in inbox, the card disappears with no feedback. He needs to know it's scheduled for publishing.

**Files to touch:**
- `frontend/app/inbox/page.tsx`

**Tasks:**
1. After successful approve API call, show a toast/banner: "✅ Approved — scheduled for publish"
2. Toast fades after 3 seconds
3. After successful reject with reason, show: "Feedback saved — the AI will avoid this pattern next time"
4. Add `GET /api/proxy/publish-jobs?project_id=...` call to show publish job statuses in a separate "Published" section below the pending list

**Implementation of toast:**
```tsx
const [toast, setToast] = useState<{msg: string; color: string} | null>(null)
// After approve:
setToast({ msg: '✅ Approved — scheduled for publish', color: 'success' })
setTimeout(() => setToast(null), 3000)
```

**Verification:** Approve asset → green toast shows → disappears → reject with reason → "Feedback saved" toast shows

---

### Step 6 — Frontend: Bulk approve button

**Context:** When many assets need approval, Omar wants to approve all at once.

**Files to touch:**
- `frontend/app/inbox/page.tsx`

**Tasks:**
1. When pending.length > 1, show "Approve All ([N])" button at top of inbox
2. Calls approve() sequentially for each pending approval
3. Shows "Approving 1/3... 2/3... 3/3..." progress
4. Final toast: "All [N] assets approved and scheduled"

**Verification:** Generate pipeline → inbox has 2+ items → "Approve All (2)" button visible → tapping it approves all

---

## SPRINT 4 — Mobile Polish

### Step 7 — Frontend: Dashboard live stats from API

**Context:** Dashboard shows hardcoded 0s for all stats. Fetch real numbers.

**Files to touch:**
- `frontend/app/page.tsx`

**Backend prerequisite:** `GET /api/metrics/summary` already exists (built in task 4 previously) — returns `published_assets`, `pending_approvals`, `total_assets_generated`

**Tasks:**
1. On dashboard load, fetch `GET /api/proxy/metrics/summary`
2. Update stats tiles: Pending Approvals, Published This Week, Total Assets
3. Active Projects stays at 4 (static — correct)
4. Loading skeleton while fetching (replace CountUp with a small spinner until data arrives)
5. Refresh stats every 60 seconds

**Verification:** Dashboard → stats show real numbers (e.g., pending_approvals matches inbox count)

---

### Step 8 — Frontend: Swipe gestures on inbox cards (mobile)

**Context:** On mobile, Tinder-style swipe is more natural than tapping Approve/Reject.

**Files to touch:**
- `frontend/app/inbox/page.tsx`
- `frontend/components/inbox/SwipeActions.tsx` (create)

**Tasks:**
1. Wrap each approval card in a swipeable container using CSS transforms (no new packages — use pointer events)
2. Swipe right (>100px) → green overlay → approve on release
3. Swipe left (>100px) → red overlay → open rejection reason modal on release
4. Desktop: unchanged (buttons still work)
5. Visual indicator: ✅ appears on right during right-swipe, ✗ appears on left during left-swipe

**Implementation — no new packages:**
```tsx
// Use onPointerDown/onPointerMove/onPointerUp
// Track deltaX, apply CSS transform translateX
// On release: if |deltaX| > 100, trigger action
```

**Verification:** Mobile 375px viewport — swipe right → card approved, swipe left → rejection modal opens

---

### Step 9 — Frontend: Inbox badge count on tab bar

**Context:** Bottom tab bar shows "Inbox" with no count. Omar needs to know at a glance how many approvals are pending.

**Files to touch:**
- `frontend/components/ui/Sidebar.tsx`

**Tasks:**
1. On mount, fetch `GET /api/proxy/approvals?status=pending` count
2. Show badge on Inbox tab item: red circle with count
3. Badge disappears when count is 0
4. Refresh every 30 seconds
5. Must work on both desktop sidebar and mobile bottom tab

**Implementation:**
```tsx
// In Sidebar, add state: const [pendingCount, setPendingCount] = useState(0)
// useEffect: fetch /api/proxy/approvals?status=pending, set count from data.length
// On Inbox nav item: show <span className="badge">{pendingCount}</span> when > 0
```

**Verification:** Generate and approve plan → inbox fills → badge shows count on tab, clears when inbox emptied

---

## SPRINT 5 — Post-Publish Analytics Loop

### Step 10 — Backend: asset-level metrics endpoint

**Context:** After publishing, we need to show per-asset metrics pulled from social APIs.

**Files to touch:**
- `backend/app/routers/analytics.py`

**Tasks:**
1. Add `GET /api/metrics/assets?project_id={id}&limit=20` — returns recent published assets with any stored metric snapshots
2. Join `assets` with `metric_snapshots` on `asset_id`
3. Return: asset_id, channel, type, published_at, platform_post_id, metrics: {impressions, clicks, engagement_rate}

**Note:** Metrics only appear if the Analytics Agent has run (Sunday 6PM). Initial response will show 0s for new publishes.

**Verification:** `curl /api/metrics/assets?project_id=...` returns array (may be empty if no metrics yet)

---

### Step 11 — Frontend: Project Analytics tab with asset performance

**Context:** Project page → Analytics tab (currently missing from project page). The standalone /analytics route exists but doesn't show per-asset data.

**Files to touch:**
- `frontend/app/projects/[id]/page.tsx` — add Analytics tab to TABS array
- Analytics tab content: fetch and display published assets + metrics

**Tasks:**
1. Add "Analytics" to TABS: `['Assets', 'Memory', 'Pipeline', 'Analytics']`
2. Analytics tab fetches `GET /api/proxy/metrics/assets?project_slug={slug}` (backend resolves slug to ID)
3. Show published assets list: thumbnail, channel, published date, metrics
4. If no metrics yet: "Analytics update every Sunday 6PM. Check back after first publish."
5. Show top performer highlight card

**Verification:** /projects/therapia → Analytics tab → shows published assets list (or empty state if none published)

---

### Step 12 — Frontend: Weekly summary card on dashboard

**Context:** After the Analytics Agent runs (Sunday), the report should be visible on the dashboard as a summary card.

**Files to touch:**
- `frontend/app/page.tsx`
- `backend/app/routers/analytics.py` — add `GET /api/metrics/weekly-summary`

**Backend task:**
```python
@router.get("/metrics/weekly-summary")
async def weekly_summary(db: AsyncSession = Depends(get_db)):
    # Get latest performance_learnings from all active project memories
    # Return: {projects: [{name, learnings, top_asset_url}]}
```

**Frontend task:**
1. Fetch weekly summary on dashboard load
2. Show "This Week's Insights" card at bottom of dashboard (only when data exists)
3. Per project: 2-3 bullet learning points from performance_learnings field
4. "Best asset" thumbnail if available

**Verification:** After Analytics Agent runs — dashboard shows insight card with learnings

---

## EXECUTION ORDER FOR CODEX

Run in this order (sequential):
1. Step 1 (backend plans API)
2. Step 2 (Pipeline tab plan view)
3. Step 3 (plan approval inline)
4. Step 7 (live dashboard stats) ← can do in parallel with 1-3
5. Step 4 (/plans/[week] page)
6. Step 5 (post-approval toast)
7. Step 6 (bulk approve)
8. Step 8 (swipe gestures) ← parallel with 9
9. Step 9 (inbox badge count) ← parallel with 8
10. Step 10 (backend metrics endpoint)
11. Step 11 (project analytics tab)
12. Step 12 (weekly summary card)

**Parallel opportunities:**
- Steps 1+7 can run simultaneously
- Steps 8+9 can run simultaneously
- Steps 10+11 can run simultaneously

---

## SUCCESS CRITERIA (the real test)

Omar opens Sovereign on his iPhone:

1. Taps Dashboard → sees real pending approval count (not 0)
2. Taps "Weekly Plan" on Therapia → status bar shows → navigates away → comes back → still showing
3. Goes to /projects/therapia → Pipeline tab → **sees the generated plan with tactics and objective** (not just buttons)
4. Taps "Approve Plan" → sees "Generating assets..." inline
5. Goes to Inbox → badge on tab shows count → swipes right to approve → "✅ Scheduled" toast
6. Opens /plans/2026-05-11 → sees all 4 projects' plans for the week
7. Goes to /projects/therapia → Analytics tab → sees published asset with placeholder metrics

---

## ANTI-PATTERNS TO AVOID

- DO NOT add loading spinners that never resolve — always add timeout fallbacks
- DO NOT use hardcoded project IDs or UUIDs — always resolve from slug
- DO NOT build swipe gestures with a new library — use pointer events
- DO NOT break existing routes — test all 12 routes after each step
- DO NOT commit without passing `npm run build`
- DO NOT leave empty tabs — every tab must show either data or a meaningful empty state
