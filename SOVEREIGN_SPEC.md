# SOVEREIGN — Autonomous AI Marketing Command Center
# Complete Implementation Spec for Codex
# Version: 1.0 | Authored by Ale (Claude) | 2026-05-09
# Status: PLANNING ONLY — Zero code written. Hand to Codex.

---

## CONTEXT FOR CODEX

Sovereign is an internal autonomous marketing OS for Omar Alomran, who manages 4 ventures:
- **Therapia** — health app (primary MVP target)
- **Qawwi** — B2B fitness coaching SaaS
- **ProductBench** — Saudi fintech competitive intelligence SaaS
- **Sahmalgo** — TBD

Omar approves or rejects. The system does everything else: plans, writes, designs, QAs, routes for approval, publishes, measures, learns.

First rule: **never publish without founder approval.**
Second rule: **never ship broken work.**
Third rule: **Arabic is primary, not an afterthought.**

---

## 1. ARCHITECTURE DECISION

### Stack (locked — no alternatives)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind | App Router for server components, RSC for fast loads |
| Backend | FastAPI (Python 3.12) | Async, fast, agent-friendly, Pydantic native |
| Database | PostgreSQL 16 + pgvector extension | Relational + vector search in one DB |
| File Storage | Cloudflare R2 | S3-compatible, cheap egress, signed URLs |
| AI Agent Core | Anthropic claude-sonnet-4-20250514 with tool use | Best tool-calling model |
| Image Generation | fal.ai (fal-ai/flux/schnell + fal-ai/flux-pro) | Fastest image gen API |
| Publishing | Direct social APIs (LinkedIn v2, Meta Graph, Twitter v2, Google Ads API) | No third-party social poster dependencies |
| Notifications | Resend (email) + Telegram Bot API | Both required |
| Task Scheduling | APScheduler (Python, in-process) | Simple, no Redis needed for MVP |
| Deployment | Railway (both frontend + backend services) | Matches Omar's existing stack |
| ORM | SQLAlchemy 2.0 (async) + Alembic migrations | Standard Python ORM |
| Auth | Single API key in env for MVP (no public auth needed — internal tool) | Keep it simple |

### Monorepo Structure
```
sovereign/
├── frontend/          # Next.js 14
├── backend/           # FastAPI
├── .env.example       # All required env vars
├── .gitignore
├── railway.toml       # Railway multi-service config
├── SOVEREIGN_SPEC.md  # This file
└── SOVEREIGN_CODEX_TASK.md  # Codex step-by-step instructions
```

### Environment Variables Required
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/sovereign
DATABASE_URL_SYNC=postgresql://user:pass@host:5432/sovereign  # for Alembic

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# fal.ai
FAL_KEY=...

# Cloudflare R2
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=sovereign-assets
R2_PUBLIC_URL=https://...r2.dev

# Notifications
RESEND_API_KEY=re_...
FOUNDER_EMAIL=oalomran443@gmail.com
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Social APIs
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_ORG_ID=...
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_USER_ID=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ANALYTICS_PROPERTY_ID=...

# Frontend
NEXT_PUBLIC_API_URL=https://sovereign-backend.railway.app
API_SECRET_KEY=...  # shared secret between frontend and backend
```

---

## 2. DATABASE SCHEMA

### Setup
```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
```

### Table 1: organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    plan_type TEXT NOT NULL DEFAULT 'internal' CHECK (plan_type IN ('internal', 'saas_starter', 'saas_pro', 'saas_enterprise')),
    owner_email TEXT NOT NULL,
    telegram_chat_id TEXT,
    resend_from_email TEXT DEFAULT 'sovereign@notifications.ai',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Table 2: projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,  -- therapia, qawwi, productbench, sahmalgo
    business_model TEXT NOT NULL CHECK (business_model IN ('b2c', 'b2b', 'saas', 'marketplace', 'other')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    primary_goal TEXT NOT NULL,  -- e.g., "app_downloads_and_assessments" for Therapia
    website_url TEXT,
    priority INTEGER NOT NULL DEFAULT 1,
    channels JSONB NOT NULL DEFAULT '[]',  -- array of {channel, account_id, connected: bool}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_org_id ON projects(org_id);
CREATE INDEX idx_projects_slug ON projects(slug);
```

### Table 3: project_memory
```sql
CREATE TABLE project_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id),
    icp JSONB NOT NULL DEFAULT '{}',
    -- icp structure: {
    --   demographics: {age_range, gender, location, income_level},
    --   pain_points: [string],
    --   goals: [string],
    --   channels_they_use: [string],
    --   buying_triggers: [string]
    -- }
    positioning TEXT,
    offers JSONB NOT NULL DEFAULT '[]',
    -- offers structure: [{name, price, description, cta, landing_url}]
    tone TEXT,  -- e.g., "warm, supportive, health-positive, never fear-mongering"
    languages TEXT[] NOT NULL DEFAULT '{ar,en}',
    funnel_goals JSONB NOT NULL DEFAULT '{}',
    -- funnel_goals: {
    --   awareness: {metric, target, current},
    --   consideration: {metric, target, current},
    --   conversion: {metric, target, current},
    --   retention: {metric, target, current}
    -- }
    constraints JSONB NOT NULL DEFAULT '{}',
    -- constraints: {budget_cap_sar, excluded_topics, competitor_mentions_allowed}
    approved_examples JSONB NOT NULL DEFAULT '[]',
    -- [{asset_id, channel, why_it_worked, metrics}]
    rejected_examples JSONB NOT NULL DEFAULT '[]',
    -- [{asset_id, channel, rejection_reason, what_to_avoid}]
    performance_learnings TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Table 4: brand_memory
```sql
CREATE TABLE brand_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE (project_id),
    logo_url TEXT,  -- R2 signed URL
    color_palette JSONB NOT NULL DEFAULT '{}',
    -- {primary: "#hex", secondary: "#hex", accent: "#hex", background: "#hex", text: "#hex"}
    typography JSONB NOT NULL DEFAULT '{}',
    -- {headline_font: str, body_font: str, arabic_font: str, data_font: str}
    arabic_font_url TEXT,  -- R2 signed URL for special Arabic font file
    visual_style TEXT,  -- "dark luxury", "clean minimal", "warm health"
    image_style TEXT,   -- "lifestyle photography", "abstract gradients", "flat illustration"
    brand_voice TEXT,
    dos JSONB NOT NULL DEFAULT '[]',    -- [string]
    donts JSONB NOT NULL DEFAULT '[]',  -- [string]
    templates JSONB NOT NULL DEFAULT '[]',
    -- [{name, type, r2_url, dimensions, channel}]
    rejected_styles JSONB NOT NULL DEFAULT '[]',
    -- [{description, example_url, rejection_reason}]
    is_provisional BOOLEAN NOT NULL DEFAULT TRUE,
    -- true until founder explicitly approves brand guide
    approved_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Table 5: weekly_plans
```sql
CREATE TABLE weekly_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    UNIQUE (project_id, week_start),
    objective TEXT NOT NULL,
    funnel_focus TEXT NOT NULL CHECK (funnel_focus IN ('awareness', 'consideration', 'conversion', 'retention')),
    tactics JSONB NOT NULL DEFAULT '[]',
    -- [{
    --   id: uuid, channel, asset_type, funnel_stage,
    --   rationale, rationale_simple,
    --   budget_estimate_sar, budget_type: 'organic'|'paid',
    --   stop_loss_sar, expected_metric, expected_value
    -- }]
    total_budget_estimate DECIMAL(10,2) NOT NULL DEFAULT 0,
    rationale TEXT NOT NULL,       -- simple 3-4 sentence explanation for founder
    risk_flags JSONB NOT NULL DEFAULT '[]',  -- [string]
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected', 'executing', 'done')),
    approval_id UUID,  -- FK to approvals (set after approval)
    created_by TEXT NOT NULL DEFAULT 'strategy_agent',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_weekly_plans_project_week ON weekly_plans(project_id, week_start);
```

### Table 6: assets
```sql
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    weekly_plan_id UUID REFERENCES weekly_plans(id),
    tactic_id TEXT,  -- references tactic.id within weekly_plan.tactics jsonb
    type TEXT NOT NULL CHECK (type IN ('post', 'carousel', 'story', 'ad_creative', 'ad_copy', 'email', 'landing_section')),
    channel TEXT NOT NULL CHECK (channel IN ('linkedin', 'instagram', 'x', 'google_ads', 'email')),
    language TEXT NOT NULL CHECK (language IN ('ar', 'en', 'bilingual')),
    copy_ar TEXT,
    copy_en TEXT,
    copy_bilingual JSONB,  -- {ar: str, en: str} for bilingual assets
    design_prompt TEXT,    -- the exact prompt sent to fal.ai
    design_url TEXT,       -- R2 URL of final design
    design_thumbnail_url TEXT,  -- R2 URL of 400px thumbnail
    platform_dimensions JSONB, -- {width: int, height: int}
    status TEXT NOT NULL DEFAULT 'generating'
        CHECK (status IN (
            'generating', 'qa_pending', 'qa_failed',
            'approval_pending', 'approved', 'rejected',
            'edit_requested', 'scheduled', 'published', 'failed'
        )),
    qa_score DECIMAL(5,2),    -- 0-100
    qa_passed BOOLEAN,
    qa_notes JSONB NOT NULL DEFAULT '[]',  -- [{check, status, note}]
    rejection_reason TEXT,
    edit_instructions TEXT,
    platform_post_id TEXT,     -- ID returned by social API after publish
    variants JSONB NOT NULL DEFAULT '[]',  -- [{copy_ar, copy_en, design_url}] for A/B
    embedding vector(1536),    -- pgvector embedding of copy for similarity search
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assets_project_id ON assets(project_id);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_channel ON assets(channel);
CREATE INDEX idx_assets_embedding ON assets USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Table 7: approvals
```sql
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES assets(id),           -- null if approving a plan
    weekly_plan_id UUID REFERENCES weekly_plans(id), -- null if approving an asset
    CONSTRAINT approval_target_check CHECK (
        (asset_id IS NOT NULL AND weekly_plan_id IS NULL) OR
        (asset_id IS NULL AND weekly_plan_id IS NOT NULL)
    ),
    approver_id TEXT NOT NULL DEFAULT 'founder',  -- email or 'system'
    decision TEXT CHECK (decision IN ('approved', 'rejected', 'edit_requested')),
    reason TEXT,
    edit_instructions TEXT,
    notification_channels TEXT[] NOT NULL DEFAULT '{email,telegram}',
    notification_sent_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_asset_id ON approvals(asset_id);
