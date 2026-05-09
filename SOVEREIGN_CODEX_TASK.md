# SOVEREIGN — Codex Implementation Task
# Read SOVEREIGN_SPEC.md first. This file is the execution checklist.
# Zero ambiguity. Zero vagueness. Execute in exact order.

## PRE-FLIGHT CHECKLIST (verify before starting)

- [ ] Read SOVEREIGN_SPEC.md completely (all 7 sections)
- [ ] Verify all env vars in .env (use .env.example as template)
- [ ] PostgreSQL 16 running with pgvector extension available
- [ ] Python 3.12+ installed
- [ ] Node.js 20+ installed
- [ ] Railway CLI installed (for deploy)

---

## PHASE 0: FOUNDATION (Steps 1-5)

### Step 1 — Repo Init
```bash
mkdir -p sovereign/{frontend,backend/app/{models,schemas,routers,agents,tools,services,scheduler},backend/migrations/versions,backend/scripts}
cd sovereign
git init
```
Create files: `.gitignore`, `.env.example`, `railway.toml`
SUCCESS GREP: `ls backend/app/agents/ | wc -l` → 10

### Step 2 — Backend Foundation
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pgvector anthropic fal-client pillow boto3 httpx beautifulsoup4 apscheduler python-telegram-bot resend pydantic-settings
pip freeze > requirements.txt
```
Create: `app/config.py`, `app/database.py`, `app/main.py`
SUCCESS: `uvicorn app.main:app` starts, `curl localhost:8000/docs` returns 200

### Step 3 — SQLAlchemy Models
Create all 10 model files in `app/models/`:
`organization.py`, `project.py`, `project_memory.py`, `brand_memory.py`,
`weekly_plan.py`, `asset.py`, `approval.py`, `publish_job.py`,
`metric_snapshot.py`, `audit_event.py`
SUCCESS: `python -c "from app.models import *"` exits 0

### Step 4 — Alembic Migration
```bash
alembic init migrations
# Configure env.py + alembic.ini
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```
SUCCESS: `psql $DATABASE_URL_SYNC -c "\dt"` lists 10 tables + `vector` extension

### Step 5 — Pydantic Schemas
Create all schema files in `app/schemas/`
SUCCESS: `python -c "from app.schemas import *"` exits 0

---

## PHASE 1: API LAYER (Steps 6-10)

### Step 6 — Projects Router
File: `app/routers/projects.py`
Endpoints:
- `GET /api/projects` → list
- `POST /api/projects` → create
- `GET /api/projects/{id}` → detail
- `PATCH /api/projects/{id}` → update

Register in `app/main.py`: `app.include_router(projects_router, prefix="/api")`
SUCCESS: `curl http://localhost:8000/api/projects` → `[]`

### Step 7 — Memory Router
File: `app/routers/memory.py`, `app/routers/brand.py`
Endpoints:
- `GET /api/projects/{id}/memory`
- `PATCH /api/projects/{id}/memory`
- `GET /api/projects/{id}/brand`
- `PATCH /api/projects/{id}/brand`
- `POST /api/projects/{id}/brand/approve` — sets is_provisional=False
SUCCESS: All return 200 with correct schema

### Step 8 — Plans Router
File: `app/routers/plans.py`
Endpoints:
- `GET /api/plans?project_id=&week_start=`
- `GET /api/plans/{id}`
- `POST /api/plans`
SUCCESS: Plan CRUD round-trip

### Step 9 — Assets Router
File: `app/routers/assets.py`
Endpoints:
- `GET /api/assets?project_id=&status=&channel=`
- `GET /api/assets/{id}`
- `POST /api/assets`
- `PATCH /api/assets/{id}`
SUCCESS: Asset CRUD round-trip

### Step 10 — Approvals Router + Webhook
File: `app/routers/approvals.py`, `app/routers/webhook.py`
Endpoints:
- `POST /api/approvals`
- `GET /api/approvals?project_id=&status=pending`
- `POST /api/approvals/{id}/decide` → triggers approval_service.handle_approval_decision
- `POST /api/webhook/telegram`
SUCCESS: Approve decision → PublishJob created in DB

