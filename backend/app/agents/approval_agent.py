from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base import BaseAgent
from app.tools.notify_tools import send_email_resend, send_telegram_notification
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are the Approval Agent for Sovereign. You route QA-passed items to the founder's approval inbox.

You send notifications. You do NOT make approval decisions. Only the founder does.

Notification rules:
1. Package each item as a clear card: channel, copy excerpt, funnel stage, rationale
2. Send email via Resend with clean summary
3. Send Telegram with inline approve/review buttons
4. Create approval record in DB (decision=null, pending)
5. NEVER mark anything approved automatically

Email subject: "Sovereign: [N] محتوى جاهز للموافقة — [Project]"
Telegram format:
"🔔 يا عمر — عندك [N] محتوى جاهز على [Project]
أبرز المحتوى: [brief list]
راجع وافق من هنا: [link]"

NEVER send more than 3 Telegram messages per day per project."""


class ApprovalAgent:
    """
    Not a Claude agent — notification dispatch is deterministic.
    This class sends notifications and creates approval records without LLM overhead.
    """

    async def notify_pending_assets(
        self,
        db: AsyncSession,
        project_id: str,
        project_name: str,
        assets: list,
    ) -> dict:
        from app.models.approval import Approval

        approval_ids = []
        for asset in assets:
            existing = (await db.execute(
                select(Approval).where(Approval.asset_id == asset.id, Approval.decision.is_(None))
            )).scalar_one_or_none()
            if not existing:
                approval = Approval(asset_id=asset.id)
                db.add(approval)
                await db.commit()
                await db.refresh(approval)
                approval_ids.append(str(approval.id))
                asset.status = "approval_pending"
                await db.commit()

        if not approval_ids:
            return {"sent": False, "reason": "no new approvals needed"}

        n = len(approval_ids)
        subject = f"Sovereign: {n} محتوى جاهز للموافقة — {project_name}"
        items_summary = "\n".join(
            f"• {a.channel} / {a.type} / {(a.copy_ar or '')[:60]}..."
            for a in assets[:3]
        )
        html = f"""
        <div dir="rtl" style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #C9A84C;">Sovereign — موافقة مطلوبة</h2>
          <p>عندك <strong>{n}</strong> محتوى جاهز للمراجعة في مشروع <strong>{project_name}</strong></p>
          <pre style="background: #1E293B; color: #F8F6F1; padding: 16px; border-radius: 8px;">{items_summary}</pre>
          <a href="http://localhost:3000/inbox" style="background: #C9A84C; color: #0A0A0A; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 16px;">
            راجع وافق الحين →
          </a>
        </div>
        """
        email_sent = await send_email_resend(
            to=settings.FOUNDER_EMAIL,
            subject=subject,
            html=html,
        )
        tg_text = (
            f"🔔 يا عمر — عندك {n} محتوى جاهز على {project_name}\n\n"
            f"{items_summary}\n\n"
            "راجع وافق من هنا: http://localhost:3000/inbox"
        )
        tg_sent = await send_telegram_notification(
            chat_id=settings.TELEGRAM_CHAT_ID or "",
            text=tg_text,
        )
        return {
            "approval_ids": approval_ids,
            "email_sent": email_sent,
            "telegram_sent": tg_sent,
            "count": n,
        }

    async def notify_plan_ready(
        self,
        db: AsyncSession,
        project_id: str,
        project_name: str,
        plan,
    ) -> dict:
        from app.models.approval import Approval

        approval = Approval(weekly_plan_id=plan.id)
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        plan.status = "pending_approval"
        await db.commit()

        subject = f"Sovereign: خطة {project_name} لهذا الأسبوع جاهزة — موافقتك مطلوبة"
        html = f"""
        <div dir="rtl" style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #C9A84C;">الخطة الأسبوعية جاهزة</h2>
          <p><strong>{project_name}</strong> — {plan.objective}</p>
          <p>التركيز: {plan.funnel_focus} | الميزانية: SAR {plan.total_budget_estimate}</p>
          <p>{plan.rationale}</p>
          <a href="http://localhost:3000/plans/{plan.week_start}" style="background: #C9A84C; color: #0A0A0A; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 16px;">
            راجع الخطة →
          </a>
        </div>
        """
        email_sent = await send_email_resend(settings.FOUNDER_EMAIL, subject, html)
        tg_text = (
            f"📋 خطة {project_name} لهذا الأسبوع جاهزة!\n\n"
            f"الهدف: {plan.objective}\n"
            f"التركيز: {plan.funnel_focus}\n"
            f"الميزانية: SAR {plan.total_budget_estimate}\n\n"
            "راجع الخطة: http://localhost:3000/inbox"
        )
        tg_sent = await send_telegram_notification(settings.TELEGRAM_CHAT_ID or "", tg_text)
        return {"approval_id": str(approval.id), "email_sent": email_sent, "telegram_sent": tg_sent}
