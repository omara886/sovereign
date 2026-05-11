from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, PublishJob


async def process_publish_queue(db: AsyncSession) -> int:
    jobs = (await db.execute(select(PublishJob).where(PublishJob.status == "scheduled"))).scalars().all()
    count = 0
    for job in jobs:
        asset = await db.get(Asset, job.asset_id)
        if not asset:
            continue
        job.status = "published"
        job.platform_post_id = f"publish_{job.channel}_{job.id}"
        asset.status = "published"
        asset.platform_post_id = job.platform_post_id
        count += 1
    await db.commit()
    return count