CREATE INDEX idx_approvals_weekly_plan_id ON approvals(weekly_plan_id);
CREATE INDEX idx_approvals_decision ON approvals(decision);
```

### Table 8: publish_jobs
```sql
CREATE TABLE publish_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    approval_id UUID NOT NULL REFERENCES approvals(id),
    channel TEXT NOT NULL,
    channel_account_id TEXT,
    scheduled_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    platform_post_id TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'publishing', 'published', 'failed', 'cancelled')),
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publish_jobs_status ON publish_jobs(status);
CREATE INDEX idx_publish_jobs_scheduled_at ON publish_jobs(scheduled_at);
```

### Table 9: metric_snapshots
```sql
CREATE TABLE metric_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),  -- link metric to specific asset if applicable
    channel TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    -- Values: followers, impressions, clicks, reach, engagement_rate,
    --         conversions, app_downloads, assessments_completed,
    --         click_through_rate, cost_per_click, roas, leads
    value DECIMAL(15,4) NOT NULL,
    date DATE NOT NULL,
    source TEXT NOT NULL,
    -- Values: instagram_api, linkedin_api, twitter_api, google_ads,
    --         google_analytics, product_db, manual
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, channel, metric_type, date, source)
);

CREATE INDEX idx_metrics_project_channel ON metric_snapshots(project_id, channel);
CREATE INDEX idx_metrics_date ON metric_snapshots(date);
CREATE INDEX idx_metrics_type ON metric_snapshots(metric_type);
```

### Table 10: audit_events
```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_type TEXT NOT NULL CHECK (actor_type IN ('founder', 'agent', 'system', 'scheduler')),
    actor_id TEXT NOT NULL,  -- agent name, 'founder', or 'scheduler'
    action TEXT NOT NULL,
    -- Values: plan_generated, plan_approved, plan_rejected,
    --         asset_generated, asset_qa_passed, asset_qa_failed,
    --         asset_approved, asset_rejected, asset_published, asset_failed,
    --         brand_updated, brand_approved, memory_updated,
    --         notification_sent, publish_job_created, publish_job_failed
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_events_object ON audit_events(object_type, object_id);
CREATE INDEX idx_audit_events_action ON audit_events(action);
CREATE INDEX idx_audit_events_created_at ON audit_events(created_at DESC);
```

### FK closing (after all tables created)
```sql
ALTER TABLE weekly_plans
    ADD CONSTRAINT fk_weekly_plans_approval
    FOREIGN KEY (approval_id) REFERENCES approvals(id);
```

---

## 3. AGENT DEFINITIONS

### Base Agent Pattern (all agents follow this)
```python
# backend/agents/base.py
# Every agent:
# 1. Loads context from DB via tools
# 2. Calls claude-sonnet-4-20250514 with tool_use
# 3. Executes tool calls in a loop until stop_reason == "end_turn"
# 4. Writes output to DB
# 5. Creates AuditEvent
# Model: claude-sonnet-4-20250514
# Max tokens: 4096 for copy agents, 1024 for QA agents
# Temperature: 0.7 for creative, 0.2 for QA/analysis
```

---

### Agent 1: Strategy Agent

**System Prompt:**
```
You are the Strategy Agent for Sovereign, an autonomous AI marketing command center.

Your job: Create a precise weekly marketing plan for a specific project.

Read the project's memory carefully before making any recommendations. Do not invent facts about the project.

Plan creation rules:
1. Identify the highest-impact funnel stage for THIS week based on current metrics vs targets
2. Select 3-5 concrete, executable tactics — no vague recommendations
3. Always include at least one organic (SAR 0) tactic
4. For paid tactics: include stop-loss threshold (max spend before pausing)
5. Explain EVERY recommendation in 1-2 sentences a non-marketer can understand
6. Set specific, measurable expected outcomes per tactic

For Therapia: north star = app downloads + health assessments completed. Every tactic must trace to these.
For Qawwi: north star = B2B leads + demo requests. Tactics should be sales-oriented.
For ProductBench: north star = waitlist signups + paying customers.
For Sahmalgo: use project memory to determine north star.

NEVER recommend tactics without "why this matters" explanation.
NEVER use marketing jargon without plain-language translation.
NEVER exceed the budget cap from project memory constraints.

Output must be valid JSON matching the WeeklyPlanOutput schema exactly.
```

**Tools:**
- `get_project_memory(project_id: str) -> ProjectMemory`
- `get_brand_memory(project_id: str) -> BrandMemory`
- `get_metric_history(project_id: str, days: int = 30) -> List[MetricSnapshot]`
- `get_previous_plans(project_id: str, count: int = 4) -> List[WeeklyPlan]`
- `get_approved_assets_summary(project_id: str, days: int = 30) -> List[dict]`
- `save_weekly_plan(plan: WeeklyPlanCreate) -> WeeklyPlan`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class StrategyInput(BaseModel):
    project_id: str
    week_start: date
    founder_notes: Optional[str] = None
    budget_cap_sar: Optional[Decimal] = None  # None = suggest freely
```

**Output Schema:**
```python
class Tactic(BaseModel):
    id: str  # uuid4
    channel: Literal["linkedin", "instagram", "x", "google_ads", "email"]
    asset_type: Literal["post", "carousel", "story", "ad_creative", "ad_copy"]
    funnel_stage: Literal["awareness", "consideration", "conversion", "retention"]
    rationale: str          # technical rationale for agent use
    rationale_simple: str   # plain language for founder (1-2 sentences)
    budget_estimate_sar: Decimal
    budget_type: Literal["organic", "paid"]
    stop_loss_sar: Optional[Decimal]
    expected_metric: str
    expected_value: str     # e.g., "500-800 impressions" or "5-10 app downloads"

class WeeklyPlanOutput(BaseModel):
    objective: str
    funnel_focus: Literal["awareness", "consideration", "conversion", "retention"]
    tactics: List[Tactic]   # 3-5 tactics
    total_budget_estimate: Decimal
    rationale: str          # 3-4 sentence plain-language summary for founder
    risk_flags: List[str]   # e.g., ["Google Ads requires account verification"]
```

**Runs:** Monday 08:00 AM (cron). Once per project per week.

---

### Agent 2: Brand Agent

**System Prompt:**
```
You are the Brand Agent for Sovereign. You build and maintain the authoritative brand identity for each project.

On FIRST RUN (is_provisional = True in BrandMemory, or BrandMemory doesn't exist):
1. Use crawl_website tool to fetch homepage, about page, and any /brand or /style pages
2. Extract: exact hex colors, font names, tone adjectives, target audience signals, value proposition
3. Generate provisional brand guide — label every unconfirmed field clearly as "(provisional)"
4. Set is_provisional = True
5. Notify founder for approval via create_approval_request

On EVERY ASSET GENERATION:
- Return brand rules as structured context for Copy and Design agents
- Include dos, don'ts, color palette, typography, voice, image style

On APPROVAL RECEIVED (is_provisional transitions to False):
- Update approved_at timestamp
- Lock brand guide (requires founder approval to change)

On REJECTION SIGNAL (asset rejected for brand reasons):
- Extract what was rejected and WHY from rejection_reason
- Add to rejected_styles
- Update donts list
- Increment version

CRITICAL: Never fabricate brand data. If the website has no color information, label colors as "(provisional — extracted from best guess)". Transparency is required.

Output must be valid JSON matching BrandMemoryOutput schema.
```

**Tools:**
- `crawl_website(url: str) -> dict`  — returns {title, colors_detected, fonts_detected, tone_words, hero_text, about_text, cta_text}
- `extract_brand_signals(crawl_result: dict) -> BrandSignals`
- `get_brand_memory(project_id: str) -> Optional[BrandMemory]`
- `save_brand_memory(brand: BrandMemoryCreate) -> BrandMemory`
- `update_brand_memory(project_id: str, updates: dict) -> BrandMemory`
- `upload_asset_r2(file_bytes: bytes, filename: str) -> str`  — returns R2 URL
- `create_approval_request(project_id: str, type: str, payload: dict) -> Approval`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class BrandAgentInput(BaseModel):
    project_id: str
    mode: Literal["init", "refresh", "update_from_rejection"]
    rejection_data: Optional[dict] = None  # {asset_id, reason} for mode=update_from_rejection
```

**Output Schema:**
```python
class BrandMemoryOutput(BaseModel):
    project_id: str
    color_palette: dict   # {primary, secondary, accent, background, text}
    typography: dict      # {headline_font, body_font, arabic_font, data_font}
    visual_style: str
    image_style: str
    brand_voice: str
    dos: List[str]
    donts: List[str]
    is_provisional: bool
```

**Runs:** During Therapia onboarding. Triggered by brand rejection events. Manual refresh on demand.

---

### Agent 3: Copy Agent

**System Prompt:**
```
You are the Copy Agent for Sovereign. You write high-converting marketing copy in Arabic and English.

ALWAYS read ProjectMemory and BrandMemory before writing. Do not invent product facts.

Arabic writing rules (NON-NEGOTIABLE):
- Gulf Saudi dialect — warm, direct, like talking to a trusted friend
- NEVER فصحى unless the context is explicitly legal or formal
- NEVER translate from English — write native Arabic from scratch
- RTL metadata must accompany all Arabic text
- Motivational tone: يلا يا بطل — enthusiastic, personal
- CTAs must be specific: نزّل التطبيق / ابدأ مجاناً / احجز جلستك
- BANNED generic CTAs: "اضغط هنا", "تعرف أكثر" (without specific action)

Per-channel format rules:
- LinkedIn: 150-300 words, professional insight-led, data-backed, 1-3 hashtags, English primary
- Instagram: 80-150 word caption, punchy Arabic opener, benefit-driven body, specific CTA, 5-10 Arabic hashtags
- X/Twitter: ≤280 chars for single tweet, 6-8 posts for threads, punchy + shareable
- Google Ads: Headline1 ≤30 chars, Headline2 ≤30 chars, Description ≤90 chars (strict limits)

Quality rules:
- Generate 2 variants per asset (Variant A: direct/rational, Variant B: emotional/story)
- Flag any unverifiable claim with [CLAIM: needs verification]
- For Therapia: NEVER make health claims that require clinical substantiation
- CTA must link to a real destination (check project memory for landing URLs)

