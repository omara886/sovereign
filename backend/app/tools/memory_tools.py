from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BrandMemory, ProjectMemory


async def get_project_memory(db: AsyncSession, project_id: str):
    return (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))).scalar_one_or_none()


async def update_project_memory(db: AsyncSession, project_id: str, updates: dict):
    obj = await get_project_memory(db, project_id)
    if not obj:
        return None
    for k, v in updates.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_brand_memory(db: AsyncSession, project_id: str):
    return (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()


async def update_brand_memory(db: AsyncSession, project_id: str, updates: dict):
    obj = await get_brand_memory(db, project_id)
    if not obj:
        return None
    for k, v in updates.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj
