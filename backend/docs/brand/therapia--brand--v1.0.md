# Therapia Design System
# Based on open-design DESIGN.md schema (9 sections)
# Visual direction: Warm Soft × Tech Utility (Health-tech, Saudi Gulf)

## 1. COLOR

Primary palette:
- Obsidian: #0A0A0A (background)
- Slate: #1E293B (card background)
- Gold: #C9A84C (primary accent — trust, premium)
- Gold Light: #E8C97A (hover states)
- Off-white: #F8F6F1 (primary text)

Functional:
- Success: #10B981
- Warning: #F59E0B
- Danger: #EF4444

Visual direction: Dark luxury. Gold as the signal of trust and health premium.
Anti-pattern: Never use purple gradients. Never use clinical blue/white (looks hospital).

## 2. TYPOGRAPHY

Primary: Thmanyah Sans (Arabic + English) — warm, structured, bilingual
- Headlines: Thmanyah Bold, 48-64px
- Body: Thmanyah Regular, 16-20px
- Data: Thmanyah Regular Mono equivalent

Arabic rules:
- Direction: RTL always
- Gulf Saudi dialect vocabulary only
- Thmanyah Bold for Arabic headlines (gold color)
- Never system fallback fonts

## 3. SPACING

- Section padding: 48-80px vertical
- Card padding: 24px
- Text padding from edges: 8-10% of image width
- Text area: bottom 40% of image reserved for copy overlay

## 4. LAYOUT

Instagram (1080x1080):
- Upper 55%: visual/image area
- Lower 45%: gradient to dark, Arabic headline + English sub
- Gold separator line between AR and EN

LinkedIn (1200x627):
- Landscape, professional
- Left or center composition
- More whitespace, less emotion, more credibility

## 5. COMPONENTS

Social card anatomy:
1. Background: gradient from #1E293B (top) → #0A0A0A (bottom)
2. Visual element: lifestyle photo or abstract health visual (fal.ai generated)
3. Gold accent stripe: 6px at very bottom
4. Arabic headline: Thmanyah Bold, gold (#C9A84C), RTL, centered
5. Separator: thin gold line
6. English sub: Thmanyah Regular, off-white, smaller

## 6. MOTION

Static cards only for v1.
Transition feel: smooth, unhurried — matches wellness brand tone.

## 7. VOICE

Brand voice: Saudi Gulf friend who cares about your health.
- Register: WhatsApp-casual, direct, warm
- Forbidden: formal MSA, Egyptian dialect, corporate speak
- Tone: supportive, honest, specific (numbers beat adjectives)
- Example good: "خل نكون صريحين... صحتك تستاهل أحسن"
- Example bad: "يا عزيزي المستخدم، نرحب بكم في تطبيقنا"

## 8. BRAND

Personality: Premium Saudi wellness. Not clinical. Not cheap. Not generic.
Positioning: "تطبيق صحتك الشخصي في جيبك"
Trust signals: specific numbers, real benefits, warm not preachy
What Therapia is NOT: mental health app, hospital, medical diagnosis

## 9. ANTI-PATTERNS

NEVER:
- Purple or blue gradients (looks generic/corporate)
- White background (clinical, not premium)
- Stock photo smiling doctor (not the brand)
- Psychological/mental health imagery or copy
- Generic CTAs: "اضغط هنا" / "اعرف أكثر" / "Discover more"
- AI-cliché copy: "unlock", "leverage", "journey to wellness"
- Egyptian Arabic: يا صديقي, حبيبي, ازيك
- Formal MSA: تفضّل, عزيزي المستخدم
- Comic Sans, Arial, Roboto (use Thmanyah only)

---
## 10. ARABIC TYPE RULES

Rendering engine (mandatory):
- PREFERRED: Pillow + libraqm (HarfBuzz shaping + FriBiDi BiDi ordering)
  font = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
  draw.text(xy, text, font=font, direction='rtl', language='ar')
- FALLBACK only (when RAQM unavailable):
  reshaped = arabic_reshaper.reshape(text)
  display  = get_display(reshaped, base_dir='R')
  draw.text(xy, display, font=font)  # no direction= kwarg
- NEVER combine both paths — RAQM already handles shaping + BiDi internally
- NEVER ask fal.ai / Flux to render Arabic copy

Font requirements:
- Primary: Thmanyah Sans Black (headlines), Bold (subheads), Regular (body)
- All Thmanyah OTF files confirmed: arabic_basic_glyphs=True, GSUB=True, arabic_in_GSUB=True
- Thmanyah uses OpenType GSUB path — arabic_reshaper (Presentation Forms) may produce .notdef glyphs
- Use RAQM path to activate Thmanyah's shaping tables correctly

Text rules:
- Max 2 lines per headline in image; max 1 line for subhead
- Measure width AFTER shaping via textbbox() — pre-wrap on unshaped text is unreliable
- Right-align all Arabic blocks; anchor from right edge (anchor='ra' with RAQM)
- Test textbbox() with real strings for clipping (tall ascenders/descenders)
- Never embed more than 6 words per headline in an exported image
- Long copy stays in caption panel, never in the visual

---
## 11. INFOGRAPHIC SYSTEM

Claim rules:
- Every numeric claim must have a row in /assets/data/claims.csv
- claims.csv columns: claim_id, numeric_value, claim_text, source_url, source_title, source_date, verifier, verified_date, flagged
- No infographic is publishable if claims.csv row has flagged=true or verifier=NULL
- Sources must be < 2 years old; mark older sources as "needs refresh"

Layout grid:
- Template B (Infographic): metric hero (large number, label), 3 benefit blocks, headline, CTA
- Metric hero: number only (Arabic-Indic or Western numerals), label separate line below
- Benefit blocks: max 3 words each, center-aligned, translucent accent background
- Safe areas: 7% padding all sides; CTA bottom 9-16% zone; brand name top-left

Platform derivatives (master → exports):
- 1080×1080 (Instagram feed)
- 1080×1350 (Instagram portrait)
- 1080×1920 (Story/Reel)
- 1200×627  (LinkedIn)
- 1600×900  (X/Twitter)
- Each derivative reflowed with Arabic text per safe-area template; not blind resize

---
## 12. QA CHECKLIST

Pre-approval gates (all must pass, in order):
1. Arabic script QA: run arabic_qa.run_arabic_qa(asset) → blocked=False
2. Preview renders: design_thumbnail_url must load (HTTP 200), variance > 15
3. QA score: asset.qa_score >= 70
4. Channel set: asset.channel must be non-empty
5. Claim sources: if infographic, all claims in claims.csv with flagged=False

Visual QA (human):
- [ ] Arabic headline: connected glyphs, no gaps at ا،د،و،ر boundaries
- [ ] Arabic direction: text reads right-to-left, not mirrored
- [ ] No text inside fal.ai generated area (text is overlay only)
- [ ] Brand colors: accent matches #4169E1 (Therapia) or project token
- [ ] CTA pill: readable, correct color, Arabic text not clipped
- [ ] Bottom bar: accent color, 6px
- [ ] No gold (#C9A84C) unless explicitly overridden by brand_memory

Compliance score weights:
- Visual token match (30%): colors match brand_memory.color_palette
- Typography (20%): Thmanyah used, correct weights, RAQM path confirmed
- Accessibility (10%): headline on dark bg passes WCAG AA (4.5:1 min)
- Arabic rendering (20%): RAQM path or validated reshaper output
- Source/factual (10%): claims.csv row exists and verified
- Export/sizing (10%): platform derivative exported at correct dimensions

Fail threshold: score < 60 → human approval required before publish