Output: structured JSON with copy_ar, copy_en, variants, character_counts, flags
```

**Tools:**
- `get_project_memory(project_id: str) -> ProjectMemory`
- `get_brand_memory(project_id: str) -> BrandMemory`
- `get_weekly_plan(plan_id: str) -> WeeklyPlan`
- `get_approved_examples(project_id: str, channel: str) -> List[dict]`
- `get_rejected_examples(project_id: str, channel: str) -> List[dict]`
- `save_asset(asset: AssetCreate) -> Asset`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class CopyAgentInput(BaseModel):
    project_id: str
    weekly_plan_id: str
    tactic_id: str
    channel: str
    asset_type: str
    language: Literal["ar", "en", "bilingual"]
    funnel_stage: str
```

**Output Schema:**
```python
class CopyVariant(BaseModel):
    label: Literal["A", "B"]
    copy_ar: Optional[str]
    copy_en: Optional[str]
    char_count_ar: Optional[int]
    char_count_en: Optional[int]
    cta_ar: Optional[str]
    cta_en: Optional[str]

class CopyOutput(BaseModel):
    asset_id: str
    copy_ar: str
    copy_en: str
    variants: List[CopyVariant]
    character_counts: dict
    claim_flags: List[str]
    hashtags_ar: List[str]
    hashtags_en: List[str]
```

**Runs:** After weekly plan is approved. Generates all copy for all tactics in parallel.

---

### Agent 4: Design Agent

**System Prompt:**
```
You are the Design Agent for Sovereign. You generate professional marketing visuals using fal.ai.

ALWAYS read BrandMemory first. Brand rules are law.

Image generation process:
1. Build detailed fal.ai prompt that encodes: color palette, image style, mood, composition, text space
2. Use fal-ai/flux-pro for hero images and ad creatives (quality priority)
3. Use fal-ai/flux/schnell for story/quick social posts (speed priority)
4. Download generated image
5. Apply text overlay via Pillow (copy + correct font)
6. Resize to exact platform dimensions
7. Upload to R2 → return design_url and design_thumbnail_url

Platform dimensions (exact, no exceptions):
- Instagram post: 1080x1080px
- Instagram story: 1080x1920px
- LinkedIn post: 1200x627px
- X/Twitter: 1600x900px
- Google Display: 1200x628px, 300x250px, 160x600px (generate all three)

Text overlay rules:
- Arabic text: ALWAYS use the project's uploaded arabic_font from BrandMemory. NEVER system fallback fonts.
- RTL: text-align right, direction RTL
- Minimum font size: 28px body, 48px headline
- Contrast: minimum 4.5:1 ratio (WCAG AA)
- Padding: 15% from edges minimum
- Arabic and English text never overlap

Brand prompt injection (always prepend to fal.ai prompt):
"[Brand palette: primary={primary_hex}, background={bg_hex}. Style: {visual_style}. Mood: {image_style}. No text in the image — leave clear space for text overlay. Professional quality, high resolution.]"

If brand colors are provisional: use them but add qa_note: "Colors provisional — founder approval pending"
```

**Tools:**
- `get_brand_memory(project_id: str) -> BrandMemory`
- `get_asset(asset_id: str) -> Asset`
- `generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes`
- `apply_text_overlay(image: bytes, text_ar: str, text_en: str, font_url: str, config: dict) -> bytes`
- `resize_image(image: bytes, width: int, height: int) -> bytes`
- `upload_to_r2(file_bytes: bytes, filename: str, content_type: str) -> str`
- `create_thumbnail(image: bytes, max_size: int = 400) -> bytes`
- `update_asset(asset_id: str, updates: dict) -> Asset`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class DesignAgentInput(BaseModel):
    project_id: str
    asset_id: str      # copy must already exist in asset record
    platform_channel: str
    asset_type: str
```

**Output Schema:**
```python
class DesignOutput(BaseModel):
    asset_id: str
    design_url: str
    design_thumbnail_url: str
    design_prompt_used: str
    platform_dimensions: dict
    fal_model_used: str
    warnings: List[str]  # e.g., "Colors provisional"
```

**Runs:** After Copy Agent completes. Design runs in parallel across all assets.

---

### Agent 5: Translation/Localization Agent

**System Prompt:**
```
You are the Localization Agent for Sovereign. You produce native-quality Arabic and English marketing content.

You are NOT a translator. You are a native Arabic copywriter who also writes English.

Arabic rules (absolute):
- Gulf Saudi dialect (الخليجي السعودي). If unsure about dialect nuance, default to warm Gulf tone.
- Write as if talking to a friend who uses WhatsApp casually — direct, warm, real
- FORBIDDEN: فصحى, Egyptian dialect, Levantine expressions (unless project specifies)
- FORBIDDEN: word-for-word translation from English
- Emotional register: match the English version's energy but in native Arabic expression
- CTAs: نزّل التطبيق / ابدأ رحلتك / احجز مجاناً / جرّبه الحين / شاركنا رأيك
- Punctuation: Arabic punctuation rules (،، ؟ ！)
- Numbers: Arabic-Indic numerals for Arabic text (٠١٢٣) unless context is technical

Bilingual assets:
- Arabic version stands alone (primary, larger)
- English version stands alone (secondary, smaller, below)
- Neither should feel like a translation of the other
- Both should convert independently

Quality check before output:
- Read the Arabic aloud mentally — does it sound like a Saudi saying this naturally?
- Would a Saudi reader find this cringe or formal? Fix it.
- Is the CTA specific and action-triggering? Not generic?
```

**Tools:**
- `get_project_memory(project_id: str) -> ProjectMemory`
- `get_brand_memory(project_id: str) -> BrandMemory`
- `get_asset(asset_id: str) -> Asset`
- `update_asset(asset_id: str, updates: dict) -> Asset`
- `check_rtl_rendering(text_ar: str) -> dict`  — validates RTL string integrity
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class LocalizationInput(BaseModel):
    asset_id: str
    source_copy: str        # the original draft copy (usually English)
    target_language: Literal["ar", "en", "bilingual"]
    channel: str
    funnel_stage: str
    tone_instructions: Optional[str] = None
```

**Output Schema:**
```python
class LocalizationOutput(BaseModel):
    asset_id: str
    copy_ar: str
    copy_en: str
    cta_ar: str
    cta_en: str
    hashtags_ar: List[str]
    hashtags_en: List[str]
    rtl_validated: bool
    dialect_check_passed: bool
```

**Runs:** After Copy Agent. Runs before Design Agent (design needs final copy for text overlay).

---

### Agent 6: QA Agent

**System Prompt:**
```
You are the QA Agent for Sovereign. Nothing reaches the founder's approval inbox until it passes all your checks.

You are the last automated line of defense. Be strict. A false pass is worse than a false fail.

SCORING: 0-100. Pass threshold: ≥85. Warning zone: 70-84 (flag but pass). Fail: <70 (block, list fixes).

BRAND QA (25 points):
- Colors match BrandMemory palette (±10% hex tolerance): 10 pts
- Typography correct (no banned fonts): 5 pts
- Tone matches BrandMemory voice profile: 5 pts
- No previously-rejected visual patterns: 5 pts

COPY QA (25 points):
- No unverified claims ("[CLAIM:]" flags must be resolved): 10 pts
- CTA is specific and action-oriented: 5 pts
- Character counts within channel limits: 5 pts
- No competitor mentions without approval: 5 pts

ARABIC QA (25 points):
- Text is RTL (not LTR with Arabic characters): 10 pts
- Arabic font is project's approved font (not system fallback): 5 pts
- No awkward line breaks mid-word: 5 pts
- Dialect is Gulf Saudi (flag if formal/فصحى detected): 5 pts

POLICY QA (25 points):
- Therapia: no health claims requiring clinical proof: 10 pts
- No prohibited platform content (violence, adult, etc.): 10 pts
- Budget/financial claims accurate for ProductBench/Qawwi: 5 pts

Output exact JSON: {qa_score, qa_passed, checks: [{check_name, status, note, points_awarded}], required_fixes: [str]}
If qa_passed is false: required_fixes must be actionable (not vague).
```

**Tools:**
- `get_brand_memory(project_id: str) -> BrandMemory`
- `get_asset(asset_id: str) -> Asset`
- `get_rejected_examples(project_id: str) -> List[dict]`
- `analyze_image_colors(image_url: str) -> List[str]`  — extract hex colors from design
- `check_font_in_image(image_url: str) -> str`  — detect font used
- `check_rtl_rendering(text_ar: str) -> dict`
- `check_text_contrast(image_url: str) -> float`  — WCAG contrast ratio
- `update_asset(asset_id: str, updates: dict) -> Asset`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class QAInput(BaseModel):
    asset_id: str
    project_id: str
```

**Output Schema:**
```python
class QACheck(BaseModel):
    check_name: str
    status: Literal["pass", "fail", "warning"]
    note: str
    points_awarded: int

class QAOutput(BaseModel):
    asset_id: str
    qa_score: float
    qa_passed: bool
    checks: List[QACheck]
    required_fixes: List[str]
```

**Runs:** After Design + Localization complete. Blocks assets from entering approval inbox.

---

### Agent 7: Approval Agent

**System Prompt:**
```
You are the Approval Agent for Sovereign. You route QA-passed items to the founder and handle all approval logistics.

You send notifications. You do NOT make approval decisions. Only the founder does.

Notification rules:
1. Package each approval item as a clean card: thumbnail, channel, copy excerpt, funnel stage, rationale_simple
2. Send email via Resend: clean HTML with preview images, approve/reject links
3. Send Telegram message: concise Arabic notification with inline keyboard buttons
4. Create approval record in DB with decision=null (pending)
5. Monitor for webhook response (approve/reject via /api/approvals/[id]/decide)
6. After decision received: trigger downstream (publish job or rejection learning)

Email subject: "Sovereign: [N] محتوى جاهز للموافقة — [Project Name]"
Telegram format: "🔔 يا عمر — عندك [N] محتوى جاهز للموافقة على [Project]\n\nأبرز المحتوى:\n• [brief description]\n\n"
Telegram buttons: [✅ وافق على الكل] [❌ ارفض] [👁 راجع في التطبيق]

NEVER mark an asset as approved automatically. Always wait for explicit founder decision.
NEVER send more than 3 Telegram notifications per day per project (batch them).
```

**Tools:**
- `get_qa_passed_assets(project_id: str) -> List[Asset]`
- `get_pending_plan_approvals(project_id: str) -> List[WeeklyPlan]`
- `create_approval_record(asset_id: Optional[str], plan_id: Optional[str]) -> Approval`
- `send_email_resend(to: str, subject: str, html: str) -> bool`
- `send_telegram_notification(chat_id: str, text: str, keyboard: dict) -> bool`
- `update_asset_status(asset_id: str, status: str) -> Asset`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class ApprovalAgentInput(BaseModel):
    project_id: str
    mode: Literal["send_notifications", "process_decision"]
    decision_data: Optional[dict] = None  # {approval_id, decision, reason}
```

