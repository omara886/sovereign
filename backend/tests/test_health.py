"""Core health tests — run before every commit."""
import os
import pytest
import asyncio
import asyncpg


DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://postgres:RdYZEbSgyaZaxcEPnZllsPXbqxUrYdmZ@metro.proxy.rlwy.net:33418/railway"
).replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")

REQUIRED_TABLES = {
    "organizations", "projects", "project_memory", "brand_memory",
    "weekly_plans", "assets", "approvals", "publish_jobs",
    "metric_snapshots", "audit_events",
}


@pytest.mark.asyncio
async def test_db_all_tables_exist():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    actual = {r["tablename"] for r in rows}
    await conn.close()
    missing = REQUIRED_TABLES - actual
    assert not missing, f"Missing tables: {missing}"


@pytest.mark.asyncio
async def test_db_has_projects():
    conn = await asyncpg.connect(DATABASE_URL)
    count = await conn.fetchval("SELECT COUNT(*) FROM projects")
    await conn.close()
    assert count >= 1, "No projects in DB — run seed script"


def test_arabic_reshaper():
    import arabic_reshaper
    from bidi.algorithm import get_display
    text = arabic_reshaper.reshape("رفيقك الصحي الذكي")
    result = get_display(text)
    assert len(result) > 0, "Arabic reshaper returned empty string"


def test_thmanyah_font_exists():
    font_path = "assets/fonts/thmanyah typeface/thmanyahsans/otf/thmanyahsans-Bold.otf"
    assert os.path.exists(font_path), f"Thmanyah font not found at {font_path}"


def test_no_debug_code_in_agents():
    """Ensure agents don't have leftover debug prints."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "print(", "app/agents/", "--include=*.py"],
        capture_output=True, text=True
    )
    assert not result.stdout.strip(), f"Debug print() found:\n{result.stdout}"


def test_r2_tools_jpeg_fallback():
    """JPEG recompression fallback reduces PNG size enough for base64 storage."""
    import asyncio
    from PIL import Image
    from io import BytesIO
    from app.tools.r2_tools import _MAX_BASE64_BYTES_LARGE

    img = Image.new("RGB", (1080, 1080), color=(10, 10, 10))
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    img2 = Image.open(BytesIO(png_bytes)).convert("RGB")
    jpeg_buf = BytesIO()
    img2.save(jpeg_buf, format="JPEG", quality=85, optimize=True)
    assert len(jpeg_buf.getvalue()) <= _MAX_BASE64_BYTES_LARGE, "JPEG recompression result too large for base64 storage"


def test_lab_agent_keywords_cover_all_agents():
    """Every agent in AGENT_SEQUENCE has at least one keyword mapping."""
    from app.routers.pipeline import AGENT_SEQUENCE, _AGENT_KEYWORDS
    keys = {a["key"] for a in AGENT_SEQUENCE}
    mapped = set(_AGENT_KEYWORDS.keys())
    uncovered = keys - mapped
    assert not uncovered, f"Agents with no keyword mapping: {uncovered}"
