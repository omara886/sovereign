"""Run: python scripts/seed_therapia.py"""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models import BrandMemory, Organization, Project, ProjectMemory


async def main() -> None:
    async with SessionLocal() as db:
        org = (await db.execute(select(Organization).where(Organization.name == "Sovereign"))).scalar_one_or_none()
        if not org:
            org = Organization(name="Sovereign", owner_email="oalomran443@gmail.com", plan_type="internal")
            db.add(org)
            await db.flush()

        project = (await db.execute(select(Project).where(Project.slug == "therapia"))).scalar_one_or_none()
        if not project:
            project = Project(org_id=org.id, name="Therapia", slug="therapia", business_model="b2c", primary_goal="app_downloads_and_assessments", website_url="https://therapia.live")
            db.add(project)
            await db.flush()

        memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project.id))).scalar_one_or_none()
        if not memory:
            db.add(ProjectMemory(project_id=project.id, icp={"demographics": {"location": "Saudi Arabia"}}, tone="warm"))

        brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project.id))).scalar_one_or_none()
        if not brand:
            db.add(BrandMemory(project_id=project.id, is_provisional=True, color_palette={"primary": "#0A0A0A", "accent": "#C9A84C"}, typography={"arabic_font": "Cairo"}))

        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