**Output Schema:**
```python
class ApprovalAgentOutput(BaseModel):
    notifications_sent: int
    approval_ids: List[str]
    email_sent: bool
    telegram_sent: bool
```

**Runs:** After QA passes for each asset batch. Also triggered by plan completion.

---

### Agent 8: Publishing Agent

**System Prompt:**
```
You are the Publishing Agent for Sovereign. You execute approved assets to social channels.

ABSOLUTE RULE 1: NEVER publish without verified approval record. Check approval.decision == "approved" AND approval.decided_at IS NOT NULL. If either is null/wrong, ABORT and log error.

ABSOLUTE RULE 2: NEVER publish to the wrong channel. Verify asset.channel matches publish_job.channel.

ABSOLUTE RULE 3: Max 3 retries on failure. After 3 failures, mark status=failed and alert founder via Telegram.

Publishing process:
1. Verify approval record
2. Check channel API token is valid (attempt token refresh if expired)
3. Upload media to platform (if required by platform API)
4. Post content
5. Capture platform_post_id from API response
6. Update asset.status = "published"
7. Update publish_job.published_at and status = "published"
8. Create AuditEvent
9. Send confirmation Telegram: "✅ تم النشر — [Project] على [Channel]"

Platform-specific rules:
- LinkedIn: Post as organization, not personal (use org_id)
- Instagram: Must use Media Object creation first, then publish
- X/Twitter: v2 API, media upload separately if image included
- Google Ads: Create ad within existing campaign structure, not new campaign per post
```

**Tools:**
- `verify_approval(approval_id: str) -> bool`
- `get_asset(asset_id: str) -> Asset`
- `get_publish_job(job_id: str) -> PublishJob`
- `publish_to_linkedin(asset: Asset, org_id: str) -> str`  — returns post_id
- `publish_to_instagram(asset: Asset, user_id: str) -> str`
- `publish_to_twitter(asset: Asset) -> str`
- `create_google_ad(asset: Asset, campaign_id: str) -> str`
- `update_asset_status(asset_id: str, status: str, platform_post_id: str) -> Asset`
- `update_publish_job(job_id: str, updates: dict) -> PublishJob`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`
- `send_telegram_notification(chat_id: str, text: str) -> bool`

**Input Schema:**
```python
class PublishingInput(BaseModel):
    publish_job_id: str
```

**Output Schema:**
```python
class PublishingOutput(BaseModel):
    publish_job_id: str
    asset_id: str
    status: str
    platform_post_id: Optional[str]
    published_at: Optional[datetime]
    error: Optional[str]
```

**Runs:** After approval decision webhook received. Scheduled at founder-approved time or immediately.

---

### Agent 9: Analytics Agent

**System Prompt:**
```
You are the Analytics Agent for Sovereign. You measure results, explain what happened simply, and feed learnings back into project memory.

Weekly cycle (runs Sunday 6PM):
1. Pull metrics from all connected channel APIs for each active project
2. Pull product metrics (Therapia: app downloads, assessments completed from GA)
3. Calculate week-over-week changes
4. Rank assets by performance (engagement rate + conversion contribution)
5. Identify top 3 performers and bottom 3 performers
6. Update ProjectMemory.performance_learnings (3-5 bullet points)
7. Update ProjectMemory.approved_examples with top performers
8. Generate weekly report in Arabic (primary) + English (secondary)
9. Send report via email + Telegram

Report language rules:
- Write in Arabic first, simple and clear. No marketing jargon.
- "المتابعين ارتفعوا بنسبة 12% هالأسبوع" not "Follower growth rate increased by 12%"
- Be honest about what didn't work. Omar needs truth, not spin.
- End with 2-3 specific recommendations for next week

Report structure:
1. ملخص الأسبوع (week summary — 2 sentences)
2. أبرز النتائج (key results — metrics vs targets)
3. المحتوى الأكثر أثراً (top performing assets)
4. ما لم ينجح وليش (what failed + hypothesis)
5. توصيات الأسبوع الجاي (next week recommendations)
```

**Tools:**
- `get_instagram_metrics(account_id: str, since: date, until: date) -> List[dict]`
- `get_linkedin_metrics(org_id: str, since: date, until: date) -> List[dict]`
- `get_twitter_metrics(since: date, until: date) -> List[dict]`
- `get_google_ads_metrics(customer_id: str, since: date, until: date) -> List[dict]`
- `get_google_analytics_metrics(property_id: str, since: date, until: date) -> List[dict]`
- `get_project_assets(project_id: str, since: date) -> List[Asset]`
- `get_project_memory(project_id: str) -> ProjectMemory`
- `update_project_memory(project_id: str, updates: dict) -> ProjectMemory`
- `save_metric_snapshots(snapshots: List[MetricSnapshotCreate]) -> None`
- `send_email_resend(to: str, subject: str, html: str) -> bool`
- `send_telegram_notification(chat_id: str, text: str) -> bool`
- `create_audit_event(action: str, object_id: str, metadata: dict) -> None`

**Input Schema:**
```python
class AnalyticsInput(BaseModel):
    project_ids: List[str]  # run for all active projects
    week_start: date
    week_end: date
```

**Output Schema:**
```python
class AnalyticsOutput(BaseModel):
    project_id: str
    report_ar: str
    report_en: str
    top_performers: List[str]  # asset_ids
    bottom_performers: List[str]
    metrics_pulled: int
    memory_updated: bool
```

**Runs:** Sunday 18:00 (cron). Covers Mon-Sun of the completed week.

---

## 4. UI SPECIFICATION

### Design System (apply to all pages)

**Colors:**
```css
--obsidian: #0A0A0A;
--gold: #C9A84C;
--gold-light: #E8C97A;
--gold-dim: rgba(201, 168, 76, 0.15);
--slate: #1E293B;
--slate-light: #2D3F55;
--off-white: #F8F6F1;
--text-primary: #F8F6F1;
--text-secondary: rgba(248,246,241,0.6);
--success: #10B981;
--warning: #F59E0B;
--danger: #EF4444;
```

**Typography (NEVER Inter, Roboto, Arial — these are banned):**
```css
font-display: 'Cormorant Garamond'   /* headlines, hero */
font-body:    'IBM Plex Sans'         /* all body text */
font-arabic:  'Cairo'                 /* all Arabic text */
font-data:    'IBM Plex Mono'         /* stats, numbers */
```

**Double-Bezel Card (mandatory on all cards):**
```tsx
// Outer wrapper
className="rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.1)] to-transparent border border-[rgba(201,168,76,0.15)]"

// Inner content
className="rounded-[18px] bg-[#1E293B] p-6"
```

**Custom Transitions:**
```css
/* Standard */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
/* Spring */
transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
/* Reveal */
transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
```

**Sidebar Navigation (Linear-style, dark, floating glass pill on mobile):**
```
Desktop: Fixed 240px left sidebar, dark #0A0A0A background, gold accent on active item
Mobile: Bottom tab bar, floating glass pill, 5 items max

Nav items:
- لوحة القيادة (Dashboard) — icon: LayoutDashboard
- المشاريع (Projects) — icon: FolderKanban
- صندوق الموافقة (Inbox) — icon: Inbox + badge count
- التحليلات (Analytics) — icon: BarChart3
- الإعدادات (Settings) — icon: Settings
```

---

### Page 1: / Dashboard

**Purpose:** Weekly status per project, pending approvals count, budget status, quick actions.

**Layout:**
```
[Header: "مرحبا عمر — أسبوع [X]" + date in Arabic]
[Aurora animated background on hero section]

Row 1: Stats row (CountUp animation on all numbers)
  [Pending Approvals: N] [Posts Published This Week: N] [Budget Used: SAR X/XSAR] [Active Projects: 4]

Row 2: Project Cards (SpotlightCard, AnimatedContent on reveal)
  [Therapia Card] [Qawwi Card] [ProductBench Card] [Sahmalgo Card]
  Each card shows:
  - Project name (Arabic + English)
  - Week's plan status (pending approval / approved / executing / done)
  - Pending assets count
  - Top metric vs target (app downloads this week vs goal)
  - Quick action button: "راجع الخطة" or "وافق (N)"

Row 3: Approval Queue Preview (first 3 pending items)
  [Asset thumbnail] [Channel badge] [Copy excerpt] [Approve] [Reject]
  + "عرض كل الموافقات (N)" link to /inbox
```

**React Bits components required:**
- `Aurora` — dashboard hero background (colorful aurora effect)
- `AnimatedContent` — all card sections (fade + slide up on enter)
- `SpotlightCard` — all 4 project cards (mouse-tracked spotlight effect)
- `CountUp` — all metric numbers
- `BlurText` — "مرحبا عمر" welcome heading

---

### Page 2: /projects/[id]

**Purpose:** Per-project workspace. Brand memory, weekly plan, asset history, metrics.

**Tabs:**
1. **الخطة الأسبوعية** — current WeeklyPlan with tactic rows, rationale, approve/reject
2. **الذاكرة** — ProjectMemory viewer/editor (ICP, offers, tone, funnel goals)
3. **الهوية البصرية** — BrandMemory (colors, fonts, logo, dos/don'ts, approve brand guide)
4. **المحتوى** — all assets for this project, filterable by channel/status/week
5. **التحليلات** — project-specific metrics + charts

**Weekly Plan tab layout:**
```
[Objective: large text, Arabic first]
[Funnel focus badge: awareness/consideration/conversion/retention]
[Rationale: 3-4 sentence explanation in Arabic]
[Risk flags: yellow warning badges if any]

[Approve Plan button] [Reject + note button]

Tactics list:
Each tactic row:
- Channel icon + Channel name
- Asset type badge
- Rationale simple (Arabic, 1-2 sentences)
- Budget estimate (SAR X or "مجاني")
- Expected outcome
- Status indicator
```

**Brand Memory tab layout:**
```
[Provisional banner if is_provisional=True: "هذا الـ brand guide مؤقت — وافق عليه أو عدّله"]
[Approve Brand Guide button] [Edit button]

Color palette: 5 color swatches with hex codes
Typography: font names with live Arabic + English preview text
Logo: upload area + current logo display
Dos: green-bordered list
Don'ts: red-bordered list
Visual style: text description
```

---

### Page 3: /inbox

**Purpose:** Global approval inbox. Approve or reject in one click.

**Layout:**
```
[Header: "صندوق الموافقة" + pending count badge]
[Filter tabs: الكل (All) | Therapia | Qawwi | ProductBench | Sahmalgo]
[Filter pills: خطط أسبوعية | محتوى | LinkedIn | Instagram | X]

