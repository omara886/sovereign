# SOVEREIGN V3 — Monster Implementation Plan
# For Codex. Read every word. No shortcuts. No assumptions.
# Generated: 2026-05-10 after full audit of all 4 root causes.

---

## THE 4 ROOT CAUSES (audit findings — understand before touching anything)

### ROOT CAUSE 1 — Images broken
`r2_tools.py` defines `_MAX_BASE64_BYTES = 300 * 1024` on line 14 but NEVER uses it.
Result: fal.ai design images (1-4MB) get base64'd → browser `<img src="data:...4MB...">` → black box.
Logos under 300KB work fine. Designs never show.
Fix: enforce the 300KB cap. Designs go to /tmp serve URL. Accept they're ephemeral until R2 is configured.
For logos/screenshots uploaded by user: base64 is correct (small files = permanent).

### ROOT CAUSE 2 — UX unclear
No onboarding. No step numbers. No "do this first" guidance anywhere.
Dashboard shows 4 project cards with identical buttons. New user has no idea what order to follow.
Pipeline tab shows "Approve Plan" button greyed out with no explanation why.
Empty states say nothing actionable.

### ROOT CAUSE 3 — Arabic sounds Egyptian / formal
Localization Agent runs on HAIKU — weaker Arabic dialect differentiation.
`approved_examples = []` and `rejected_examples = []` in every project — agents have zero real examples to anchor to.
`tone` field in seed says "دافئ، داعم" but no actual Gulf vocabulary or forbidden phrases.
Localization Agent `_get_project_memory` doesn't pass `approved_examples` to the agent.

### ROOT CAUSE 4 — Content sounds AI / robotic
Copy Agent outputs full JSON in one shot — JSON mode produces declarative, structured sentences.
Two rewrites (Copy Agent → Localization Agent) each pass through JSON schema → doubly robotic.
`brand_voice` still marked `(provisional)` → agent writes cautiously/generically.
No real rejection examples → no style learning has happened.

---

## IMPLEMENTATION ORDER

Steps 1-4: Fix images + fix agent quality (most impactful, backend only)
Steps 5-7: Fix UX clarity (frontend guided flow)
Steps 8-10: Fix Arabic content quality (agent prompts + memory)
Steps 11-12: Fix design premium feel (visual polish)

---

## STEP 1 — Fix r2_tools: enforce 300KB cap on base64

**File:** `backend/app/tools/r2_tools.py`

**What to change:** Restore the `_MAX_BASE64_BYTES` enforcement that was accidentally removed.

```python
async def upload_to_r2(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    client = _get_client()
    bucket = settings.R2_BUCKET_NAME
    public_base = settings.R2_PUBLIC_URL or ""

    # Strategy 1: Real R2
    if client and bucket:
        import asyncio
        await asyncio.to_thread(client.put_object, Bucket=bucket, Key=filename, Body=file_bytes, ContentType=content_type)
        return f"{public_base.rstrip('/')}/{filename}"

    # Strategy 2: Small images only → base64 (permanent, browser-renderable)
    # 300KB limit: user logos/screenshots are small. fal.ai designs are 1-4MB → use Strategy 3.
    if content_type in _IMAGE_TYPES and len(file_bytes) <= _MAX_BASE64_BYTES:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return f"data:{content_type};base64,{b64}"

    # Strategy 3: Large files → /tmp serve (ephemeral, breaks on restart — acceptable for generated designs)
    target = Path("/tmp/sovereign_r2") / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)
    backend_base = settings.BACKEND_PUBLIC_URL or "https://backend-production-37a17.up.railway.app"
    return f"{backend_base.rstrip('/')}/api/uploads/serve/{filename}"
```

**Also fix `_download_file` in `asset_analyzer.py`** to handle data: URLs:
```python
async def _download_file(url: str) -> bytes | None:
    # Handle base64 data URLs (logos stored without R2)
    if url.startswith("data:"):
        try:
            _, encoded = url.split(",", 1)
            return base64.b64decode(encoded)
        except Exception:
            return None
    if url.startswith("file://"):
        path = Path(url.replace("file://", ""))
        return path.read_bytes() if path.exists() else None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            return r.content if r.status_code == 200 else None
    except Exception:
        return None
```

