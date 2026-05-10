import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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


@router.post("/{project_slug}")
async def upload_file(
    project_slug: str,
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

        return {
            "url": url,
            "filename": file.filename,
            "file_type": file_type,
            "size_kb": round(len(content) / 1024, 1),
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
