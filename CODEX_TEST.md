# SOVEREIGN — Codex Test Suite
# Test every feature end-to-end. Report PASS/FAIL for each. No fixes — report only.
# Frontend: https://frontend-production-9eea5.up.railway.app
# Backend: https://backend-production-37a17.up.railway.app

---

## HOW TO RUN

Use Playwright to test every flow. Run headless on mobile viewport (375x812).
Report format per test: PASS | FAIL | ERROR: [exact message]

---

## TEST 1 — Auth

1. Open https://frontend-production-9eea5.up.railway.app
2. Assert: redirected to /login (not dashboard)
3. Enter username: omar / password: wrong → assert error message visible
4. Enter username: omar / password: Sovereign!2026 → assert redirected to /
5. Reload page → assert still on / (session persists, not kicked to login)
6. Click Sign Out → assert redirected to /login

PASS criteria: all 5 steps succeed

---

## TEST 2 — Navigation (375px mobile viewport)

1. Log in
2. Assert: bottom tab bar visible (4 tabs: Dashboard, Projects, Inbox, Analytics)
3. Tap each tab — assert correct page loads with no 404
4. Assert: no horizontal scroll on any page
5. Assert: content not hidden behind bottom tab bar

PASS criteria: all tabs load, no overflow, no hidden content

---

## TEST 3 — Upload

1. Navigate to /projects/therapia
2. Assert: 3 tabs visible (Assets, Memory, Pipeline)
3. Select "Logo" tab
4. Upload a 100x100 PNG file (generate one programmatically)
5. Assert: response status 200 (not 500)
6. Assert: uploaded file appears in grid below upload zone
7. Assert: image actually renders (not black box)
8. Wait 10 seconds → assert Memory tab updates (brand_voice or visual_style changed)

PASS criteria: upload returns 200, image visible in grid

---

## TEST 4 — Pipeline

1. Navigate to / (dashboard)
2. Click "Weekly Plan" on Therapia card
3. Assert: status bar appears showing "Generating weekly plan..."
4. Navigate to /inbox (different page)
5. Navigate back to /
6. Assert: status bar still showing (persists across navigation via localStorage)
7. Wait for completion (max 60 seconds)
8. Assert: "Go to Inbox" or success message appears

PASS criteria: status persists on navigation, completes without error

---

## TEST 5 — Inbox

1. Run pipeline first (or use existing pending approvals)
2. Navigate to /inbox
3. Assert: approval cards visible (not empty state)
4. Assert: each card shows channel badge, copy text (not empty)
5. Click "View" on a card → assert full detail modal opens
6. Assert: modal shows full English copy (not truncated)
7. Assert: modal shows full Arabic copy with RTL direction
8. Click Approve → assert card disappears from inbox
9. Open a new card → click Reject → assert rejection reason textarea visible
10. Type a reason → click "Reject & Save Feedback" → assert card disappears

PASS criteria: approve removes card, reject with reason removes card

---

## TEST 6 — Content Quality

1. After pipeline runs, open inbox
2. Read the English copy on each asset
3. Assert: no mention of "mental health", "psychological", "therapy", "depression", "psychiatry"
4. Assert: copy references the actual product (health app, assessments, wellness)
5. Assert: CTA is specific (not "Click here" or "Learn more")

PASS criteria: zero psychological terms in generated copy

---

## TEST 7 — Images

1. Open /inbox with pending approvals
2. Assert: thumbnail area shows either an image OR the ImageOff icon (not a black box)
3. Click "View" on a card
4. Assert: design_url image loads in modal (or ImageOff shown gracefully)
5. Open /projects/therapia → Assets tab (if logo uploaded)
6. Assert: logo image renders or shows Image icon placeholder

PASS criteria: no black boxes anywhere — either image loads or clean placeholder shown

---

## TEST 8 — Memory Tab

1. Navigate to /projects/therapia → Memory tab
2. Assert: Brand Memory section loads (not loading spinner stuck)
3. Assert: shows visual_style, brand_voice values
4. Assert: Dos list visible
5. Assert: Donts list visible
6. Assert: Project Memory section shows positioning, tone, funnel goals
7. Assert: excluded_topics in constraints does NOT include mental health terms (verify via API call GET /api/proxy/projects/therapia/memory)

PASS criteria: all memory fields visible and populated

---

## TEST 9 — Analytics

1. Navigate to /analytics
2. Assert: 3 metric tiles visible (Published Assets, Pending Approvals, Total Assets)
3. Assert: numbers show (even if 0, not loading spinner stuck)
4. Assert: CountUp animation plays on page load

PASS criteria: page loads with numbers, no stuck spinner

---

## TEST 10 — Settings

1. Navigate to /settings
2. Assert: Account section shows username: omar, email: oalomran443@gmail.com
3. Assert: Automation Schedule section shows 4 schedule items
4. Assert: System Status shows backend URL (not "Loading...")

PASS criteria: all sections populated

---

## REPORT FORMAT

```
TEST 1 — Auth: PASS
TEST 2 — Navigation: FAIL — /settings returns 404
TEST 3 — Upload: PASS
TEST 4 — Pipeline: FAIL — ERROR: timeout after 60s
TEST 5 — Inbox: PASS
TEST 6 — Content Quality: FAIL — found "psychological" in copy_en of asset abc123
TEST 7 — Images: PASS
TEST 8 — Memory: PASS
TEST 9 — Analytics: PASS
TEST 10 — Settings: PASS

SUMMARY: 8/10 PASS
FAILURES:
- TEST 2: [exact error]
- TEST 4: [exact error]
- TEST 6: [exact content snippet that failed]
```

---

## IMPORTANT

- Do NOT fix anything. Only test and report.
- Use real network calls to the Railway URLs (not mocks)
- If a test depends on pipeline output, run the pipeline first and wait for it
- Report the exact error message, not paraphrases
- Test on 375px viewport for all mobile tests