**Success test:**
```bash
python -c "
import asyncio
from app.tools.r2_tools import upload_to_r2, _MAX_BASE64_BYTES

async def test():
    # Small image → base64
    small = b'PNG' * 1000  # ~3KB
    url = await upload_to_r2(small, 'test/logo.png', 'image/png')
    assert url.startswith('data:'), f'Small image should be base64, got: {url[:30]}'

    # Large image → serve URL
    large = b'PNG' * 200000  # ~600KB
    url = await upload_to_r2(large, 'test/design.png', 'image/png')
    assert '/api/uploads/serve/' in url, f'Large image should be serve URL, got: {url[:30]}'
    print('PASS')

asyncio.run(test())
"
```

---

## STEP 2 — Fix Localization Agent: use Sonnet + pass examples

**File:** `backend/app/agents/localization.py`

**Change 1:** Switch from Haiku to Sonnet for Arabic quality.
```python
class LocalizationAgent(BaseAgent):
    MODEL = SONNET  # was HAIKU — Gulf Arabic dialect needs Sonnet's stronger language model
```

**Change 2:** Pass `approved_examples` and `rejected_examples` to agent via `_get_project_memory`:
```python
async def _get_project_memory(self, db: AsyncSession, project_id: str) -> dict:
    mem = await get_project_memory(db, project_id)
    if not mem:
        return {"error": "not found"}
    return {
        "tone": mem.tone,
        "languages": mem.languages,
        "icp": mem.icp,
        "approved_examples": mem.approved_examples,   # ADD THIS
        "rejected_examples": mem.rejected_examples,   # ADD THIS
        "constraints": mem.constraints,               # ADD THIS
    }
```

**Change 3:** Update system prompt to include Gulf-specific vocabulary and forbidden phrases:

Replace the existing SYSTEM_PROMPT with:
```python
SYSTEM_PROMPT = """You are a native Gulf Saudi Arabic copywriter. You ONLY write in Saudi Gulf dialect.

GULF SAUDI VOCABULARY (USE THESE):
- خل = let's / just
- شوف = see / check out
- وش = what
- يبيلك = you need
- ما صار = it's not right / unacceptable
- الحين = now (not الآن)
- يلا = let's go / come on
- جرّب = try it
- تمام = perfect / great
- أحسن = better

FORBIDDEN WORDS (NEVER USE — these are Egyptian or formal):
- يا صديقي (Egyptian)
- حبيبي (Lebanese/Egyptian)
- ازيك / إيه الأخبار (Egyptian)
- تفضّل (formal)
- عزيزي المستخدم (corporate)
- أي فصحى unless context is explicitly formal/legal
- نفسي / نفسية / علاج / طب نفسي (excluded topics)

WRITING STYLE:
- Write like a WhatsApp message to a friend, not a marketing email
- Short sentences. Max 2-3 lines per paragraph.
- Start strong: "خل نكون صريحين..." / "وش يصير..." / "تعرف إيش؟"
- End with specific action: "جرّب الحين" / "ابدأ اليوم" / "شوف الفرق"
- Use emoji sparingly (1-2 max) — 💪 ✅ are fine

NEVER:
- Translate from English word-for-word
- Use generic CTAs like "اضغط هنا"
- Sound like a doctor or corporation
- Sound like an AI wrote it

Read approved_examples in project memory — write in the same register.
Read rejected_examples — avoid those exact patterns.
Read constraints.excluded_topics — never mention those words.

Output JSON: {"copy_ar": "...", "copy_en": "...", "cta_ar": "...", "cta_en": "..."}"""
```

**Success test:** Run pipeline → check generated Arabic copy:
```bash
python -c "
import asyncio
from app.database import SessionLocal
from app.agents.localization import LocalizationAgent
from app.models.project import Project
from sqlalchemy import select

async def test():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.slug == 'therapia'))).scalar_one()
        agent = LocalizationAgent()
        result = await agent.localize(db, str(p.id), 'Try Therapia app today for better health', 'instagram', 'awareness', 'bilingual')
        ar = result.get('copy_ar', '')
        print('Arabic:', ar[:200])
        # Must not contain Egyptian markers
        forbidden = ['يا صديقي', 'حبيبي', 'ازيك', 'تفضّل', 'نفسي', 'نفسية']
        found = [f for f in forbidden if f in ar]
        assert not found, f'Found forbidden words: {found}'
        print('PASS — no forbidden words detected')

asyncio.run(test())
"
```

