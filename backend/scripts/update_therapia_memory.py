"""
Run: python -m scripts.update_therapia_memory
Updates Therapia ProjectMemory with Omar's feedback constraints.
"""
import asyncio
from sqlalchemy import select
from app.database import SessionLocal
from app.models.project import Project
from app.models.project_memory import ProjectMemory


async def main():
    async with SessionLocal() as db:
        project = (await db.execute(select(Project).where(Project.slug == "therapia"))).scalar_one()
        memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project.id))).scalar_one()

        # Update constraints with Omar's feedback
        constraints = dict(memory.constraints or {})
        constraints["excluded_topics"] = [
            "mental health",
            "mental illness",
            "therapy",
            "psychiatry",
            "depression",
            "anxiety disorder",
            "medical diagnoses",
            "clinical treatment claims",
            "guaranteed results",
            "يعالج",
            "مضمون 100%",
            "علمياً مثبت",
            "طب نفسي",
            "اكتئاب",
        ]

        memory.constraints = constraints
        memory.version = (memory.version or 1) + 1

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(memory, "constraints")
        await db.commit()
        print(f"✓ Therapia constraints updated — excluded topics: {len(constraints['excluded_topics'])}")
        print("Excluded:", constraints["excluded_topics"])


asyncio.run(main())