---

## PHASE 2: AGENT TOOLS (Steps 11-13)

### Step 11 — Memory + Crawl Tools
Files: `app/tools/memory_tools.py`, `app/tools/crawl_tools.py`
Functions:
- `get_project_memory(db, project_id) -> ProjectMemory`
- `update_project_memory(db, project_id, updates) -> ProjectMemory`
- `get_brand_memory(db, project_id) -> BrandMemory`
- `update_brand_memory(db, project_id, updates) -> BrandMemory`
- `crawl_website(url: str) -> dict` — httpx + BeautifulSoup
- `extract_brand_signals(crawl_result: dict) -> dict`
SUCCESS: `crawl_website("https://therapia.live")` returns dict with colors, fonts, tone

### Step 12 — Image + Storage Tools
Files: `app/tools/fal_tools.py`, `app/tools/r2_tools.py`, `app/tools/image_tools.py`
Functions:
- `generate_image_fal(prompt, model, width, height) -> bytes`
- `upload_to_r2(file_bytes, filename, content_type) -> str`
- `get_signed_url(filename, expiry_seconds=3600) -> str`
- `apply_text_overlay(image_bytes, text_ar, text_en, arabic_font_url, config) -> bytes`
- `resize_image(image_bytes, width, height) -> bytes`
- `create_thumbnail(image_bytes, max_size=400) -> bytes`
SUCCESS: Pipeline test → R2 URL returned for a generated+overlaid image

### Step 13 — Notify + Social Tools
Files: `app/tools/notify_tools.py`, `app/tools/social_tools.py`
Functions:
- `send_email_resend(to, subject, html) -> bool`
- `send_telegram_notification(chat_id, text, keyboard=None) -> bool`
- `setup_telegram_webhook(webhook_url) -> bool`
- `publish_to_linkedin(asset, org_id, access_token) -> str`
- `publish_to_instagram(asset, user_id, access_token) -> str`
- `publish_to_twitter(asset, credentials) -> str`
SUCCESS: Test Telegram message received in TELEGRAM_CHAT_ID

---

## PHASE 3: AGENT CORE (Steps 14-20)

### Step 14 — Base Agent
File: `app/agents/base.py`

```python
class BaseAgent:
    MODEL = "claude-sonnet-4-20250514"
    
    def __init__(self, system_prompt: str, tools: list):
        self.client = anthropic.AsyncAnthropic()
        self.system_prompt = system_prompt
        self.tools = tools  # list of tool definitions for Claude
        self.tool_implementations = {}  # name → callable

    async def run(self, user_message: str, db: AsyncSession) -> str:
        messages = [{"role": "user", "content": user_message}]
        
        while True:
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages
            )
            
            if response.stop_reason == "end_turn":
                return response.content[-1].text
            
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        fn = self.tool_implementations[block.name]
                        result = await fn(db=db, **block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
```

SUCCESS: Test agent with a simple echo tool completes loop

### Step 15 — Strategy Agent
File: `app/agents/strategy.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 1
Tools: get_project_memory, get_brand_memory, get_metric_history, get_previous_plans, save_weekly_plan, create_audit_event
SUCCESS: Generates WeeklyPlan with 3+ tactics for Therapia, saved to DB

### Step 16 — Brand Agent
File: `app/agents/brand.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 2
Tools: crawl_website, extract_brand_signals, get_brand_memory, save_brand_memory, update_brand_memory, upload_to_r2, create_approval_request, create_audit_event
SUCCESS: Crawls therapia.live → provisional BrandMemory in DB

### Step 17 — Copy Agent
File: `app/agents/copy.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 3
Tools: get_project_memory, get_brand_memory, get_weekly_plan, get_approved_examples, get_rejected_examples, save_asset, create_audit_event
SUCCESS: Generates asset with copy_ar (Gulf Arabic) + copy_en for Instagram

### Step 18 — Localization Agent
File: `app/agents/localization.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 5
Tools: get_project_memory, get_brand_memory, get_asset, update_asset, check_rtl_rendering, create_audit_event
SUCCESS: Arabic copy passes RTL validation, no فصحى detected

