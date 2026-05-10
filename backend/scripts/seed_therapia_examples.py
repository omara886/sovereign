"""
Seed real Gulf Saudi approved/rejected examples for Therapia.
Run: python -m scripts.seed_therapia_examples
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.database import SessionLocal
from app.models.brand_memory import BrandMemory
from app.models.project import Project
from app.models.project_memory import ProjectMemory

APPROVED_EXAMPLES = [
    {
        "channel": "instagram",
        "copy_ar": "وش يصير لما تنام 8 ساعات كل يوم؟\n\nجسمك يشكرك، تركيزك يزيد، ومزاجك يتحسن.\n\nجرّب Therapia لمدة أسبوع — سجّل نومك، شوف الفرق بنفسك 💪\n\nابدأ الحين ←",
        "copy_en": "What happens when you sleep 8 hours every day?\n\nYour body thanks you. Your focus sharpens. Your mood lifts.\n\nTry Therapia for one week — track your sleep, see the difference yourself.\n\nStart now →",
        "why_it_works": "Opens with a question, uses Gulf vocabulary, specific benefit, clear CTA",
        "channel_format": "instagram_post",
    },
    {
        "channel": "instagram",
        "copy_ar": "ستة أشهر من متابعة صحتي مع Therapia — وش تغير؟\n\n✅ شربت ماء أكثر\n✅ نمت أبكر\n✅ حسيت بفرق واضح\n\nما احتجت دكتور. احتجت نظام.\n\nTherapia يساعدك تبني العادة الصح 🏃",
        "copy_en": "Six months tracking my health with Therapia — what changed?\n\nDrank more water. Slept earlier. Felt the difference.\n\nDidn't need a doctor. Needed a system.\n\nTherapia helps you build the right habits.",
        "why_it_works": "Specific timeframe, concrete habits, relatable, not medical",
        "channel_format": "instagram_post",
    },
    {
        "channel": "instagram",
        "copy_ar": "الصحة مو بس الجيم.\n\nالنوم. الماء. الخطوات. الضغط.\n\nTherapia يجمع كل هذا في مكان واحد — تتابعه يومياً بدون تعقيد.",
        "copy_en": "Health is not just the gym.\n\nSleep. Water. Steps. Stress.\n\nTherapia brings it all together — track it daily without the complexity.",
        "why_it_works": "Simple, short, relatable Saudi reality, not preachy",
        "channel_format": "instagram_story",
    },
]

REJECTED_EXAMPLES = [
    {
        "channel": "instagram",
        "copy_ar": "يا صديقي، هل تعاني من الإجهاد والضغط النفسي؟ تطبيق Therapia يساعدك على تحقيق التوازن في حياتك وتعزيز صحتك النفسية والجسدية.",
        "rejection_reason": "Egyptian Arabic (يا صديقي), mentions psychological health (excluded topic), too formal, sounds like an ad",
        "what_to_avoid": "يا صديقي / نفسية / formal MSA / ad-speak",
    },
    {
        "channel": "instagram",
        "copy_ar": "ابدأ رحلتك نحو حياة أكثر صحة وسعادة مع تطبيق Therapia. اكتشف قوة التتبع اليومي لعاداتك الصحية.",
        "rejection_reason": "Robotic marketing language, رحلة (journey cliché), اكتشف (discover cliché), reads like AI",
        "what_to_avoid": "رحلة / اكتشف / حياة أكثر سعادة / corporate phrasing",
    },
]

BRAND_MEMORY_UPDATES = {
    "brand_voice": "Saudi Gulf friend who genuinely cares about your health. Talks like WhatsApp, not a brochure. Specific, honest, not preachy.",
    "is_provisional": False,
    "dos": [
        "Open with a real observation or question a Saudi would actually say",
        "Use خل، شوف، وش، يبيلك، الحين، يلا — natural Gulf vocabulary",
        "Give one specific, concrete benefit — not a list of vague claims",
        "End with a specific CTA from the offers list",
        "Keep it short — if it takes more than 10 seconds to read, cut it",
    ],
    "donts": [
        "Never say يا صديقي or حبيبي — Egyptian markers",
        "Never use رحلة (journey), اكتشف (discover), قوة (power) — AI clichés",
        "Never mention mental health, psychology, or therapy (excluded topic)",
        "Never sound like a doctor or give medical advice",
        "Never use فصحى unless context is explicitly formal",
        "Never start with Are you..., Do you..., Unlock..., Discover...",
    ],
}


async def main() -> None:
    async with SessionLocal() as db:
        project = (await db.execute(select(Project).where(Project.slug == "therapia"))).scalar_one()
        memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project.id))).scalar_one()
        brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project.id))).scalar_one()

        memory.approved_examples = APPROVED_EXAMPLES
        memory.rejected_examples = REJECTED_EXAMPLES
        memory.tone = "Gulf Saudi — warm, direct, like a fit Saudi friend. WhatsApp register, not corporate. Use: خل، شوف، وش، يبيلك، الحين، يلا. Never: يا صديقي، رحلة، اكتشف، نفسي."
        flag_modified(memory, "approved_examples")
        flag_modified(memory, "rejected_examples")
        memory.version = (memory.version or 1) + 1

        for k, v in BRAND_MEMORY_UPDATES.items():
            setattr(brand, k, v)
        flag_modified(brand, "dos")
        flag_modified(brand, "donts")

        await db.commit()
        print(f"✓ Seeded {len(APPROVED_EXAMPLES)} approved + {len(REJECTED_EXAMPLES)} rejected examples")
        print("✓ Brand voice updated and approved (is_provisional=False)")


if __name__ == "__main__":
    asyncio.run(main())
