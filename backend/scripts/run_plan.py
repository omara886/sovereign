import asyncio
from app.database import SessionLocal
from app.agents.strategy import StrategyAgent
from app.models.project import Project
from sqlalchemy import select
from datetime import date

async def run():
    async with SessionLocal() as db:
        project = (await db.execute(select(Project).where(Project.slug == "therapia"))).scalar_one()
        agent = StrategyAgent()
        print("Running Strategy Agent for Therapia...")
        plan = await agent.create_plan(db, str(project.id), date.today())
        print("\nObjective:", plan.get("objective"))
        print("Funnel focus:", plan.get("funnel_focus"))
        print("Tactics:", len(plan.get("tactics", [])))
        print("\nRationale:", plan.get("rationale", "")[:300])
        print("\nTactics:")
        for t in plan.get("tactics", []):
            print(f"  - {t.get('channel')} / {t.get('asset_type')} / SAR {t.get('budget_estimate_sar')} / {t.get('rationale_simple', '')[:80]}")

asyncio.run(run())