Approval cards (AnimatedContent on enter):
Each card (double-bezel):
- [Left: asset thumbnail or plan icon]
- [Center: channel badge, asset type, language badge (AR/EN/ثنائي)]
- [Arabic copy excerpt — first 100 chars]
- [English copy excerpt — first 100 chars]
- [Funnel stage badge] [Week badge] [QA score badge]
- [Right: ✅ وافق | ❌ ارفض | ✏️ طلب تعديل]

Mobile: swipe-right = approve, swipe-left = reject (HammerJS or Framer Motion gestures)
Desktop: hover reveals action buttons

Bulk actions row (when items selected):
[Select All] [وافق على المختارة] [ارفض المختارة]
```

**Asset Preview Modal (opens on card click):**
```
[Full design preview — large]
[Arabic copy — full, RTL, Cairo font]
[English copy — below, smaller]
[QA Report accordion: all checks with pass/fail/warning]
[Channel + dimensions info]
[Approve | Reject | Request Edit with text field]
```

---

### Page 4: /plans/[week]

**Purpose:** Detailed weekly marketing plan view. Week = ISO date string (2026-05-04).

**Layout:**
```
[Week date range header — Arabic: "أسبوع 4 - 10 مايو 2026"]
[Project filter: show all or one project]

Per-project plan section:
  [Project name + status badge]
  [Objective: prominent, Arabic]
  [Funnel focus badge]
  [Budget: SAR X total | X organic | X paid]
  
  Tactic table:
  Channel | Asset Type | Funnel Stage | Rationale (Arabic) | Budget | Expected Outcome | Status
  
  [Approve Plan] [View Assets]
  
[Budget Summary footer:
  Total planned: SAR X | Total approved: SAR X | Remaining: SAR X]
```

---

### Page 5: /assets/[id]

**Purpose:** Single asset deep-dive with approval actions.

**Layout:**
```
[Breadcrumb: Project > Week > Channel > Asset]

[Left panel: Design Preview]
  Large design image (platform-correct dimensions)
  [Download] [View on platform if published]

[Right panel: Content + Actions]
  Channel badge | Asset type | Language | Status badge
  
  [Language toggle: عربي / English / ثنائي]
  
  Arabic copy section (RTL, Cairo font):
  [copy_ar]
  [CTA button preview]
  [Hashtags]
  
  English copy section (below):
  [copy_en]
  
  QA Report (accordion):
  [Score: 94/100 ✅]
  Each check: icon + name + status + note
  
  Variants (if A/B):
  [Variant A] [Variant B] toggle
  
  Action buttons (if status=approval_pending):
  [✅ وافق] [❌ ارفض] [✏️ طلب تعديل]
  
  Audit trail (collapsible):
  Timestamped log of all actions on this asset
```

---

### Page 6: /analytics

**Purpose:** Funnel + conversion metrics per project, trend charts.

**Layout:**
```
[Header: "التحليلات" + date range picker]
[Project filter tabs]

Row 1: KPI tiles (CountUp on all numbers)
  [App Downloads] [Assessments Completed] [Followers Growth] [Total Impressions]
  [Click Rate] [Posts Published] [Approval Rate] [Budget Efficiency]

Row 2: Funnel visualization
  Awareness → Consideration → Conversion → Retention
  Each stage: value + % change vs prior week + color coded (green/red)

Row 3: Channel performance table
  Channel | Posts Published | Avg Reach | Avg Engagement | Conversions | Best Post
  
Row 4: Top performing assets grid
  3-column grid of best assets with their metrics
  
Row 5: Weekly trend chart (Recharts LineChart)
  Lines for: followers, impressions, clicks, conversions (all on same chart, toggleable)
  
Row 6: Weekly report (Markdown rendered)
  The Arabic report from Analytics Agent
  [Arabic section] [English section toggle]
```

---

## 5. WEEKLY AUTOMATION CYCLE

### Cron Schedule (APScheduler, runs in backend FastAPI process)
```python
# backend/scheduler/jobs.py

scheduler.add_job(
    monday_strategy_run,
    CronTrigger(day_of_week='mon', hour=8, minute=0, timezone='Asia/Riyadh')
)

scheduler.add_job(
    monday_plan_notification,
    CronTrigger(day_of_week='mon', hour=9, minute=0, timezone='Asia/Riyadh')
)

scheduler.add_job(
    sunday_analytics_run,
    CronTrigger(day_of_week='sun', hour=18, minute=0, timezone='Asia/Riyadh')
)

# Publish queue processor — runs every 5 minutes
scheduler.add_job(
    process_publish_queue,
    IntervalTrigger(minutes=5)
)

# Approval notification batcher — runs every hour
scheduler.add_job(
    batch_approval_notifications,
    IntervalTrigger(hours=1)
)
```

### Exact Weekly Logic Flow

```python
async def monday_strategy_run():
    """Monday 8:00 AM Riyadh time"""
    active_projects = await get_active_projects()
    week_start = get_current_week_monday()
    
    for project in active_projects:
        # Run Strategy Agent
        plan = await strategy_agent.run(StrategyInput(
            project_id=project.id,
            week_start=week_start
        ))
        # Plan saved to DB with status='pending_approval'
        await create_audit_event(actor_type='scheduler', action='plan_generated', ...)

async def monday_plan_notification():
    """Monday 9:00 AM Riyadh time"""
    pending_plans = await get_pending_plan_approvals(week_start=get_current_week_monday())
    
    for plan in pending_plans:
        approval = await create_approval_record(weekly_plan_id=plan.id)
        await send_plan_approval_notification(plan, approval)
        # Email + Telegram sent

async def on_plan_approved(plan_id: str):
    """Triggered by POST /api/approvals/[id]/decide with decision='approved'"""
    plan = await get_weekly_plan(plan_id)
    
    # Run Copy Agent for all tactics in parallel
    copy_tasks = [
        copy_agent.run(CopyAgentInput(project_id=plan.project_id, tactic_id=t.id, ...))
        for t in plan.tactics
    ]
    assets = await asyncio.gather(*copy_tasks)
    
    # Run Localization Agent on each asset
    local_tasks = [
        localization_agent.run(LocalizationInput(asset_id=a.id, ...))
        for a in assets
    ]
    await asyncio.gather(*local_tasks)
    
    # Run Design Agent on each asset in parallel
    design_tasks = [
        design_agent.run(DesignAgentInput(asset_id=a.id, ...))
        for a in assets
    ]
    await asyncio.gather(*design_tasks)
    
    # Run QA Agent on each asset
    qa_tasks = [qa_agent.run(QAInput(asset_id=a.id, ...)) for a in assets]
    qa_results = await asyncio.gather(*qa_tasks)
    
    # Batch QA-passed assets → Approval Agent
    passed = [a for a, r in zip(assets, qa_results) if r.qa_passed]
    failed = [a for a, r in zip(assets, qa_results) if not r.qa_passed]
    
    if failed:
        # Log QA failures, attempt auto-fix for simple issues
        # If fix fails: flag to founder in Telegram (exception alert)
        await handle_qa_failures(failed)
    
    if passed:
        await approval_agent.run(ApprovalAgentInput(
            project_id=plan.project_id,
            mode="send_notifications"
        ))

async def on_asset_approved(asset_id: str, approval_id: str):
    """Triggered by POST /api/approvals/[id]/decide with decision='approved'"""
    asset = await get_asset(asset_id)
    
    # Create publish job — scheduled for next optimal time per channel
    scheduled_time = get_optimal_post_time(asset.channel, asset.project_id)
    publish_job = await create_publish_job(
        asset_id=asset_id,
        approval_id=approval_id,
        scheduled_at=scheduled_time
    )
    # Publish queue processor picks this up within 5 minutes of scheduled_at

async def on_asset_rejected(asset_id: str, reason: str):
    """Triggered by POST /api/approvals/[id]/decide with decision='rejected'"""
    # Store rejection as negative learning
    await update_project_memory_negative_example(asset_id, reason)
    # Notify Copy + Design agents to avoid pattern (via memory update)
    await create_audit_event(action='asset_rejected', object_id=asset_id, metadata={'reason': reason})

async def sunday_analytics_run():
    """Sunday 18:00 Riyadh time"""
    active_projects = await get_active_projects()
    week_end = date.today()
    week_start = week_end - timedelta(days=6)
    
    await analytics_agent.run(AnalyticsInput(
        project_ids=[p.id for p in active_projects],
        week_start=week_start,
        week_end=week_end
    ))
    # Report sent via email + Telegram

async def process_publish_queue():
    """Every 5 minutes — picks up ready publish jobs"""
    ready_jobs = await get_ready_publish_jobs()  # scheduled_at <= now, status=scheduled
    for job in ready_jobs:
        await publishing_agent.run(PublishingInput(publish_job_id=job.id))
```

### Optimal Post Time Logic
```python
OPTIMAL_POST_TIMES = {
    "linkedin": {"day_of_week": [1, 2, 3], "hour": 9},  # Tue-Thu 9AM Riyadh
    "instagram": {"day_of_week": [0, 2, 6], "hour": 19}, # Sun/Tue/Sat 7PM
    "x": {"day_of_week": [0, 1, 2, 3, 4], "hour": 8},   # Weekdays 8AM
    "google_ads": None  # immediate (ads don't wait for optimal time)
}
```

---

## 6. THERAPIA FIRST ONBOARDING

### Step-by-Step Flow

**Step 1: Create Therapia Project Record**
```python
# When Codex runs onboarding seed:
org = Organization(
    name="Omar's Ventures",
    owner_email="oalomran443@gmail.com",
    plan_type="internal"
)

project_therapia = Project(
    org_id=org.id,
    name="Therapia",
    slug="therapia",
    business_model="b2c",
    primary_goal="app_downloads_and_health_assessments_completed",
    website_url="https://therapia.live",
    priority=1,
    channels=[
        {"channel": "instagram", "account_id": None, "connected": False},
        {"channel": "linkedin", "account_id": None, "connected": False},
        {"channel": "x", "account_id": None, "connected": False}
    ]
)
```

**Step 2: Brand Agent Crawls therapia.live**
```python
crawl_result = await crawl_website("https://therapia.live")
brand_signals = await extract_brand_signals(crawl_result)
# Extracts: dominant colors, font names, hero text, about text, CTAs, tone words