### Step 19 — Design Agent
File: `app/agents/design.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 4
Tools: get_brand_memory, get_asset, generate_image_fal, apply_text_overlay, resize_image, upload_to_r2, create_thumbnail, update_asset, create_audit_event
SUCCESS: design_url + thumbnail_url populated on asset, verify images load from R2

### Step 20 — QA Agent
File: `app/agents/qa.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 6
Tools: get_brand_memory, get_asset, get_rejected_examples, analyze_image_colors, check_rtl_rendering, check_text_contrast, update_asset, create_audit_event
SUCCESS: qa_score populated, checks array has 12+ entries, pass/fail correct

---

## PHASE 4: PUBLISHING PIPELINE (Steps 21-24)

### Step 21 — Approval Agent
File: `app/agents/approval_agent.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 7
Tools: get_qa_passed_assets, create_approval_record, send_email_resend, send_telegram_notification, update_asset_status, create_audit_event
SUCCESS: Email received + Telegram notification sent with asset summary

### Step 22 — Approval Service
File: `app/services/approval_service.py`
Functions:
- `handle_approval_decision(db, approval_id, decision, reason, edit_instructions)`
- `update_project_memory_negative_example(db, asset_id, reason)`
Called by: `POST /api/approvals/{id}/decide`
SUCCESS: Approve → PublishJob created; Reject → ProjectMemory.rejected_examples updated

### Step 23 — Publishing Agent + Service
Files: `app/agents/publishing.py`, `app/services/publish_service.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 8
`process_publish_queue()`: fetches ready jobs, calls PublishingAgent
SUCCESS: Mock publish (no real API needed for test) → platform_post_id="mock_123" saved

### Step 24 — Analytics Agent + Google Tools
Files: `app/agents/analytics_agent.py`, `app/tools/google_tools.py`
System prompt: exact text from SOVEREIGN_SPEC.md Section 3, Agent 9
SUCCESS: Analytics agent runs, saves metric_snapshots, sends Telegram report

---

## PHASE 5: SCHEDULER (Step 25)

### Step 25 — APScheduler Integration
File: `app/scheduler/jobs.py`
Jobs: monday_strategy_run (Mon 08:00 Riyadh), monday_plan_notification (Mon 09:00 Riyadh), sunday_analytics_run (Sun 18:00 Riyadh), process_publish_queue (every 5 min)
Integration in `app/main.py`:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```
SUCCESS: App starts, scheduler logs show "Scheduler started", test with 1-min cron

---

## PHASE 6: FRONTEND (Steps 26-29)

### Step 26 — Next.js Setup + Design System
```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --app --src-dir=false
npm install swr framer-motion recharts react-swipeable lucide-react
```
Configure `tailwind.config.ts` with design system colors (Section 4)
Create `app/globals.css` with @font-face + CSS custom properties
Create: `components/ui/Card.tsx` (double-bezel), `Button.tsx`, `Badge.tsx`
Create: `components/react-bits/Aurora.tsx`, `AnimatedContent.tsx`, `SpotlightCard.tsx`, `BlurText.tsx`, `CountUp.tsx`
Create: `lib/api.ts`, `lib/types.ts`, `lib/constants.ts`

CARD COMPONENT (exact implementation):
```tsx
// components/ui/Card.tsx
export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.1)] to-transparent border border-[rgba(201,168,76,0.15)] ${className}`}>
      <div className="rounded-[18px] bg-[#1E293B] p-6 h-full">
        {children}
      </div>
    </div>
  )
}
```

SUCCESS: `npm run build` exits 0, zero TypeScript errors

### Step 27 — Sidebar + Dashboard
Create: `components/ui/Sidebar.tsx` (240px desktop, bottom tab mobile)
Create: `app/layout.tsx` (Sidebar + content area, font variables applied)
Create: `components/dashboard/DashboardHero.tsx` (Aurora + BlurText)
Create: `components/dashboard/StatsRow.tsx` (4 tiles with CountUp)
Create: `components/dashboard/ProjectCard.tsx` (SpotlightCard + AnimatedContent)
Create: `components/dashboard/QuickApprovals.tsx`
Create: `app/page.tsx`
SUCCESS: localhost:3000 loads, Aurora animation visible, Arabic text RTL

