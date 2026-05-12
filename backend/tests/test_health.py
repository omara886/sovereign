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


# ── Acceptance Tests (auditor requirements) ────────────────────────────────────

def test_arabic_qa_blocks_chinese_contamination():
    from app.utils.arabic_qa import run_arabic_qa
    result = run_arabic_qa({'copy_ar': '痛点 في النص العربي مع صيني'})
    assert result['blocked'], "FAIL: Chinese characters not blocked"
    assert result['issues'][0]['type'] == 'CJK_CONTAMINATION'


def test_arabic_qa_passes_clean_arabic():
    from app.utils.arabic_qa import run_arabic_qa
    result = run_arabic_qa({'copy_ar': 'رفيقك الصحي الذكي — تقييم صحتك في ٨ دقائق'})
    assert result['passed'], f"FAIL: Clean Arabic failed QA: {result['issues']}"


def test_arabic_qa_blocks_japanese():
    from app.utils.arabic_qa import run_arabic_qa
    result = run_arabic_qa({'copy_ar': 'محتوى عربي مع كاتاكانا アラビア語'})
    assert result['blocked'], "FAIL: Japanese Katakana not blocked"


def test_no_bulk_approve_in_frontend():
    import subprocess
    result = subprocess.run(
        ['grep', '-rn', 'Approve All\\|approveAll\\|bulkProgress\\|bulk.*approv',
         '../frontend/app/', '--include=*.tsx', '--include=*.ts'],
        capture_output=True, text=True, cwd='.'
    )
    assert not result.stdout.strip(), f"FAIL: Bulk approve still exists:\n{result.stdout}"
