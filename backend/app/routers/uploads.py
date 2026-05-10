import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal, get_db
from app.models.project import Project
from app.models.brand_memory import BrandMemory
from app.tools.r2_tools import upload_to_r2

router = APIRouter(prefix="/uploads", tags=["uploads"])
LOCAL_FALLBACK_DIR = Path("/tmp/sovereign_r2")

ALLOWED_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml",
    "application/pdf", "font/ttf", "font/otf", "font/woff", "font/woff2",
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


async def _run_asset_analysis(project_id: str, project_name: str, url: str, file_type: str, filename: str):
    """Background task: analyze uploaded asset with Claude Vision and update memory."""
    from app.agents.asset_analyzer import analyze_and_update
    async with SessionLocal() as db:
        try:
            result = await analyze_and_update(db, project_id, project_name, url, file_type, filename)
            print(f"asset_analyzer [{project_name}]: {result.get('summary')}")
        except Exception as exc:
            print(f"asset_analyzer error: {exc}")


@router.post("/{project_slug}")
async def upload_file(
    project_slug: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    import traceback
    try:
        project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "Project not found")

        content = await file.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(400, "File too large — max 10MB")

        content_type = file.content_type or "application/octet-stream"
        ext = (file.filename or "file").rsplit(".", 1)[-1].lower()
        filename = f"{project_slug}/{file_type}/{uuid.uuid4()}.{ext}"

        url = await upload_to_r2(content, filename, content_type)

        brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project.id))).scalar_one_or_none()
        if brand:
            if file_type == "logo":
                brand.logo_url = url
            elif file_type == "font":
                brand.arabic_font_url = url
            else:
                from sqlalchemy.orm.attributes import flag_modified
                templates = list(brand.templates or [])
                templates.append({"name": file.filename, "type": file_type, "r2_url": url})
                brand.templates = templates
                flag_modified(brand, "templates")
            await db.commit()

        # Trigger asset analysis in background — reads image, updates brand/project memory
        background_tasks.add_task(
            _run_asset_analysis,
            str(project.id), project.name, url, file_type, file.filename or filename
        )

        return {
            "url": url,
            "filename": file.filename,
            "file_type": file_type,
            "size_kb": round(len(content) / 1024, 1),
            "analysis": "started",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()[-500:]}")


@router.get("/serve/{project_slug}/{file_type}/{filename}")
async def serve_file(project_slug: str, file_type: str, filename: str):
    path = LOCAL_FALLBACK_DIR / project_slug / file_type / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


@router.post("/{project_slug}/analyze-now")
async def trigger_analysis(project_slug: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Manually re-run asset analysis on all uploaded assets for a project."""
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    from app.models.brand_memory import BrandMemory as BM
    brand = (await db.execute(select(BM).where(BM.project_id == project.id))).scalar_one_or_none()
    urls = []
    if brand:
        if brand.logo_url:
            background_tasks.add_task(_run_asset_analysis, str(project.id), project.name, brand.logo_url, "logo", "logo")
            urls.append("logo")
        for t in (brand.templates or []):
            if t.get("r2_url"):
                background_tasks.add_task(_run_asset_analysis, str(project.id), project.name, t["r2_url"], t.get("type", "other"), t.get("name", "asset"))
                urls.append(t.get("name", "asset"))
    return {"triggered": len(urls), "assets": urls}


@router.get("/{project_slug}")
async def list_uploads(project_slug: str, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project.id))).scalar_one_or_none()
    if not brand:
        return {"files": []}

    files = []
    if brand.logo_url:
        files.append({"type": "logo", "url": brand.logo_url, "name": "Logo"})
    if brand.arabic_font_url:
        files.append({"type": "font", "url": brand.arabic_font_url, "name": "Arabic Font"})
    for t in (brand.templates or []):
        files.append({"type": t.get("type", "other"), "url": t.get("r2_url"), "name": t.get("name", "File")})

    return {"files": files}