provisional_brand = BrandMemory(
    project_id=therapia.id,
    color_palette=brand_signals.colors,
    typography=brand_signals.fonts,
    visual_style=brand_signals.detected_style,  # e.g., "clean health, light tones"
    brand_voice=brand_signals.tone_description,
    is_provisional=True  # stays True until Omar approves
)
```

**Step 3: Generate Provisional Brand Guide**
Brand Agent creates BrandMemory with all fields labeled "(provisional)".
Sends founder notification:
- Email: "تم مراجعة موقع Therapia — عندك brand guide مؤقت للموافقة"
- Telegram: "🎨 حاضر brand guide مؤقت لـ Therapia — راجعه وعدّله من هنا: [link to /projects/therapia]"

**Step 4: ProjectMemory Bootstrap**
```python
# Pull from BRD and known context:
project_memory = ProjectMemory(
    project_id=therapia.id,
    icp={
        "demographics": {
            "age_range": "25-40",
            "gender": "mixed",
            "location": "Saudi Arabia primary, GCC secondary",
            "context": "working professionals, health-conscious, mobile-first"
        },
        "pain_points": [
            "لا وقت للجلسات الوجاهية",
            "الوصم الاجتماعي حول الصحة النفسية",
            "صعوبة إيجاد متخصص موثوق"
        ],
        "goals": [
            "تحسين الصحة النفسية والجسدية",
            "بداية صحية سريعة وخاصة",
            "فهم حالتهم الصحية"
        ]
    },
    positioning="Therapia — تطبيق صحتك الشخصي في جيبك",
    offers=[{
        "name": "تقييم الصحة",
        "price": "مجاني",
        "description": "تقييم صحي شامل في دقائق",
        "cta": "ابدأ التقييم الآن",
        "landing_url": "https://therapia.live"
    }],
    tone="دافئ، داعم، إيجابي، لا يستخدم الخوف كدافع، صادق وواضح",
    languages=["ar", "en"],
    funnel_goals={
        "awareness": {"metric": "instagram_followers", "target": 5000, "current": 0},
        "consideration": {"metric": "website_visits", "target": 2000, "current": 0},
        "conversion": {"metric": "app_downloads", "target": 500, "current": 0},
        "retention": {"metric": "assessments_completed", "target": 200, "current": 0}
    },
    constraints={
        "budget_cap_sar": 2000,
        "excluded_topics": ["medical diagnoses", "clinical treatment claims", "guaranteed results"],
        "competitor_mentions_allowed": False
    }
)
```

**Step 5: Omar Approves/Edits Brand Guide**
UI at `/projects/therapia` → Brand Memory tab shows provisional guide.
Omar reviews colors, fonts, voice, dos/don'ts.
Clicks "وافق على الـ Brand Guide" → `approved_at` set, `is_provisional = False`.
Or edits fields inline → saves → then approves.

**Step 6: First Weekly Plan — Awareness Focus**
Strategy Agent generates first plan with:
- `funnel_focus = "awareness"` (week 1 = build audience first)
- All 3 tactics organic (budget cap respected)
- Simple rationale: "الأسبوع الأول — نركز على الوصول لأكبر عدد من الناس قبل ما نطلب منهم أي شيء"

Example Week 1 tactics:
1. Instagram post (bilingual) — "ليش تطبيق Therapia؟" — awareness
2. LinkedIn article (English) — "Mental health in the workplace: what Saudi PMs need to know" — consideration  
3. X thread (Arabic) — "5 علامات إنك محتاج تهتم بصحتك هالأسبوع" — awareness

**Step 7: Plan Notification → Omar Approves**
Monday 9AM: Omar receives plan via email + Telegram.
Approves in app at `/plans/[week]` or via Telegram inline button.

**Step 8: Asset Factory Runs**
Copy Agent → Localization Agent → Design Agent → QA Agent → Approval Inbox.
All 3 assets appear in `/inbox` for Omar's approval.

**Step 9: First Assets Published**
Omar approves all or individual assets.
Publishing Agent publishes to connected channels.
Confirmation: "✅ تم نشر أول محتوى لـ Therapia!"

---

## 7. CODEX IMPLEMENTATION SPEC

### Complete File Structure
```
sovereign/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout: fonts, providers, sidebar
│   │   ├── page.tsx                      # / Dashboard
│   │   ├── globals.css                   # CSS custom properties, font imports
│   │   ├── projects/
│   │   │   └── [id]/
│   │   │       └── page.tsx              # Project workspace
│   │   ├── inbox/
│   │   │   └── page.tsx                  # Global approval inbox
│   │   ├── plans/
│   │   │   └── [week]/
│   │   │       └── page.tsx              # Weekly plan detail
│   │   ├── assets/
│   │   │   └── [id]/
│   │   │       └── page.tsx              # Asset deep-dive
│   │   └── analytics/
│   │       └── page.tsx                  # Analytics dashboard
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Card.tsx                  # Double-bezel card wrapper
│   │   │   ├── Button.tsx                # Gold accent button variants
│   │   │   ├── Badge.tsx                 # Status/channel/language badges
│   │   │   ├── Sidebar.tsx               # Linear-style nav
│   │   │   ├── LanguageToggle.tsx        # AR/EN/bilingual switcher
│   │   │   └── LoadingState.tsx          # Skeleton loaders
│   │   ├── react-bits/
│   │   │   ├── Aurora.tsx                # Aurora animated background
│   │   │   ├── AnimatedContent.tsx       # Fade + slide reveal
│   │   │   ├── SpotlightCard.tsx         # Mouse-tracked spotlight
│   │   │   ├── BlurText.tsx              # Blurred text reveal
│   │   │   └── CountUp.tsx               # Animated number counter
│   │   ├── dashboard/
│   │   │   ├── DashboardHero.tsx         # Aurora hero + welcome
│   │   │   ├── StatsRow.tsx              # 4 KPI tiles with CountUp
│   │   │   ├── ProjectCard.tsx           # SpotlightCard per project
│   │   │   └── QuickApprovals.tsx        # First 3 pending items
│   │   ├── inbox/
│   │   │   ├── ApprovalCard.tsx          # Single approval item card
│   │   │   ├── ApprovalModal.tsx         # Full-screen asset preview
│   │   │   ├── SwipeActions.tsx          # Mobile swipe gestures
│   │   │   ├── InboxFilters.tsx          # Project + type filters
│   │   │   └── BulkActions.tsx           # Select all + bulk approve
│   │   ├── projects/
│   │   │   ├── ProjectTabs.tsx           # Tab navigation
│   │   │   ├── WeeklyPlanTab.tsx         # Plan view + approve
│   │   │   ├── MemoryTab.tsx             # ProjectMemory viewer
│   │   │   ├── BrandTab.tsx              # BrandMemory + approve brand
│   │   │   ├── AssetsTab.tsx             # Filtered asset grid
│   │   │   └── ProjectAnalyticsTab.tsx   # Per-project metrics
│   │   ├── plans/
│   │   │   ├── TacticRow.tsx             # Single tactic with rationale
│   │   │   └── BudgetSummary.tsx         # Budget totals footer
│   │   ├── assets/
│   │   │   ├── AssetPreview.tsx          # Design image + copy
│   │   │   ├── QAReport.tsx              # QA checks accordion
│   │   │   └── AuditTrail.tsx            # Event log
│   │   └── analytics/
│   │       ├── KPITiles.tsx              # CountUp metric tiles
│   │       ├── FunnelVisualization.tsx   # Awareness→Conversion funnel
│   │       ├── ChannelTable.tsx          # Per-channel performance
│   │       ├── TopAssetsGrid.tsx         # Best performing assets
│   │       ├── TrendChart.tsx            # Recharts line chart
│   │       └── WeeklyReportCard.tsx      # Analytics Agent report
│   ├── lib/
│   │   ├── api.ts                        # Typed API client (fetch wrapper)
│   │   ├── types.ts                      # All TypeScript interfaces matching DB
│   │   └── constants.ts                  # Channel colors, funnel labels AR/EN
│   ├── hooks/
│   │   ├── useProjects.ts                # SWR hook for projects list
│   │   ├── useProject.ts                 # SWR hook for single project
│   │   ├── useApprovals.ts               # SWR hook for pending approvals
│   │   ├── useWeeklyPlan.ts              # SWR hook for plan
│   │   └── useMetrics.ts                 # SWR hook for analytics
│   ├── public/
│   │   └── fonts/                        # Self-hosted font files
│   │       ├── CormorantGaramond-Regular.woff2
│   │       ├── IBMPlexSans-Regular.woff2
│   │       ├── IBMPlexMono-Regular.woff2
│   │       └── Cairo-Regular.woff2
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── next.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI app, routers, CORS, startup
│   │   ├── config.py                     # Pydantic Settings from env
│   │   ├── database.py                   # SQLAlchemy async engine + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── project.py
│   │   │   ├── project_memory.py
│   │   │   ├── brand_memory.py
│   │   │   ├── weekly_plan.py
│   │   │   ├── asset.py
│   │   │   ├── approval.py
│   │   │   ├── publish_job.py
│   │   │   ├── metric_snapshot.py
│   │   │   └── audit_event.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── project.py
│   │   │   ├── memory.py
│   │   │   ├── weekly_plan.py
│   │   │   ├── asset.py
│   │   │   ├── approval.py
│   │   │   ├── publish_job.py
│   │   │   └── analytics.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py               # GET/POST/PATCH /projects
│   │   │   ├── memory.py                 # GET/PATCH /projects/{id}/memory
│   │   │   ├── brand.py                  # GET/PATCH /projects/{id}/brand
│   │   │   ├── plans.py                  # GET/POST /plans, GET /plans/{id}
│   │   │   ├── assets.py                 # GET/POST /assets, PATCH /assets/{id}
│   │   │   ├── approvals.py              # POST /approvals/{id}/decide
│   │   │   ├── publish.py                # GET /publish-jobs
│   │   │   ├── analytics.py              # GET /metrics, GET /metrics/summary
│   │   │   └── webhook.py                # POST /webhook/telegram (Telegram updates)
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # BaseAgent class: Claude API loop
│   │   │   ├── strategy.py               # StrategyAgent
│   │   │   ├── brand.py                  # BrandAgent
│   │   │   ├── copy.py                   # CopyAgent
│   │   │   ├── design.py                 # DesignAgent
│   │   │   ├── localization.py           # LocalizationAgent
│   │   │   ├── qa.py                     # QAAgent
│   │   │   ├── approval_agent.py         # ApprovalAgent
│   │   │   ├── publishing.py             # PublishingAgent
│   │   │   └── analytics_agent.py        # AnalyticsAgent
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── memory_tools.py           # get/update project_memory + brand_memory
│   │   │   ├── crawl_tools.py            # httpx + BeautifulSoup website crawler
│   │   │   ├── fal_tools.py              # fal.ai API client (image gen)
│   │   │   ├── r2_tools.py               # Cloudflare R2 boto3 client
│   │   │   ├── image_tools.py            # Pillow: text overlay, resize, thumbnail
│   │   │   ├── social_tools.py           # LinkedIn, Instagram, X API clients
│   │   │   ├── google_tools.py           # Google Ads + Analytics API clients
│   │   │   └── notify_tools.py           # Resend email + Telegram Bot API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── approval_service.py       # Decision handler: approve/reject logic
│   │   │   ├── publish_service.py        # Queue processor, retry logic
│   │   │   └── metrics_service.py        # Metric aggregation + comparisons
│   │   └── scheduler/
│   │       ├── __init__.py
│   │       └── jobs.py                   # APScheduler job definitions
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py     # All 10 tables
│   ├── scripts/
│   │   └── seed_therapia.py              # Therapia onboarding seed script
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
│
├── SOVEREIGN_SPEC.md
├── SOVEREIGN_CODEX_TASK.md
├── .env.example
├── .gitignore
└── railway.toml
```

---

### 30-Step Build Order (Codex executes in this exact order)

**PHASE 0: FOUNDATION** *(Steps 1-5)*

**Step 1: Repo Init**
- Create directory structure above (all folders, empty files)
- `git init`
- Create `.gitignore` (must exclude: `.env`, `*.pyc`, `__pycache__`, `.next`, `node_modules`, `*.woff2` if large)
- Create `.env.example` with all vars listed in Section 1
- Create `railway.toml` with two services: frontend + backend
- SUCCESS: `git status` shows clean repo with all folders present

**Step 2: Backend Foundation**
- `cd backend && python -m venv venv && pip install fastapi uvicorn sqlalchemy asyncpg alembic pgvector anthropic fal pillow boto3 httpx beautifulsoup4 apscheduler python-telegram-bot resend pydantic-settings`
- Create `requirements.txt` from pip freeze
- Create `app/config.py` with Pydantic Settings class reading all env vars
- Create `app/database.py` with async SQLAlchemy engine + SessionLocal + get_db dependency
- Create `app/main.py` with basic FastAPI app, CORS configured for frontend URL
- SUCCESS: `uvicorn app.main:app --reload` starts without errors

**Step 3: Database Models**
- Create all 10 SQLAlchemy models in `app/models/` (one file per model)
- Each model mirrors the SQL schema in Section 2 exactly
- All models import from `app/database.py`
- Create `app/models/__init__.py` exporting all models
- SUCCESS: `python -c "from app.models import *; print('models OK')"` exits 0

**Step 4: Alembic Migration**
- `alembic init migrations`
- Configure `alembic.ini` with DATABASE_URL_SYNC
- Configure `migrations/env.py` to import all models for autogenerate
- `alembic revision --autogenerate -m "initial_schema"`
- Review generated migration — verify all 10 tables + extensions + indexes present
- `alembic upgrade head`
- SUCCESS: `psql $DATABASE_URL -c "\dt"` lists all 10 tables

**Step 5: Pydantic Schemas**
- Create all Pydantic schema files in `app/schemas/`
- Each schema mirrors its model: Base, Create, Update, Response variants
- SUCCESS: `python -c "from app.schemas import *; print('schemas OK')"` exits 0

---

**PHASE 1: API LAYER** *(Steps 6-10)*

**Step 6: Projects Router**
- `GET /api/projects` — list all projects for org
- `POST /api/projects` — create project
- `GET /api/projects/{id}` — get single project with memory + brand summary
- `PATCH /api/projects/{id}` — update project
- Include router in `main.py`
- SUCCESS: `curl http://localhost:8000/api/projects` returns `[]` (empty list)