---

## STEP 3 — Fix Copy Agent: free-form Arabic first, then extract JSON

**File:** `backend/app/agents/copy.py`

**Problem:** JSON output mode produces robotic declarative sentences.
**Fix:** Two-phase output — write copy naturally first, then structure it.

Update SYSTEM_PROMPT:
```python
SYSTEM_PROMPT = """You are a Saudi Gulf marketing copywriter. Write HUMAN copy, not AI copy.

ALWAYS read project memory first (get_project_memory + get_brand_memory).
Use ONLY facts from ProjectMemory. Never invent product features.
Never write anything in constraints.excluded_topics.

WRITING RULES:
1. Write like a real person wrote it — not like it came from a template
2. Avoid starting sentences with "Are you...", "Do you...", "Discover...", "Unlock..."
3. Avoid numbered lists that read like instructions
4. Avoid corporate words: "leverage", "empower", "transform", "journey", "revolutionize"
5. Use specific numbers and concrete details instead of vague claims
6. For Arabic: Gulf Saudi dialect ONLY. Read the approved_examples for the exact register.
7. CTA must be specific to the offer in project memory — not generic

PER-CHANNEL LIMITS (strict):
- Instagram: 80-150 word caption, 5-8 hashtags
- LinkedIn: 150-300 words, professional but human, 1-3 hashtags  
- X/Twitter: ≤270 chars
- Google Ads: Headline ≤30 chars, Description ≤90 chars

Quality check before outputting:
- Does this sound like a human wrote it?
- Is every sentence earning its place?
- Would a Saudi reader find this cringe or robotic? Fix if yes.

Output JSON:
{
  "copy_ar": "Gulf Arabic copy",
  "copy_en": "English copy",
  "cta_ar": "Arabic CTA from offers list",
  "cta_en": "English CTA",
  "hashtags_ar": [],
  "hashtags_en": [],
  "claim_flags": []
}"""
```

**Success test:** Generate copy and check it doesn't contain AI clichés:
```bash
python -c "
import asyncio, json
from app.database import SessionLocal
from app.agents.copy import CopyAgent
from app.models.project import Project
from sqlalchemy import select

BANNED_PHRASES = ['unlock', 'leverage', 'empower', 'transform', 'journey', 'revolutionize',
                  'Are you tired', 'Do you want', 'Discover the', 'experience the']

async def test():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.slug == 'therapia'))).scalar_one()
        agent = CopyAgent()
        result = await agent.generate_copy(db, str(p.id), 'instagram', 'post', 'awareness', 'bilingual')
        en = result.get('copy_en', '')
        print('English copy:', en[:200])
        found = [bp for bp in BANNED_PHRASES if bp.lower() in en.lower()]
        assert not found, f'AI clichés detected: {found}'
        print('PASS — no AI clichés')

asyncio.run(test())
"
```

---

## STEP 4 — Seed real approved/rejected examples in Therapia memory

**File:** `backend/scripts/seed_therapia_examples.py` (create new file)

