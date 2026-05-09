from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Asset
from app.schemas import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
async def list_assets(project_id: UUID | None = None, status: str | None = None, channel: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Asset)
    if project_id:
        q = q.where(Asset.project_id == project_id)
    if status:
        q = q.where(Asset.status == status)
    if channel:
        q = q.where(Asset.channel == channel)
    return (await db.execute(q)).scalars().all()


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Asset, asset_id)
    if not obj:
        raise HTTPException(404, "asset not found")
    return obj


@router.post("", response_model=AssetRead)
async def create_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)):
    obj = Asset(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/{asset_id}", response_model=AssetRead)
async def patch_asset(asset_id: UUID, payload: AssetUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Asset, asset_id)
    if not obj:
        raise HTTPException(404, "asset not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj
