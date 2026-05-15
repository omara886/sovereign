"""
Skill rules embedded as deployable strings.
Source: ~/.claude/skills/ — extracted and hardcoded so Railway can use them.
Each function returns a compact rule block for injection into agent prompts.
"""

# ── CONTENT-ENGINE ────────────────────────────────────────────────────────────

def content_engine_rules() -> str:
    return """CONTENT-ENGINE RULES (non-negotiable):
- One idea per asset. One message. One CTA. No multi-purpose visuals.
- Build from source: use approved_examples patterns, avoid rejected_examples patterns.
- Platform-native: Instagram tactics ≠ LinkedIn tactics ≠ X tactics.
- Generate 3-5 DISTINCT story angles — not restylings of the same story.
- Sequence matters: awareness before consideration before conversion.
- Every stat or claim must have a proof_point. No unsourced numbers.
- CTA must be specific and actionable ("ابدأ مجاناً" not "اعرف أكثر").
- Formats by funnel_stage: awareness→poster/hero, consideration→infographic/carousel, conversion→stat_card/UI_mock."""

# ── MARKETING-PSYCHOLOGY ──────────────────────────────────────────────────────

def marketing_psychology_rules() -> str:
    return """MARKETING-PSYCHOLOGY FRAMEWORKS (apply one per asset):
- PAS (Problem-Agitate-Solution): open with pain, intensify, resolve.
- AIDA (Attention-Interest-Desire-Action): hook → educate → want → act.
- Loss-aversion: frame as what they LOSE by not acting (2x more effective than gain framing).
- Social-proof: specific numbers beat adjectives ("٣٢٠٠ مستخدم" beats "الكثير").
- Authority: credentials + specificity ("٨ دقائق" not "سريع").
- Reciprocity: give value before asking (free assessment, insight, checklist).
RULE: Select ONE framework per concept and annotate every copy line with its role (hook/promise/proof/CTA)."""

# ── BRAND-VOICE ───────────────────────────────────────────────────────────────

def brand_voice_rules(brand_voice: str = "", dos: list | None = None, donts: list | None = None) -> str:
    dos_text = "\n- ".join(dos[:5]) if dos else "Warm, direct, Gulf Saudi tone"
    donts_text = "\n- NEVER: ".join(donts[:5]) if donts else "No formal فصحى, no Egyptian dialect, no corporate speak"
    return f"""BRAND-VOICE RULES:
Stored voice: {brand_voice or 'Gulf Saudi, warm, direct, specific'}
DO:
- {dos_text}
NEVER:
- {donts_text}
- Generic CTAs: "اضغط هنا" / "اعرف أكثر" / "Discover more"
- AI-cliché: "unlock", "leverage", "journey to wellness"
- Formal register: تفضّل, عزيزي المستخدم, يسعدنا
ANNOTATION REQUIRED: Tag each copy line with [hook|promise|proof|CTA] + emotional tone."""

# ── CRAFT-POLISH ──────────────────────────────────────────────────────────────

def craft_polish_rules() -> str:
    return """CRAFT-POLISH CONSTRAINTS:
- 8pt spacing grid: all padding/margin must be multiples of 8px.
- Generous breathing room: minimum 7% padding from any edge.
- Typography hierarchy: max 3 type sizes; clear H1→H2→body→caption steps.
- Contrast: headline on background must pass WCAG AA (≥4.5:1 for body, ≥3:1 for headlines).
- Shadows: soft and warm; never hard box-shadows or outline strokes.
- Color: maximum 2 non-neutral hues per viewport unless brand.md explicitly allows more.
- Grain/texture: only as post-process overlay; never generated.
- Every element must serve a purpose; remove decorative noise."""

# ── FRONTEND-DESIGN-ANTI-SLOP ─────────────────────────────────────────────────