```python
"""
Seed real Gulf Saudi approved examples + rejected examples for Therapia.
Run: python -m scripts.seed_therapia_examples
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from app.database import SessionLocal
from app.models.project import Project
from app.models.project_memory import ProjectMemory
from app.models.brand_memory import BrandMemory

APPROVED_EXAMPLES = [
    {
        "channel": "instagram",
        "copy_ar": "وش يصير لما تنام 8 ساعات كل يوم؟\n\nجسمك يشكرك، تركيزك يزيد، ومزاجك يتحسن.\n\nجرّب Therapia لمدة أسبوع — سجّل نومك، شوف الفرق بنفسك 💪\n\nابدأ الحين ←",
        "copy_en": "What happens when you sleep 8 hours every day?\n\nYour body thanks you. Your focus sharpens. Your mood lifts.\n\nTry Therapia for one week — track your sleep, see the difference yourself.\n\nStart now →",
        "why_it_works": "Opens with a question, uses خل vocabulary, specific benefit, clear CTA",
        "channel_format": "instagram_post"
    },
    {
        "channel": "instagram",
        "copy_ar": "ستة أشهر من متابعة صحتي مع Therapia — وش تغير؟\n\n✅ شربت ماء أكثر\n✅ نمت أبكر\n✅ حسيت بفرق واضح\n\nما احتجت دكتور. احتجت نظام.\n\nTherapia يساعدك تبني العادة الصح 🏃",
        "copy_en": "Six months tracking my health with Therapia — what changed?\n\nDrank more water. Slept earlier. Felt the difference.\n\nDidn't need a doctor. Needed a system.\n\nTherapia helps you build the right habits.",
        "why_it_works": "Specific timeframe, concrete habits, relatable, not medical",
        "channel_format": "instagram_post"
    },
    {
        "channel": "instagram",
        "copy_ar": "الصحة مو بس الجيم.\n\nالنوم. الماء. الخطوات. الضغط.\n\nTherapia يجمع كل هذا في مكان واحد — تتابعه يومياً بدون تعقيد.",
        "copy_en": "Health is not just the gym.\n\nSleep. Water. Steps. Stress.\n\nTherapia brings it all together — track it daily without the complexity.",
        "why_it_works": "Simple, short, relatable Saudi reality, not preachy",
        "channel_format": "instagram_story"
    },
]

REJECTED_EXAMPLES = [
    {
        "channel": "instagram",
        "copy_ar": "يا صديقي، هل تعاني من الإجهاد والضغط النفسي؟ تطبيق Therapia يساعدك على تحقيق التوازن في حياتك وتعزيز صحتك النفسية والجسدية.",
        "rejection_reason": "Egyptian Arabic (يا صديقي), mentions psychological health (excluded topic), too formal, sounds like an ad",
        "what_to_avoid": "يا صديقي / نفسية / formal MSA / ad-speak"
    },
    {
        "channel": "instagram",
        "copy_ar": "ابدأ رحلتك نحو حياة أكثر صحة وسعادة مع تطبيق Therapia. اكتشف قوة التتبع اليومي لعاداتك الصحية.",
        "rejection_reason": "Robotic marketing language, رحلة (journey cliché), اكتشف (discover cliché), reads like AI",
        "what_to_avoid": "رحلة / اكتشف / حياة أكثر سعادة / corporate phrasing"
    },
]

BRAND_MEMORY_UPDATES = {
    "brand_voice": "Saudi Gulf friend who genuinely cares about your health. Talks like WhatsApp, not a brochure. Specific, honest, not preachy.",
    "is_provisional": False,
    "dos": [
        "Open with a real observation or question a Saudi would actually say",
        "Use خل، شوف، وش، يبيلك، الحين — natural Gulf vocabulary",
        "Give one specific, concrete benefit — not a list of vague claims",
        "End with a specific CTA from the offers list",
        "Keep it short — if it takes more than 10 seconds to read, cut it",
    ],
    "donts": [
        "Never say يا صديقي or حبيبي — Egyptian markers",
        "Never use رحلة (journey), اكتشف (discover), قوة (power) — AI clichés",
        "Never mention mental health, psychology, or therapy (excluded topic)",
        "Never sound like a doctor or give medical advice",
        "Never use فصحى unless context is explicitly formal",
        "Never start with Are you..., Do you..., Unlock..., Discover...",
    ],
}


async def main():
    async with SessionLocal() as db:
        project = (await db.execute(select(Project).where(Project.slug == "therapia"))).scalar_one()
        memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project.id))).scalar_one()
        brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project.id))).scalar_one()

        # Update project memory with real examples
        memory.approved_examples = APPROVED_EXAMPLES
        memory.rejected_examples = REJECTED_EXAMPLES
        memory.tone = "Gulf Saudi — warm, direct, like a fit Saudi friend. WhatsApp register, not corporate. Use: خل، شوف، وش، يبيلك، الحين، يلا. Never: يا صديقي، رحلة، اكتشف، نفسي."
        flag_modified(memory, "approved_examples")
        flag_modified(memory, "rejected_examples")
        memory.version = (memory.version or 1) + 1

        # Update brand memory — mark as approved, not provisional
        for k, v in BRAND_MEMORY_UPDATES.items():
            setattr(brand, k, v)
        flag_modified(brand, "dos")
        flag_modified(brand, "donts")

        await db.commit()
        print(f"✓ Seeded {len(APPROVED_EXAMPLES)} approved + {len(REJECTED_EXAMPLES)} rejected examples")
        print(f"✓ Brand voice updated and approved (is_provisional=False)")


asyncio.run(main())
```

