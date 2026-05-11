# SOVEREIGN IMAGE PIPELINE — ZERO MISTAKE GUIDE FOR CODEX
# Superpowers methodology: spec → plan → implement → test → done
# Every step has exact code, exact test, exact success check.
# DO NOT move to next step until current step test passes.

---

## THE SPEC (what must work)

Omar runs Full Pipeline on Therapia.
Result in inbox: a real image showing a Saudi lifestyle scene, with Arabic headline
in Thmanyah Black font, English subtitle below. Not a dark rectangle. Not boxes.
A real social media post that looks designed.

---

## ROOT CAUSES (what is broken right now)

1. fal.ai call fails silently → returns dark placeholder → looks broken
2. arabic-reshaper not in requirements.txt Docker install → Arabic = ⊠⊠⊠  
3. DeepSeek art director never ran → generic prompt → generic (or no) image
4. No end-to-end test was ever run on Railway with real keys

---

## STEP 1 — Fix requirements.txt (backend)

**File:** `backend/requirements.txt`

Add these lines if not present:
```
arabic-reshaper==3.0.0
python-bidi==0.6.6
```

**Verify locally:**
```bash
cd backend && source venv/bin/activate
pip install arabic-reshaper python-bidi
python -c "import arabic_reshaper; from bidi.algorithm import get_display; print('arabic OK')"
```
Expected output: `arabic OK`

**Commit:** `fix: add arabic-reshaper and python-bidi to requirements`

---

## STEP 2 — Fix fal.ai API call

**File:** `backend/app/tools/fal_tools.py`

The current `fal.run/{model}` endpoint is wrong for some models.
Replace entire file with this exact code:

```python
import io
import logging
import httpx
from PIL import Image
from app.config import get_settings

logger = logging.getLogger(__name__)


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    settings = get_settings()
    if not settings.FAL_KEY:
        logger.warning("FAL_KEY not set — using placeholder")
        return _placeholder(width, height)

    # fal.ai correct endpoint format
    url = f"https://fal.run/{model}"
    headers = {
        "Authorization": f"Key {settings.FAL_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
        "enable_safety_checker": False,
    }

    logger.info("fal.ai POST %s | %dx%d | prompt=%.60s", url, width, height, prompt)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=headers, json=body)
            logger.info("fal.ai response: %d | %s", r.status_code, r.text[:200])
            r.raise_for_status()
            data = r.json()
            images = data.get("images", [])
            if not images:
                logger.error("fal.ai returned no images: %s", data)
                return _placeholder(width, height)
            image_url = images[0]["url"]
            logger.info("fal.ai image url: %s", image_url)
            img_r = await client.get(image_url, timeout=60)
            img_r.raise_for_status()
            logger.info("fal.ai downloaded %d bytes", len(img_r.content))
            return img_r.content
    except httpx.HTTPStatusError as e:
        logger.error("fal.ai HTTP error %d: %s", e.response.status_code, e.response.text[:300])
        return _placeholder(width, height)
    except Exception as e:
        logger.error("fal.ai exception: %s", type(e).__name__, exc_info=True)
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(30, 35, 42))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

**Local test (add your real FAL_KEY temporarily):**
```bash
python -c "
import asyncio, os
os.environ['FAL_KEY'] = 'YOUR_REAL_FAL_KEY'

# Reload settings
import importlib
import app.config
importlib.reload(app.config)

from app.tools.fal_tools import generate_image_fal

async def test():
    result = await generate_image_fal(
        'Saudi professional, golden hour, Riyadh skyline, cinematic',
        'fal-ai/flux/schnell',
        1080, 1080
    )
    print(f'Result: {len(result)} bytes')
    assert len(result) > 100000, f'Too small: {len(result)} — still placeholder'
    print('PASS — real image received')

asyncio.run(test())
"
```
Expected: `Result: 450000 bytes` or similar. If still small → fal.ai not working.

**Commit:** `fix: fal.ai correct request format with full error logging`

---

## STEP 3 — Fix Arabic rendering test

**File:** `backend/app/tools/image_tools.py`

The font paths must be absolute. Verify they resolve correctly:

```python
# Add this test at the top after FONT_BLACK, FONT_BOLD, FONT_REGULAR are defined
import sys
for name, path in [("FONT_BLACK", FONT_BLACK), ("FONT_BOLD", FONT_BOLD), ("FONT_REGULAR", FONT_REGULAR)]:
    if not Path(path).exists():
        print(f"MISSING FONT: {name} at {path}", file=sys.stderr)
```

**Local test:**
```bash
python -c "
import asyncio
from app.tools.image_tools import apply_text_overlay, create_thumbnail