def anti_slop_rules() -> str:
    return """ANTI-SLOP BLACKLIST — reject any design containing:
LAYOUT TROPES:
- 3-column feature grids with icon + title + description
- Centered hero portrait with text below
- Full-bleed stock photo with white text overlay
- Symmetrical left/right split layouts
- Generic icon-in-colored-circle patterns

AI VISUAL TELLS:
- Neon blue/purple gradients
- Floating geometric particles/shapes
- Glowing orbs or light bokeh as decoration
- Purple-to-teal gradients
- Oversaturated "tech" blues

COMPOSITION FAILURES:
- Text-first designs with no visual anchor
- Wall of text inside the creative
- More than 2 focal points
- Busy backgrounds competing with the message
- Generic corporate "business" aesthetics
- Dribbble-style drop shadows and glow effects

AUTOMATIC REJECTION if any of the above are detected in layout_family, style_family, or generation prompt."""

# ── ARTIFACT-COMPOSITION ─────────────────────────────────────────────────────

def artifact_composition_rules() -> str:
    return """ARTIFACT-COMPOSITION RULES:
- ONE dominant focal point per asset. Everything else is secondary.
- Clear information hierarchy: hero stat/claim → supporting detail → CTA.
- Layout families (choose one):
  bento_grid: 2-4 unequal panels, varied sizes create rhythm
  hero_stat: large number dominates, 1-2 supporting facts, CTA
  vertical_flow: top-down narrative, 3-5 steps or facts
  comparison: before/after or option A vs B, clear winner signaled
  timeline: 3-5 milestones, directional flow
  poster_hero: single strong image + headline + CTA only
- Text must never compete with the image for dominance.
- Whitespace is a design element, not wasted space."""

# ── EDITORIAL-TYPOGRAPHY (Arabic/Urdu) ────────────────────────────────────────

def editorial_typography_rules(lang: str = "ar") -> str:
    rtl = lang in ("ar", "ur")
    return f"""EDITORIAL-TYPOGRAPHY RULES ({lang.upper()}/RTL={'YES' if rtl else 'NO'}):
- Primary font: Thmanyah Sans (or brand-specified Arabic/Urdu font).
  Weights: Black for headlines, Bold for subheads, Regular for body.
- Direction: dir=rtl on all Arabic/Urdu text containers.
- Alignment: RIGHT-aligned for Arabic/Urdu. NEVER centered unless 1-2 words.
- Headline: maximum 2 lines. Maximum 6 words per line. Never orphaned words.
- Mobile legibility: minimum 40px headline at 1080px width.
- Line height: 1.3x for Arabic headlines, 1.5x for body.
- Arabic rendering: RAQM (HarfBuzz+FriBiDi) PREFERRED.
  Fallback only: arabic_reshaper + python-bidi (mark as 'reshaper_fallback' in sidecar).
  NEVER bake Arabic text into the fal.ai image prompt.
- Mixed AR/EN: Arabic dominates visually; English is secondary and smaller.
- Contrast: Arabic text must have dedicated overlay zone; never float over busy backgrounds."""

# ── RESPONSIVE-LAYOUT ────────────────────────────────────────────────────────

def responsive_layout_rules() -> str:
    return """RESPONSIVE-LAYOUT SAFE-AREA RULES:
Platform sizes and text safe zones (all in px):
  1080×1080 (Instagram feed): safe area = 75px all sides (6.9%)
  1080×1350 (Instagram portrait): safe area = 75px sides, 100px top/bottom
  1080×1920 (Story/Reel): safe area = 88px sides, 15% top, 20% bottom (avoid tap zones)
  1200×627 (LinkedIn): safe area = 84px sides, 50px top/bottom
  1600×900 (X/Twitter): safe area = 112px sides, 63px top/bottom
TEXT ZONE: for Arabic/Urdu: bottom 40-50% of image is the primary text zone.
THUMBNAIL TEST: every asset must be legible at 300px width (thumbnail). Headline must be readable.
Never place critical content in the outer 7% margin.
Text must reflow (not just resize) when switching between portrait and landscape formats."""
