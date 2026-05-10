"""
Asset Analyzer Agent — runs after every file upload.
Uses Claude Vision to read uploaded images and automatically update
ProjectMemory and BrandMemory with what it discovers.
"""
import base64
import json
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.tools.memory_tools import get_brand_memory, get_project_memory, update_brand_memory, update_project_memory

settings = get_settings()

SYSTEM_PROMPT = """You are an Asset Analysis Agent for Sovereign. You analyze uploaded brand assets and extract structured information to update the project's brand and memory guides.

When analyzing a LOGO:
- Extract dominant colors (as hex codes)
- Identify visual style (minimal, bold, elegant, playful, corporate, etc.)
- Describe the brand personality the logo conveys
- Note any typography style visible

When analyzing APP SCREENSHOTS:
- Describe what the product actually does (not assumptions — read the UI)
- Extract the actual features, screens, and user flows visible
- Note the app's color scheme and UI style
- Identify what the product is NOT (to avoid wrong content)
- Extract any visible text that describes the product

When analyzing BRAND COLOR PALETTES:
- Extract all hex codes visible
- Map to: primary, secondary, accent, background, text

When analyzing FONTS:
- Note the font name if visible, or describe the style

Output ONLY valid JSON matching this schema — no explanation:
{
  "brand_updates": {
    "color_palette": {"primary": "#hex", "accent": "#hex"} or null,
    "visual_style": "string describing brand style" or null,
    "image_style": "string" or null,
    "brand_voice": "string based on what you see" or null,
    "dos": ["things to do based on visuals"] or null,
    "donts": ["things NOT to do based on visuals"] or null
  },
  "memory_updates": {
    "positioning": "what this product actually is based on the screenshots" or null,
    "tone": "tone implied by the brand visuals" or null,
    "product_facts": ["fact1 extracted from screenshots", "fact2"] or null,
    "excluded_topics": ["topics clearly unrelated to this product"] or null
  },
  "summary": "2-3 sentence plain English summary of what you learned from this asset"
}

If you cannot determine something, use null — do not guess."""


async def analyze_and_update(
    db: AsyncSession,
    project_id: str,
    project_name: str,
    file_url: str,
    file_type: str,
    filename: str,
) -> dict:
    """Download the uploaded asset, analyze with Claude Vision, update memory."""

    # Skip fonts — nothing to visually analyze
    if file_type == "font":
        return {"summary": "Font uploaded — recorded in brand memory.", "updated": False}

    # Download the image
    image_bytes = await _download_file(file_url)
    if not image_bytes:
        return {"summary": "Could not download file for analysis.", "updated": False}

    # Build Claude vision message
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    media_type = _media_type(ext)
    if not media_type:
        return {"summary": "File type not supported for visual analysis.", "updated": False}

    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    type_context = {
        "logo": "This is the brand LOGO for the project.",
        "screenshot": "This is an APP SCREENSHOT showing the actual product UI.",
        "color_palette": "This is a BRAND COLOR PALETTE or style guide.",
        "other": "This is a brand asset.",
    }.get(file_type, "This is a brand asset.")

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": f"Project: {project_name}\n{type_context}\nAnalyze this asset and return the JSON update.",
                },
            ],
        }],
    )

    raw = response.content[0].text.strip()
    # Extract JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {"summary": "Could not parse analysis output.", "updated": False}

    analysis = json.loads(raw[start:end])

    # Apply brand updates
    brand_mem = await get_brand_memory(db, project_id)
    if brand_mem:
        updates: dict = {}
        bu = analysis.get("brand_updates") or {}
        if bu.get("color_palette"):
            existing = dict(brand_mem.color_palette or {})
            existing.update(bu["color_palette"])
            updates["color_palette"] = existing
        if bu.get("visual_style"):
            updates["visual_style"] = bu["visual_style"]
        if bu.get("image_style"):
            updates["image_style"] = bu["image_style"]
        if bu.get("brand_voice"):
            updates["brand_voice"] = bu["brand_voice"]
        if bu.get("dos"):
            existing_dos = list(brand_mem.dos or [])
            for d in bu["dos"]:
                if d not in existing_dos:
                    existing_dos.append(d)
            updates["dos"] = existing_dos
        if bu.get("donts"):
            existing_donts = list(brand_mem.donts or [])
            for d in bu["donts"]:
                if d not in existing_donts:
                    existing_donts.append(d)
            updates["donts"] = existing_donts
        if updates:
            await update_brand_memory(db, project_id, updates)

    # Apply memory updates
    proj_mem = await get_project_memory(db, project_id)
    if proj_mem:
        mem_updates: dict = {}
        mu = analysis.get("memory_updates") or {}
        if mu.get("positioning"):
            mem_updates["positioning"] = mu["positioning"]
        if mu.get("tone"):
            mem_updates["tone"] = mu["tone"]
        if mu.get("excluded_topics"):
            constraints = dict(proj_mem.constraints or {})
            existing_excluded = list(constraints.get("excluded_topics", []))
            for t in mu["excluded_topics"]:
                if t not in existing_excluded:
                    existing_excluded.append(t)
            constraints["excluded_topics"] = existing_excluded
            mem_updates["constraints"] = constraints
        if mem_updates:
            await update_project_memory(db, project_id, mem_updates)

    return {
        "summary": analysis.get("summary", "Asset analyzed and memory updated."),
        "updated": True,
        "brand_updates_applied": list((analysis.get("brand_updates") or {}).keys()),
        "memory_updates_applied": list((analysis.get("memory_updates") or {}).keys()),
    }


async def _download_file(url: str) -> bytes | None:
    if url.startswith("data:"):
        try:
            _, encoded = url.split(",", 1)
            return base64.b64decode(encoded)
        except Exception:
            return None
    # Handle local file:// URLs
    if url.startswith("file://"):
        path = Path(url.replace("file://", ""))
        if path.exists():
            return path.read_bytes()
        return None
    # Handle backend serve URLs — fetch directly
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return r.content
    except Exception:
        pass
    return None


def _media_type(ext: str) -> str | None:
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext)