async def test():
    # Use a real image-like input (not solid color so it goes through overlay path)
    from PIL import Image
    from io import BytesIO
    import random
    
    # Create a noisy image (not monochromatic → forces overlay path)
    img = Image.new('RGB', (1080, 1080))
    pixels = [(random.randint(20,60), random.randint(30,70), random.randint(40,80)) 
              for _ in range(1080*1080)]
    img.putdata(pixels)
    buf = BytesIO(); img.save(buf, 'PNG')
    
    result = await apply_text_overlay(
        buf.getvalue(),
        text_ar='رفيقك الصحي الذكي',
        text_en='Your Smart Health Companion',
        brand_primary='#1E293B',
        brand_accent='#C9A84C',
    )
    with open('/tmp/arabic_test.png', 'wb') as f:
        f.write(result)
    print(f'Size: {len(result)} bytes')
    print('Open /tmp/arabic_test.png — must show connected Arabic letters, NOT boxes')

asyncio.run(test())
"
open /tmp/arabic_test.png
```
**Success:** Arabic text reads right-to-left with connected letters. No boxes.

**Commit:** `fix: verify arabic font paths resolve on Railway`

---

## STEP 4 — Fix DeepSeek art director prompt

**File:** `backend/app/agents/design.py`

The `_get_visual_prompt` falls back when DeepSeek key missing. On Railway with key set, it must work.

Add a direct test:
```bash
python -c "
import asyncio, os
os.environ['DEEPSEEK_API_KEY'] = 'YOUR_REAL_DEEPSEEK_KEY'

from app.agents.design import DesignAgent

async def test():
    agent = DesignAgent()
    prompt = await agent._get_visual_prompt(
        copy_en='Your Smart Health Companion',
        copy_ar='رفيقك الصحي الذكي',
        channel='instagram_post',
        brand_colors={'primary': '#1E293B', 'accent': '#C9A84C'},
        brand_style='dark luxury, warm editorial',
        image_style='cinematic lifestyle photography',
        funnel_stage='awareness',
    )
    print('PROMPT:', prompt)
    assert len(prompt) > 20, 'Prompt too short'
    assert 'Saudi' in prompt or 'cinematic' in prompt.lower(), 'No scene context'
    print('PASS — art director prompt generated')

asyncio.run(test())
"
```
Expected: A 50-100 word fal.ai prompt describing a Saudi lifestyle scene.

---

## STEP 5 — Full end-to-end test on Railway

After all fixes deployed, run from the Sovereign dashboard OR curl:

```bash
# Trigger pipeline
curl -X POST https://backend-production-37a17.up.railway.app/api/pipeline/run/therapia

# Get job_id from response, then poll status
curl https://backend-production-37a17.up.railway.app/api/pipeline/status/JOB_ID_HERE
```

Watch Railway backend logs for:
```
fal.ai POST https://fal.run/fal-ai/flux/schnell | 1080x1080 | prompt=...
fal.ai response: 200 | ...
fal.ai downloaded 450000 bytes
```

Then check the inbox. The image must be:
- A real photograph-quality scene (not dark rectangle)
- Arabic text in Thmanyah Black, readable, connected letters
- English text below in Thmanyah Regular
- Gold accent element present

**SUCCESS CRITERIA — all must pass:**
```python
# Run this after pipeline completes
import asyncio
from sqlalchemy import select
from app.database import SessionLocal
from app.models.asset import Asset
from app.models.project import Project
import base64

async def check():
    async with SessionLocal() as db:
        p = (await db.execute(select(Project).where(Project.slug == 'therapia'))).scalar_one()
        assets = (await db.execute(
            select(Asset).where(Asset.project_id == p.id, Asset.status == 'approval_pending')
            .order_by(Asset.created_at.desc()).limit(2)
        )).scalars().all()
        
        assert len(assets) >= 1, 'No assets generated'
        
        for a in assets:
            thumb = a.design_thumbnail_url or ''
            assert thumb.startswith('data:'), f'Thumbnail not base64: {thumb[:50]}'
            
            # Decode and check size — real image is larger than placeholder
            img_bytes = base64.b64decode(thumb.split(',')[1])
            assert len(img_bytes) > 15000, f'Image too small ({len(img_bytes)} bytes) — still placeholder'
            
            assert a.copy_ar, 'No Arabic copy'
            assert 'يا صديقي' not in a.copy_ar, 'Egyptian Arabic detected'
            assert a.qa_score and a.qa_score >= 60, f'QA score too low: {a.qa_score}'
            
            print(f'Asset {a.channel}: thumb={len(img_bytes)} bytes, QA={a.qa_score}')
        
        print('ALL CHECKS PASSED')

asyncio.run(check())
```

---

## COMMIT ORDER FOR CODEX

```
1. fix: arabic-reshaper in requirements.txt
2. fix: fal.ai correct API format with full error logging  
3. fix: verify font paths and arabic rendering
4. test: end-to-end pipeline generates real image on Railway
```

## RULES FOR CODEX

- Run each step's test before moving to the next
- Do NOT commit if the test fails
- Do NOT skip steps
- If fal.ai test returns < 100KB → stop and report the exact error log
- If Arabic shows boxes → stop and report font path issues
- Report back with Railway log output proving fal.ai returned real bytes