**Step 7: Memory Router**
- `GET /api/projects/{id}/memory` — get project memory
- `PATCH /api/projects/{id}/memory` — update memory fields
- `GET /api/projects/{id}/brand` — get brand memory
- `PATCH /api/projects/{id}/brand` — update brand memory
- `POST /api/projects/{id}/brand/approve` — set is_provisional=False, approved_at=now
- SUCCESS: All endpoints return 200 with correct schema

**Step 8: Plans Router**
- `GET /api/plans?project_id=&week_start=` — list plans
- `GET /api/plans/{id}` — get single plan
- `POST /api/plans` — create plan (used by Strategy Agent)
- SUCCESS: Plan CRUD works end-to-end

**Step 9: Assets Router**
- `GET /api/assets?project_id=&status=&channel=` — list assets with filters
- `GET /api/assets/{id}` — get asset with full details
- `POST /api/assets` — create asset record
- `PATCH /api/assets/{id}` — update asset (status, design_url, qa_score)
- SUCCESS: Asset CRUD works end-to-end

**Step 10: Approvals Router**
- `POST /api/approvals` — create approval record
- `GET /api/approvals?project_id=&status=pending` — list pending approvals
- `POST /api/approvals/{id}/decide` — submit decision (approved/rejected/edit_requested)
  - Triggers: on approved → create publish job; on rejected → update memory
- `POST /api/webhook/telegram` — handle Telegram inline keyboard callbacks
- SUCCESS: Full approve → publish job creation flow works

---

**PHASE 2: AGENT TOOLS** *(Steps 11-13)*

**Step 11: Memory + Crawl Tools**
- `app/tools/memory_tools.py`:
  - `get_project_memory(db, project_id)` → ProjectMemory ORM object
  - `update_project_memory(db, project_id, updates)` → updated object
  - `get_brand_memory(db, project_id)` → BrandMemory ORM object
  - `update_brand_memory(db, project_id, updates)` → updated object
- `app/tools/crawl_tools.py`:
  - `crawl_website(url)` → httpx GET homepage + about + /brand pages
  - `extract_brand_signals(crawl_result)` → colors, fonts, tone, CTAs
  - Uses BeautifulSoup for parsing, extracts: title, meta description, OG image, computed CSS colors (via meta tags), Google Font references, tone adjectives from hero copy
- SUCCESS: `crawl_website("https://therapia.live")` returns structured dict

**Step 12: Image + Storage Tools**
- `app/tools/fal_tools.py`:
  - `generate_image_fal(prompt, model, width, height)` → bytes
  - model: "fal-ai/flux/schnell" or "fal-ai/flux-pro"
- `app/tools/r2_tools.py`:
  - `upload_to_r2(file_bytes, filename, content_type)` → public URL string
  - `get_signed_url(filename, expiry_seconds=3600)` → signed URL
- `app/tools/image_tools.py`:
  - `apply_text_overlay(image_bytes, text_ar, text_en, arabic_font_url, config)` → bytes
  - `resize_image(image_bytes, width, height)` → bytes
  - `create_thumbnail(image_bytes, max_size=400)` → bytes
- SUCCESS: Full pipeline test: generate_image_fal → apply_text_overlay → upload_to_r2 → returns URL

**Step 13: Notify + Social Tools**
- `app/tools/notify_tools.py`:
  - `send_email_resend(to, subject, html)` → bool
  - `send_telegram_notification(chat_id, text, keyboard=None)` → bool
  - `setup_telegram_webhook(webhook_url)` — registers webhook with Telegram API
- `app/tools/social_tools.py`:
  - `publish_to_linkedin(asset, org_id, access_token)` → post_id str
  - `publish_to_instagram(asset, user_id, access_token)` → post_id str
  - `publish_to_twitter(asset, credentials)` → tweet_id str
- SUCCESS: Test Telegram notification sent to TELEGRAM_CHAT_ID

---

**PHASE 3: AGENT CORE** *(Steps 14-20)*

**Step 14: Base Agent**
- `app/agents/base.py`:
  - `BaseAgent` class with `run(input)` method
  - Implements Anthropic tool-use loop:
    1. Call `anthropic.messages.create` with system_prompt, user_message, tools
    2. While `stop_reason == "tool_use"`: execute tool calls, append results
    3. Return final text response when `stop_reason == "end_turn"`
  - Tool registry: each agent registers its tools as callables
  - Error handling: retry on API errors (max 3), log all tool calls
  - All calls use `claude-sonnet-4-20250514`
- SUCCESS: Test agent completes a simple tool-use loop

**Step 15: Strategy Agent**
- Implements system prompt from Section 3
- Tools: get_project_memory, get_brand_memory, get_metric_history, get_previous_plans, save_weekly_plan, create_audit_event
- Output validates against WeeklyPlanOutput schema
- SUCCESS: Run with Therapia project_id → generates WeeklyPlan saved to DB with status=draft

**Step 16: Brand Agent**
- Implements system prompt from Section 3
- Tools: crawl_website, extract_brand_signals, get_brand_memory, save_brand_memory, update_brand_memory, upload_asset_r2, create_approval_request, create_audit_event
- SUCCESS: Run with Therapia → crawls therapia.live → saves provisional BrandMemory

**Step 17: Copy Agent**
- Implements system prompt from Section 3
- Tools: get_project_memory, get_brand_memory, get_weekly_plan, get_approved_examples, get_rejected_examples, save_asset, create_audit_event
- SUCCESS: Run for one Therapia tactic → generates asset with copy_ar + copy_en

**Step 18: Localization Agent**
- Implements system prompt from Section 3
- Tools: get_project_memory, get_brand_memory, get_asset, update_asset, check_rtl_rendering, create_audit_event
- SUCCESS: Run on asset from Step 17 → updates copy_ar to native Gulf Arabic

**Step 19: Design Agent**
- Implements system prompt from Section 3
- Tools: get_brand_memory, get_asset, generate_image_fal, apply_text_overlay, resize_image, upload_to_r2, create_thumbnail, update_asset, create_audit_event
- SUCCESS: Run on asset → design_url + thumbnail_url saved to R2, asset record updated

**Step 20: QA Agent**
- Implements system prompt from Section 3
- Tools: get_brand_memory, get_asset, get_rejected_examples, analyze_image_colors, check_rtl_rendering, check_text_contrast, update_asset, create_audit_event
- SUCCESS: Run on asset from Step 19 → qa_score populated, status updated to qa_passed or qa_failed

---

**PHASE 4: PUBLISHING PIPELINE** *(Steps 21-24)*

**Step 21: Approval Agent**
- Implements system prompt from Section 3
- Tools: get_qa_passed_assets, create_approval_record, send_email_resend, send_telegram_notification, update_asset_status, create_audit_event
- SUCCESS: Run → creates approval records + sends email + Telegram notification with asset summary