**Run after creating:**
```bash
python -m scripts.seed_therapia_examples
```

**Success test:**
```bash
python -c "
import asyncio
from sqlalchemy import select
from app.database import SessionLocal
from app.models.project_memory import ProjectMemory
from app.models.project import Project

async def test():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.slug == 'therapia'))).scalar_one()
        m = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == p.id))).scalar_one()
        assert len(m.approved_examples) >= 3, 'Need 3+ approved examples'
        assert len(m.rejected_examples) >= 2, 'Need 2+ rejected examples'
        print('PASS — examples seeded')

asyncio.run(test())
"
```

---

## STEP 5 — UX: Guided onboarding for new users

**File:** `frontend/app/projects/[id]/page.tsx`

**What to add:** A step indicator at the top of the project page showing where Omar is in the setup flow.

Add this component ABOVE the tabs:

```tsx
function SetupProgress({ uploads, hasPlan, hasApprovedAssets }: {
  uploads: number; hasPlan: boolean; hasApprovedAssets: boolean
}) {
  const steps = [
    { label: 'Upload logo', done: uploads > 0 },
    { label: 'Generate plan', done: hasPlan },
    { label: 'Approve & publish', done: hasApprovedAssets },
  ]
  const allDone = steps.every(s => s.done)
  if (allDone) return null  // hide once fully set up

  return (
    <div className="flex items-center gap-2 px-4 py-3 mb-4 rounded-xl bg-[rgba(201,168,76,0.06)] border border-[rgba(201,168,76,0.15)]">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
            step.done ? 'bg-[#10B981] text-white' : 'bg-[rgba(201,168,76,0.2)] text-[#C9A84C]'
          }`}>
            {step.done ? '✓' : i + 1}
          </div>
          <span className={`font-['IBM_Plex_Sans'] text-xs ${step.done ? 'text-[rgba(248,246,241,0.35)] line-through' : 'text-[rgba(248,246,241,0.7)]'}`}>
            {step.label}
          </span>
          {i < steps.length - 1 && <div className="w-4 h-px bg-[rgba(255,255,255,0.1)]" />}
        </div>
      ))}
    </div>
  )
}
```

**Render condition:** Show it when `uploads.length === 0 || !currentPlan`.
Place it right after the tab bar, before the tab content.

**Also fix:** Disable "Full Pipeline" button on Pipeline tab if `uploads.length === 0`. Add tooltip:
```tsx
<button
  onClick={() => runPipeline('run')}
  disabled={running || uploads.length === 0}
  title={uploads.length === 0 ? 'Upload a logo first so the AI can match your brand' : undefined}
  ...
>
```

---

## STEP 6 — UX: Dashboard first-run empty state

**File:** `frontend/app/page.tsx`

**What to add:** When `metrics.total_assets_generated === 0`, show a "Start here" banner above the project cards:

```tsx
{!metricsLoading && metrics.total_assets_generated === 0 && (
  <AnimatedContent delay={150}>
    <div className="mb-6 rounded-xl border border-[rgba(201,168,76,0.2)] bg-[rgba(201,168,76,0.05)] px-5 py-4 flex items-start gap-4">
      <div className="w-8 h-8 rounded-full bg-[#C9A84C] text-[#0A0A0A] flex items-center justify-center font-bold text-sm shrink-0">1</div>
      <div>
        <p className="font-['IBM_Plex_Sans'] text-sm font-semibold text-[#F8F6F1] mb-1">Start with Therapia</p>
        <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.5)]">
          Upload your logo → generate a weekly plan → approve content → it publishes automatically.
        </p>
        <Link href="/projects/therapia" className="inline-block mt-2 font-['IBM_Plex_Sans'] text-xs text-[#C9A84C] hover:underline">
          Set up Therapia →
        </Link>
      </div>
    </div>
  </AnimatedContent>
)}
```

**Place:** Between the stats row and the project cards.

---

## STEP 7 — UX: Empty states with action buttons everywhere

**Files:** Multiple pages — add action buttons to every empty state.

### Inbox empty state
```tsx
// Current: "No pending approvals. Run the pipeline on a project to generate content."
// Fix: add a direct link
<Link href="/projects/therapia" className="mt-3 inline-block font-['IBM_Plex_Sans'] text-sm text-[#C9A84C] border border-[rgba(201,168,76,0.3)] rounded-xl px-4 py-2 min-h-[44px] flex items-center hover:bg-[rgba(201,168,76,0.08)] transition-all">
  Run pipeline on Therapia →