### Step 28 — Inbox Page
Create: `components/inbox/ApprovalCard.tsx` (double-bezel, thumbnail, actions)
Create: `components/inbox/ApprovalModal.tsx` (full preview on click)
Create: `components/inbox/SwipeActions.tsx` (Framer Motion swipe gestures)
Create: `components/inbox/InboxFilters.tsx`
Create: `components/inbox/BulkActions.tsx`
Create: `hooks/useApprovals.ts` (SWR hook)
Create: `app/inbox/page.tsx`
SUCCESS: localhost:3000/inbox loads, swipe-right triggers approve API call

### Step 29 — All Remaining Pages
Create all components for projects/[id], plans/[week], assets/[id], analytics
All use SWR hooks for data fetching
All Arabic text: dir="rtl", font-family: Cairo
All metrics: CountUp component
Analytics charts: Recharts LineChart for trends
SUCCESS: All 6 routes return 200, no console errors

---

## PHASE 7: SEED + DEPLOY (Step 30)

### Step 30 — Therapia Seed + Railway Deploy

Create `backend/scripts/seed_therapia.py`:
```python
"""
Run: python scripts/seed_therapia.py
Creates: Organization, Therapia project, ProjectMemory, provisional BrandMemory
Then runs Brand Agent to crawl therapia.live
"""
```

Create `railway.toml`:
```toml
[build]
builder = "nixpacks"

[[services]]
name = "sovereign-backend"
source = "backend"

[services.build]
buildCommand = "pip install -r requirements.txt"

[services.deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"

[[services]]
name = "sovereign-frontend"
source = "frontend"

[services.build]
buildCommand = "npm ci && npm run build"

[services.deploy]
startCommand = "npm start"
```

Deploy steps:
1. `git add . && git commit -m "initial: sovereign autonomous marketing OS"`
2. `git push origin main`
3. Connect repo to Railway, set all env vars
4. Railway auto-deploys both services
5. Run seed: `python scripts/seed_therapia.py` (with PROD DATABASE_URL)
6. Set Telegram webhook: `curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" -d "url=https://sovereign-backend.railway.app/api/webhook/telegram"`

SUCCESS CRITERIA (all must pass before marking done):
- [ ] `curl https://sovereign-backend.railway.app/api/projects` → Therapia project returned
- [ ] `curl https://sovereign-backend.railway.app/api/projects/{id}/memory` → ProjectMemory with ICP
- [ ] `curl https://sovereign-backend.railway.app/api/projects/{id}/brand` → provisional BrandMemory
- [ ] `https://sovereign-frontend.railway.app` → dashboard loads, no 500 errors
- [ ] Telegram webhook test: send `/start` to bot → receives response
- [ ] `npm run build` (frontend): zero errors
- [ ] `grep -r "console.log" frontend/` → nothing (clean)
- [ ] `grep -r "TODO\|FIXME\|placeholder\|mock" backend/app/` → nothing except test files

---

## FINAL QUALITY CHECKS

Before closing this task:

```bash
# Backend
cd backend
grep -r "console.log" app/ --include="*.py"      # must return nothing
grep -r "TODO\|FIXME\|placeholder" app/ --include="*.py"  # must return nothing
grep -r "hardcoded" app/ --include="*.py"         # must return nothing
python -m pytest tests/ -v --tb=short             # all pass

# Frontend
cd frontend
npm run build                                      # zero TS errors
npm run lint                                       # zero ESLint errors
grep -r "console.log" app/ components/            # must return nothing
grep -r "TODO\|FIXME" app/ components/            # must return nothing

# Arabic check
grep -r "Inter\|Roboto\|Arial\|system-ui" app/ components/ tailwind.config.ts  # must return nothing
```

---

*SOVEREIGN_CODEX_TASK.md — Exact spec. No ambiguity. Execute in order.*
*Claude = Architect. Codex = Builder. Omar = Approver.*