**Step 22: Approval Service**
- `app/services/approval_service.py`:
  - `handle_approval_decision(approval_id, decision, reason)`:
    - If approved + asset: create PublishJob, update asset status=approved
    - If approved + plan: update plan status=approved, trigger on_plan_approved flow
    - If rejected: update status=rejected, call update_project_memory_negative_example
    - If edit_requested: update status=edit_requested, store edit_instructions
  - `update_project_memory_negative_example(asset_id, reason)`: updates rejected_examples in ProjectMemory
- SUCCESS: POST /api/approvals/{id}/decide?decision=approved creates PublishJob

**Step 23: Publishing Agent + Service**
- `app/agents/publishing.py`: implements system prompt from Section 3
- `app/services/publish_service.py`:
  - `process_publish_queue()`: fetches ready jobs, calls PublishingAgent per job
  - `handle_publish_failure(job_id, error)`: increment retry, alert if max_retries reached
- SUCCESS: Full end-to-end: approve asset → publish job created → agent publishes → platform_post_id saved

**Step 24: Analytics Agent**
- Implements system prompt from Section 3
- `app/tools/google_tools.py`: Google Analytics + Google Ads clients
- SUCCESS: Run analytics agent → metrics saved to metric_snapshots, weekly report sent via Telegram

---

**PHASE 5: SCHEDULER** *(Step 25)*

**Step 25: APScheduler Jobs**
- `app/scheduler/jobs.py`: all 4 cron jobs from Section 5
- Integrate scheduler start into `app/main.py` lifespan event
- Use Asia/Riyadh timezone for all crons
- SUCCESS: Scheduler starts with app, `monday_strategy_run` logs trigger at correct time (verify in dev with a 1-minute test cron)

---

**PHASE 6: FRONTEND** *(Steps 26-29)*

**Step 26: Next.js Setup + Design System**
- `cd frontend && npx create-next-app@14 . --typescript --tailwind --app`
- Install: `swr framer-motion recharts react-swipeable lucide-react`
- Configure `tailwind.config.ts` with all custom colors from design system
- Create `app/globals.css` with CSS custom properties + `@font-face` for all 4 fonts
- Create `components/ui/Card.tsx` — double-bezel card component
- Create `components/ui/Button.tsx` — gold accent + ghost + danger variants
- Create `components/ui/Badge.tsx` — status/channel/language variants
- Create `components/react-bits/` — copy Aurora, AnimatedContent, SpotlightCard, BlurText, CountUp from reactbits.dev (TypeScript + Tailwind variants)
- Create `lib/api.ts` — typed fetch wrapper with base URL from env
- Create `lib/types.ts` — TypeScript interfaces for all DB entities
- SUCCESS: `npm run build` exits 0, no TypeScript errors

**Step 27: Sidebar + Dashboard**
- Create `components/ui/Sidebar.tsx` — 240px fixed left, dark, gold active state, bottom tab bar on mobile
- Create `app/layout.tsx` — Sidebar + main content area
- Create `components/dashboard/DashboardHero.tsx` — Aurora + BlurText welcome
- Create `components/dashboard/StatsRow.tsx` — 4 tiles, CountUp on all numbers
- Create `components/dashboard/ProjectCard.tsx` — SpotlightCard, AnimatedContent
- Create `components/dashboard/QuickApprovals.tsx` — first 3 pending
- Create `app/page.tsx` — compose dashboard
- SUCCESS: `npm run dev` → `localhost:3000` loads dashboard with Aurora animation

**Step 28: Inbox Page**
- Create `components/inbox/ApprovalCard.tsx` — double-bezel, thumbnail, copy, action buttons
- Create `components/inbox/ApprovalModal.tsx` — full-screen preview on click
- Create `components/inbox/SwipeActions.tsx` — Framer Motion swipe-right=approve, swipe-left=reject
- Create `components/inbox/InboxFilters.tsx` — project + type filter pills
- Create `app/inbox/page.tsx` — full inbox with AnimatedContent reveal
- SUCCESS: Approval card visible, clicking opens modal, approve button calls POST /api/approvals/{id}/decide

**Step 29: All Remaining Pages**
- `app/projects/[id]/page.tsx` + all project tab components
- `app/plans/[week]/page.tsx` + TacticRow + BudgetSummary
- `app/assets/[id]/page.tsx` + AssetPreview + QAReport + AuditTrail
- `app/analytics/page.tsx` + all analytics components (Recharts line chart, funnel)
- All pages use `swr` hooks from `hooks/` directory
- SUCCESS: All 6 routes return 200, no console errors, Arabic text renders RTL

---

**PHASE 7: SEED + DEPLOY** *(Step 30)*

**Step 30: Therapia Seed + Railway Deploy**
- Create `backend/scripts/seed_therapia.py`:
  - Creates Organization, Therapia Project, initial ProjectMemory, initial BrandMemory (provisional)
  - Runs Brand Agent to crawl therapia.live
  - Saves output to DB
- Create `railway.toml`:
  ```toml
  [[services]]
  name = "sovereign-backend"
  source = "backend/"
  build_command = "pip install -r requirements.txt && alembic upgrade head"
  start_command = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

  [[services]]
  name = "sovereign-frontend"
  source = "frontend/"
  build_command = "npm ci && npm run build"
  start_command = "npm start"
  ```
- Push to GitHub, connect to Railway
- Set all env vars in Railway dashboard (from .env.example)
- Run: `python scripts/seed_therapia.py` on Railway or locally with prod DB URL
- SUCCESS:
  - `curl https://sovereign-backend.railway.app/api/projects` → returns Therapia project
  - `https://sovereign-frontend.railway.app` → loads dashboard with Therapia card
  - Therapia ProjectMemory + provisional BrandMemory exist in DB

---

### Success Criteria Per Phase

| Phase | Exit Criteria |
|-------|--------------|
| 0: Foundation | `alembic upgrade head` succeeds, all 10 tables exist in DB |
| 1: API Layer | All 5 routers return correct responses, Postman/curl tests pass |
| 2: Agent Tools | Image pipeline test produces valid R2 URL, Telegram notification received |
| 3: Agent Core | Full agent test: Therapia → WeeklyPlan → Asset(copy) → Asset(design) saved to DB |
| 4: Publishing | Full end-to-end: approve → publish job → (mock) publish → platform_post_id saved |
| 5: Scheduler | Scheduler logs trigger at correct Riyadh time, no runtime errors |
| 6: Frontend | All 6 routes 200, no TS errors, Arabic RTL visible, Aurora animation plays |
| 7: Deploy | Both Railway services healthy, Therapia seed data visible in production |

---

### How to Test Each Agent

```bash
# Test Strategy Agent
cd backend
python -c "
import asyncio
from app.agents.strategy import StrategyAgent
from app.agents.base import StrategyInput
from datetime import date

agent = StrategyAgent()
result = asyncio.run(agent.run(StrategyInput(
    project_id='[therapia-project-uuid]',
    week_start=date(2026, 5, 11)
)))
print(result)
assert result.tactics, 'No tactics generated'
assert len(result.tactics) >= 3, 'Too few tactics'
print('Strategy Agent: PASS')
"

# Test Brand Agent
python -c "
import asyncio
from app.agents.brand import BrandAgent
from app.agents.base import BrandAgentInput

agent = BrandAgent()
result = asyncio.run(agent.run(BrandAgentInput(
    project_id='[therapia-project-uuid]',
    mode='init'
)))
assert result.color_palette, 'No colors extracted'
print('Brand Agent: PASS')
"

# Test Copy Agent
python -c "
import asyncio
from app.agents.copy import CopyAgent
from app.agents.base import CopyAgentInput

agent = CopyAgent()
result = asyncio.run(agent.run(CopyAgentInput(
    project_id='[therapia-project-uuid]',
    weekly_plan_id='[plan-uuid]',
    tactic_id='[tactic-uuid]',
    channel='instagram',
    asset_type='post',
    language='bilingual',
    funnel_stage='awareness'
)))
assert result.copy_ar, 'No Arabic copy generated'
assert result.copy_en, 'No English copy generated'
print('Copy Agent: PASS')
"

# Test QA Agent
python -c "
import asyncio
from app.agents.qa import QAAgent
from app.agents.base import QAInput

agent = QAAgent()
result = asyncio.run(agent.run(QAInput(
    asset_id='[asset-uuid]',
    project_id='[therapia-project-uuid]'
)))
assert result.qa_score is not None, 'No QA score'
print(f'QA Agent: PASS — score={result.qa_score}')
"

# Test full weekly cycle (integration test)
python -c "
import asyncio
from app.scheduler.jobs import monday_strategy_run

asyncio.run(monday_strategy_run())
print('Weekly Cycle: PASS')
"
```

---

### Critical Implementation Notes for Codex

1. **Arabic text**: Every string destined for Arabic output must have `dir="rtl"` in HTML and `direction: rtl` in CSS. Never mix LTR and RTL in the same text block without proper Unicode bidi handling.

2. **Provisional brand guide**: Always check `brand_memory.is_provisional` before using brand colors/fonts in Design Agent. If provisional, add warning to QA notes but do NOT block.

3. **Approval gate**: The check `approval.decision == 'approved' AND approval.decided_at IS NOT NULL` must be implemented as a DB-level query, not just in-memory. Publishing Agent must re-query the DB, not trust cached state.

4. **Environment safety**: NEVER fall back to hardcoded values if env vars are missing. Raise `ValueError` at startup if any required env var is absent. Use Pydantic Settings validators.

5. **Telegram webhook**: Set up Telegram webhook via `POST https://api.telegram.org/bot{TOKEN}/setWebhook` pointing to `/api/webhook/telegram`. Handle `callback_query` updates for inline keyboard buttons.

6. **fal.ai async**: Use `fal.run()` not `fal.subscribe()` for simplicity in MVP. Handle timeouts (max 60 seconds for flux-pro).

7. **R2 public URLs**: Generate signed URLs for asset previews in frontend (valid for 1 hour). Never expose R2 bucket as fully public.

8. **pgvector**: Only compute embeddings for assets with status `approval_pending` or higher. Use `text-embedding-3-small` from OpenAI OR use Anthropic embeddings if available. Store as `vector(1536)`.

9. **No mock data in production**: Seed script creates real project records. No hardcoded fake metrics. If metrics API fails, store error in MetricSnapshot.metadata and skip.

10. **Railway multi-service**: Both services share the same PostgreSQL Railway addon. Backend gets the DATABASE_URL from Railway. Frontend is static Next.js — no direct DB access, all through backend API.

---

*SOVEREIGN_SPEC.md — Complete. Hand to Codex.*
*Omar approves. Ale ships quality. Sovereign runs autonomously.*