</Link>
```

### Analytics empty state
```tsx
// Add: "After you approve and publish content, metrics appear here automatically."
// Add link to inbox
```

### Project analytics tab empty state
```tsx
// Add: specific next action — "Approve content in Inbox to start publishing"
```

---

## STEP 8 — Design: Dashboard premium feel

**File:** `frontend/app/page.tsx`

**What's wrong:** Stats row shows hardcoded zeros with generic icons. Project cards look identical. No visual hierarchy.

**Fix 1:** Stats row — make the numbers bigger, add subtle color coding:
- Pending Approvals: if > 0 → gold number (action needed)
- Published: green number
- Budget Used: normal

```tsx
// Replace the stats tiles with color-aware versions:
{[
  { icon: Clock, label: 'Pending Approvals', value: metrics.pending_approvals, accent: metrics.pending_approvals > 0 ? '#C9A84C' : undefined },
  { icon: CheckCircle, label: 'Published', value: metrics.published_assets, accent: metrics.published_assets > 0 ? '#10B981' : undefined },
  { icon: TrendingUp, label: 'Assets Generated', value: metrics.total_assets_generated },
  { icon: LayoutDashboard, label: 'Active Projects', value: 4 },
].map(({ icon: Icon, label, value, accent }) => (
  <Card key={label}>
    <Icon size={16} className="mb-2" style={{ color: accent || 'rgba(201,168,76,0.6)' }} />
    <p className="font-['IBM_Plex_Mono'] text-2xl font-bold" style={{ color: accent || '#F8F6F1' }}>
      <CountUp end={value} />
    </p>
    <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">{label}</p>
  </Card>
))}
```

**Fix 2:** Project cards — show different status badges per project:
- If has pending approvals: show gold "N pending" badge
- If pipeline running: show spinning indicator
- If no plan yet: show "Not started" in muted color

Update the PROJECTS constant to be fetched from API (not hardcoded), so status is real:
```tsx
// Instead of hardcoded PROJECTS array, fetch from GET /api/proxy/projects
// Each project response includes status and channel connections
```

---

## STEP 9 — Design: Inbox — premium card design

**File:** `frontend/app/inbox/page.tsx`

**What's wrong:** Cards look generic. The approve/reject buttons are not prominent enough on mobile. No visual distinction between channels.

**Fix:** Channel-specific color accents on cards:
```tsx
const CHANNEL_COLORS: Record<string, string> = {
  instagram: 'rgba(225,48,108,0.15)',
  linkedin: 'rgba(0,119,181,0.15)',
  x: 'rgba(29,161,242,0.15)',
  google_ads: 'rgba(66,133,244,0.15)',
}

// Apply to card border:
<div className="rounded-[20px] p-[2px]" style={{
  background: `linear-gradient(135deg, ${CHANNEL_COLORS[asset?.channel || ''] || 'rgba(201,168,76,0.1)'}, transparent)`
}}>
```

**Fix 2:** Make approve button full-width on mobile, more prominent:
```tsx
// On mobile: stack approve/reject vertically, each full width, 56px height
<div className="flex flex-col gap-2 sm:flex-row mt-4 pt-4 border-t border-[rgba(201,168,76,0.08)]">
  <button className="... h-14 text-base font-semibold"> Approve </button>
  <button className="... h-14"> Reject </button>
