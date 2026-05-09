import json
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base import BaseAgent
from app.tools.memory_tools import get_project_memory, update_project_memory
from app.tools.notify_tools import send_email_resend, send_telegram_notification
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are the Analytics Agent for Sovereign. You measure results, explain what happened in simple terms, and feed learnings back into project memory.

Weekly cycle:
1. Review the metrics snapshot data provided
2. Calculate week-over-week changes for key metrics
3. Identify top 3 performing assets (by engagement + conversion)
4. Identify bottom 3 performers
5. Update project memory with 3-5 performance learning bullet points
6. Generate a simple Arabic weekly report (no jargon)

Report language rules:
- Arabic primary, simple and clear
- "المتابعين ارتفعوا 12% هالأسبوع" not "Follower growth rate increased by 12%"
- Honest about what didn't work
- End with 2-3 specific recommendations for next week

Report structure:
1. ملخص الأسبوع (2 sentences)
2. أبرز النتائج (key metrics vs targets)
3. المحتوى الأكثر أثراً (top assets)
4. ما لم ينجح وليش (failures + hypothesis)
5. توصيات الأسبوع الجاي

Output JSON:
{
  "report_ar": "Full Arabic report text",
  "report_en": "Full English report text",
  "top_performers": ["asset_id1", "asset_id2"],
  "bottom_performers": ["asset_id3"],
  "performance_learnings": ["learning 1", "learning 2", "learning 3"],
  "key_metrics": {"metric_name": {"value": 123, "change_pct": 12.5}}
}"""

TOOLS = [
    {
        "name": "get_project_memory",
        "description": "Get current project memory with funnel goals and past learnings",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
]


class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=4096)
        self.tool_implementations = {
            "get_project_memory": self._get_project_memory,
        }

    async def _get_project_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_project_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {
            "funnel_goals": mem.funnel_goals,
            "approved_examples": mem.approved_examples,
            "rejected_examples": mem.rejected_examples,
            "performance_learnings": mem.performance_learnings,
        }

    async def run_weekly_report(
        self,
        db: AsyncSession,
        project_id: str,
        project_name: str,
        metrics_snapshot: list[dict],
        published_assets: list[dict],
        week_start: date,
        week_end: date,
    ) -> dict:
        msg = (
            f"Generate weekly analytics report for project_id={project_id} ({project_name}). "
            f"Week: {week_start} to {week_end}.\n\n"
            f"Published assets this week: {json.dumps(published_assets[:10], default=str)}\n\n"
            f"Metrics snapshots: {json.dumps(metrics_snapshot[:20], default=str)}\n\n"
            "Call get_project_memory to see funnel targets. "
            "Then analyze the data and generate the full report JSON."
        )
        result = await self.run(msg, db)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                report_data = json.loads(result[start:end])
            except json.JSONDecodeError:
                report_data = {"report_ar": result, "report_en": result, "performance_learnings": []}
        else:
            report_data = {"report_ar": result, "report_en": result, "performance_learnings": []}

        # Update project memory with new learnings
        if report_data.get("performance_learnings"):
            await update_project_memory(db, project_id, {
                "performance_learnings": "\n".join(report_data["performance_learnings"])
            })

        # Send report to founder
        subject = f"Sovereign: تقرير أسبوع {week_start} — {project_name}"
        html = f"""
        <div dir="rtl" style="font-family: sans-serif; max-width: 700px; margin: 0 auto;">
          <h2 style="color: #C9A84C;">التقرير الأسبوعي — {project_name}</h2>
          <div style="background: #1E293B; color: #F8F6F1; padding: 24px; border-radius: 12px; white-space: pre-wrap;">
            {report_data.get("report_ar", "")}
          </div>
          <hr style="border-color: rgba(201,168,76,0.2); margin: 24px 0;">
          <div style="color: #666; font-size: 14px; white-space: pre-wrap;">
            {report_data.get("report_en", "")}
          </div>
        </div>
        """
        await send_email_resend(settings.FOUNDER_EMAIL, subject, html)
        tg_summary = (report_data.get("report_ar", "") or "")[:400]
        await send_telegram_notification(
            settings.TELEGRAM_CHAT_ID or "",
            f"📊 التقرير الأسبوعي — {project_name}\n\n{tg_summary}\n\n[التقرير الكامل في بريدك]",
        )
        return report_data
