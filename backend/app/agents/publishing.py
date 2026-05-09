from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.notify_tools import send_telegram_notification
from app.tools.social_tools import publish_to_instagram, publish_to_linkedin, publish_to_twitter
from app.config import get_settings

settings = get_settings()

CHANNEL_PUBLISHERS = {
    "linkedin": publish_to_linkedin,
    "instagram": publish_to_instagram,
    "x": publish_to_twitter,
}


class PublishingAgent:
    """
    Deterministic — no LLM needed. Verify approval → call social API → update DB.
    ABSOLUTE RULE: NEVER publish without verified approval record.
    """

    async def publish(self, db: AsyncSession, publish_job_id: str) -> dict:
        from app.models.publish_job import PublishJob
        from app.models.approval import Approval
        from app.models.asset import Asset

        job = await db.get(PublishJob, publish_job_id)
        if not job:
            return {"error": "publish job not found"}

        # CRITICAL: verify approval before doing anything
        approval = await db.get(Approval, job.approval_id)
        if not approval or approval.decision != "approved" or not approval.decided_at:
            await self._fail_job(db, job, "approval not verified — publish blocked")
            return {"error": "approval not verified"}

        asset = await db.get(Asset, job.asset_id)
        if not asset:
            await self._fail_job(db, job, "asset not found")
            return {"error": "asset not found"}

        if job.channel not in CHANNEL_PUBLISHERS:
            # Google Ads handled separately
            job.status = "published"
            job.published_at = datetime.now(timezone.utc)
            job.platform_post_id = "google_ads_pending"
            await db.commit()
            return {"status": "google_ads_deferred"}

        job.status = "publishing"
        await db.commit()

        try:
            publisher = CHANNEL_PUBLISHERS[job.channel]
            credentials = self._get_credentials(job.channel)
            platform_post_id = await publisher(asset, **credentials)

            job.status = "published"
            job.published_at = datetime.now(timezone.utc)
            job.platform_post_id = platform_post_id
            asset.status = "published"
            asset.platform_post_id = platform_post_id
            await db.commit()

            from app.models.audit_event import AuditEvent
            event = AuditEvent(
                actor_type="agent",
                actor_id="publishing_agent",
                action="asset_published",
                object_type="asset",
                object_id=asset.id,
                metadata={"channel": job.channel, "platform_post_id": platform_post_id},
            )
            db.add(event)
            await db.commit()

            await send_telegram_notification(
                chat_id=settings.TELEGRAM_CHAT_ID or "",
                text=f"✅ تم النشر على {job.channel} — {asset.type}",
            )
            return {"status": "published", "platform_post_id": platform_post_id}

        except Exception as exc:
            job.retry_count = (job.retry_count or 0) + 1
            if job.retry_count >= (job.max_retries or 3):
                await self._fail_job(db, job, str(exc))
                await send_telegram_notification(
                    chat_id=settings.TELEGRAM_CHAT_ID or "",
                    text=f"⚠️ فشل النشر على {job.channel} بعد {job.retry_count} محاولات. راجع لوحة التحكم.",
                )
                return {"error": "max retries reached", "detail": str(exc)}
            job.status = "scheduled"
            job.error_message = str(exc)
            await db.commit()
            return {"error": str(exc), "retry_count": job.retry_count}

    async def _fail_job(self, db, job, error_message: str) -> None:
        job.status = "failed"
        job.error_message = error_message
        await db.commit()

    def _get_credentials(self, channel: str) -> dict:
        if channel == "linkedin":
            return {"org_id": settings.LINKEDIN_ORG_ID or "", "access_token": settings.LINKEDIN_ACCESS_TOKEN or ""}
        if channel == "instagram":
            return {"user_id": settings.INSTAGRAM_USER_ID or "", "access_token": settings.INSTAGRAM_ACCESS_TOKEN or ""}
        if channel == "x":
            return {"credentials": {
                "api_key": settings.TWITTER_API_KEY or "",
                "api_secret": settings.TWITTER_API_SECRET or "",
                "access_token": settings.TWITTER_ACCESS_TOKEN or "",
                "access_secret": settings.TWITTER_ACCESS_SECRET or "",
            }}
        return {}