</div>
```

---

## STEP 10 — Design: Mobile navigation polish

**File:** `frontend/components/ui/Sidebar.tsx`

**What's wrong:** Bottom tab bar has 4 items — Plans is missing. Icons are too small on some phones.

**Fix:** Include Plans in mobile nav (5 items with smaller text):
```tsx
// Mobile: show 5 items with smaller text
{NAV_ITEMS.slice(0, 5).map(({ href, icon: Icon, label }) => (
  <Link key={href} href={href}
    className={`relative flex flex-col items-center gap-0.5 px-2 py-2 rounded-lg flex-1 min-h-[52px] justify-center ${
      isActive(href) ? 'text-[#C9A84C]' : 'text-[rgba(248,246,241,0.35)]'
    }`}
  >
    <Icon size={20} />
    <span className="font-['IBM_Plex_Sans'] text-[9px] leading-tight text-center">{label}</span>
    {/* inbox badge */}
  </Link>
))}
```

---

## VERIFICATION CHECKLIST (run after all steps)

```bash
# Backend imports
cd backend && source venv/bin/activate
python -c "from app.agents.copy import CopyAgent; from app.agents.localization import LocalizationAgent; print('agents OK')"

# Image fix test
python -c "
import asyncio
from app.tools.r2_tools import upload_to_r2, _MAX_BASE64_BYTES
async def test():
    small = b'x' * 1000
    large = b'x' * (_MAX_BASE64_BYTES + 1)
    s = await upload_to_r2(small, 'test/logo.png', 'image/png')
    l = await upload_to_r2(large, 'test/big.png', 'image/png')
    assert s.startswith('data:'), 'small must be base64'
    assert '/api/uploads/serve/' in l, 'large must be serve URL'
    print('image test PASS')
asyncio.run(test())
"

# Examples seeded
python -m scripts.seed_therapia_examples

# Frontend build
cd ../frontend && npm run build
# Must: ✓ Compiled successfully — ZERO errors

# Route check
for route in "/" "/inbox" "/projects/therapia" "/plans/2026-05-11" "/analytics" "/settings"; do
  echo "Checking $route..."
done
# All must return 200

# Arabic content check (after running pipeline)
# Generated Arabic must NOT contain:
# يا صديقي | حبيبي | ازيك | نفسي | نفسية | رحلة | اكتشف | يا عزيزي
```

---

## COMMIT FORMAT

One commit per step:
```
fix(step-N): description
```

Example:
```
fix(step-1): enforce 300KB base64 cap — large designs use serve URL
fix(step-2): localization agent upgraded to Sonnet + Gulf vocabulary anchors
fix(step-3): copy agent anti-AI-cliché rules + free-form writing mode
fix(step-4): seed real Gulf Saudi approved/rejected examples for Therapia
feat(step-5): guided setup progress indicator on project page
feat(step-6): first-run empty state on dashboard with "Start here" CTA
feat(step-7): action buttons on all empty states
feat(step-8): color-aware dashboard stats + live project status
feat(step-9): channel-specific card accents + mobile-first approve buttons
feat(step-10): 5-item mobile nav with Plans included
```

---

## WHAT DONE LOOKS LIKE

Omar opens Sovereign on his iPhone:

1. Dashboard → gold number on "3 Pending Approvals" → taps Inbox
2. Inbox → cards have Instagram pink border / LinkedIn blue border
3. Swipe right → "✅ Approved — scheduled for publish" toast
4. Opens /projects/therapia → sees 3-step progress bar: "1. Upload logo ✓ 2. Generate plan ✓ 3. Approve & publish →"
5. Runs Full Pipeline → Arabic copy reads like a real Saudi wrote it → no يا صديقي, no رحلة, no نفسية
6. Reads English copy → no "leverage", no "journey", no "unlock"
7. Images → logos show correctly (base64 < 300KB) / design images show clean placeholder if /tmp expired
8. Every empty state has a "do this next" action button

---

## FOR CODEX — CRITICAL NOTES

- Steps 1-4 are BACKEND ONLY. Do not touch frontend for steps 1-4.
- Steps 5-10 are FRONTEND ONLY. Do not touch backend for steps 5-10.
- After step 1: run the image test. If it fails, STOP and fix it.
- After step 4: run `python -m scripts.seed_therapia_examples`. Must print "PASS".
- After every step: `npm run build` or `python -c "from app.agents... "` — zero errors before commit.
- The Localization Agent MODEL change (HAIKU → SONNET) in step 2 costs ~5x more per run. That is intentional — Arabic quality is the priority.
- Do NOT change any database schema. Do NOT run migrations.
- Do NOT add new npm packages without checking bundle impact.
- Do NOT change auth logic.
- Do NOT modify Railway config files.
