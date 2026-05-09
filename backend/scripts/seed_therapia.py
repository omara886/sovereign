"""
Therapia onboarding seed.
Run: python scripts/seed_therapia.py
Creates: Organization, Therapia Project, full ProjectMemory, provisional BrandMemory.
Then runs Brand Agent to crawl therapia.live.
"""
import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models.organization import Organization
from app.models.project import Project
from app.models.project_memory import ProjectMemory
from app.models.brand_memory import BrandMemory


THERAPIA_ICP = {
    "demographics": {
        "age_range": "25-40",
        "gender": "mixed",
        "location": "Saudi Arabia primary, GCC secondary",
        "context": "working professionals, health-conscious, mobile-first"
    },
    "pain_points": [
        "لا وقت للجلسات الوجاهية",
        "الوصم الاجتماعي حول الصحة النفسية",
        "صعوبة إيجاد متخصص موثوق",
        "No accessible mental health resources in Arabic",
    ],
    "goals": [
        "تحسين الصحة النفسية والجسدية",
        "بداية صحية سريعة وخاصة",
        "فهم حالتهم الصحية",
    ],
    "channels_they_use": ["Instagram", "X/Twitter", "LinkedIn", "WhatsApp"],
    "buying_triggers": ["friend recommendation", "doctor referral", "social media discovery"],
}

THERAPIA_FUNNEL_GOALS = {
    "awareness": {"metric": "instagram_followers", "target": 5000, "current": 0},
    "consideration": {"metric": "website_visits", "target": 2000, "current": 0},
    "conversion": {"metric": "app_downloads", "target": 500, "current": 0},
    "retention": {"metric": "assessments_completed", "target": 200, "current": 0},
}

THERAPIA_OFFERS = [
    {
        "name": "تقييم الصحة",
        "price": "مجاني",
        "description": "تقييم صحي شامل في دقائق",
        "cta": "ابدأ التقييم الآن",
        "landing_url": "https://therapia.live",
    }
]

THERAPIA_CONSTRAINTS = {
    "budget_cap_sar": 2000,
    "excluded_topics": [
        "medical diagnoses",
        "clinical treatment claims",
        "guaranteed results",
        "يعالج",
        "مضمون 100%",
        "علمياً مثبت",
    ],
    "competitor_mentions_allowed": False,
}


async def main() -> None:
    async with SessionLocal() as db:
        # 1. Organization
        org = (await db.execute(
            select(Organization).where(Organization.owner_email == "oalomran443@gmail.com")
        )).scalar_one_or_none()
        if not org:
            org = Organization(
                name="Omar's Ventures",
                owner_email="oalomran443@gmail.com",
                plan_type="internal",
            )
            db.add(org)
            await db.flush()
            print(f"✓ Organization created: {org.name} ({org.id})")
        else:
            print(f"→ Organization exists: {org.name}")

        # 2. Therapia Project
        project = (await db.execute(
            select(Project).where(Project.slug == "therapia")
        )).scalar_one_or_none()
        if not project:
            project = Project(
                org_id=org.id,
                name="Therapia",
                slug="therapia",
                business_model="b2c",
                primary_goal="app_downloads_and_health_assessments_completed",
                website_url="https://therapia.live",
                priority=1,
                status="active",
                channels=[
                    {"channel": "instagram", "account_id": None, "connected": False},
                    {"channel": "linkedin", "account_id": None, "connected": False},
                    {"channel": "x", "account_id": None, "connected": False},
                ],
            )
            db.add(project)
            await db.flush()
            print(f"✓ Project created: Therapia ({project.id})")
        else:
            print(f"→ Project exists: Therapia ({project.id})")

        # 3. ProjectMemory
        memory = (await db.execute(
            select(ProjectMemory).where(ProjectMemory.project_id == project.id)
        )).scalar_one_or_none()
        if not memory:
            memory = ProjectMemory(
                project_id=project.id,
                icp=THERAPIA_ICP,
                positioning="Therapia — تطبيق صحتك الشخصي في جيبك",
                offers=THERAPIA_OFFERS,
                tone="دافئ، داعم، إيجابي، لا يستخدم الخوف كدافع، صادق وواضح",
                languages=["ar", "en"],
                funnel_goals=THERAPIA_FUNNEL_GOALS,
                constraints=THERAPIA_CONSTRAINTS,
                approved_examples=[],
                rejected_examples=[],
                performance_learnings=None,
            )
            db.add(memory)
            print("✓ ProjectMemory created with full ICP, funnel goals, constraints")
        else:
            print("→ ProjectMemory exists")

        # 4. Provisional BrandMemory (will be updated by Brand Agent crawl)
        brand = (await db.execute(
            select(BrandMemory).where(BrandMemory.project_id == project.id)
        )).scalar_one_or_none()
        if not brand:
            brand = BrandMemory(
                project_id=project.id,
                is_provisional=True,
                color_palette={
                    "primary": "#0A0A0A",
                    "secondary": "#1E293B",
                    "accent": "#C9A84C",
                    "background": "#0A0A0A",
                    "text": "#F8F6F1",
                },
                typography={
                    "headline_font": "Cormorant Garamond",
                    "body_font": "IBM Plex Sans",
                    "arabic_font": "Cairo",
                    "data_font": "IBM Plex Mono",
                },
                visual_style="(provisional) clean health, warm tones",
                image_style="(provisional) lifestyle photography, warm light",
                brand_voice="(provisional) warm, supportive, health-positive, never fear-mongering",
                dos=[
                    "Use warm, conversational Gulf Arabic",
                    "Focus on empowerment not fear",
                    "Specific CTAs with clear next steps",
                    "Show real benefits in simple language",
                ],
                donts=[
                    "No medical claims without substantiation",
                    "No فصحى — always Gulf Saudi dialect",
                    "No fear-based messaging",
                    "No generic CTAs like 'اضغط هنا'",
                ],
                templates=[],
                rejected_styles=[],
            )
            db.add(brand)
            print("✓ BrandMemory created (provisional — crawl therapia.live to update)")
        else:
            print("→ BrandMemory exists")

        await db.commit()
        print(f"\n✅ Therapia seed complete. Project ID: {project.id}")
        print("\nNext steps:")
        print("  1. Run Brand Agent to crawl therapia.live")
        print("  2. Review provisional brand guide at /projects/therapia")
        print("  3. Approve brand guide → weekly plan generates Monday 8AM")

        # 5. Run Brand Agent crawl
        print("\n🕷️  Running Brand Agent on therapia.live...")
        try:
            from app.agents.brand import BrandAgent
            agent = BrandAgent()
            result = await agent.init_project_brand(db, str(project.id), "https://therapia.live")
            print(f"✓ Brand Agent complete: {result.get('result', '')[:200]}")
        except Exception as exc:
            print(f"⚠ Brand Agent failed (non-blocking): {exc}")
            print("  → Provisional brand guide is usable. Run manually later.")


if __name__ == "__main__":
    asyncio.run(main())
