import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.crawl_tools import crawl_website, extract_brand_signals
from app.tools.memory_tools import get_brand_memory, update_brand_memory

SYSTEM_PROMPT = """You are the Brand Agent for Sovereign. You build and maintain the authoritative brand identity for each project.

On FIRST RUN (no BrandMemory exists):
1. Use crawl_website tool to fetch homepage, about page, and /brand pages
2. Extract brand signals: colors, fonts, tone, CTAs, value proposition via extract_brand_signals
3. Build a provisional brand guide — label every unconfirmed field clearly as "(provisional)"
4. Call save_brand_memory to store it with is_provisional=true

On REFRESH:
- Re-crawl the website and update changed fields only
- Do NOT overwrite fields already approved by the founder

CRITICAL: Never fabricate brand data. If no color info found, label as "(provisional — best guess)".
Transparency required. Mark is_provisional=true until founder approves.

Output JSON summary of what was saved."""

TOOLS = [
    {
        "name": "crawl_website",
        "description": "Crawl a website URL and extract brand signals (colors, fonts, tone words, CTAs)",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "extract_brand_signals",
        "description": "Process crawl result to extract structured brand signals",
        "input_schema": {
            "type": "object",
            "properties": {"crawl_result": {"type": "object"}},
            "required": ["crawl_result"],
        },
    },
    {
        "name": "get_brand_memory",
        "description": "Get existing brand memory for a project",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "save_brand_memory",
        "description": "Save new provisional brand memory for a project",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "color_palette": {"type": "object"},
                "typography": {"type": "object"},
                "visual_style": {"type": "string"},
                "image_style": {"type": "string"},
                "brand_voice": {"type": "string"},
                "dos": {"type": "array", "items": {"type": "string"}},
                "donts": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "update_brand_memory",
        "description": "Update specific fields of existing brand memory",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "updates": {"type": "object"},
            },
            "required": ["project_id", "updates"],
        },
    },
]


class BrandAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=4096)
        self.tool_implementations = {
            "crawl_website": self._crawl_website,
            "extract_brand_signals": self._extract_brand_signals,
            "get_brand_memory": self._get_brand_memory,
            "save_brand_memory": self._save_brand_memory,
            "update_brand_memory": self._update_brand_memory,
        }

    async def _crawl_website(self, db: AsyncSession, url: str) -> dict:
        return await crawl_website(url)

    async def _extract_brand_signals(self, db: AsyncSession, crawl_result: dict) -> dict:
        return extract_brand_signals(crawl_result)

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"exists": False}
        return {
            "exists": True,
            "color_palette": mem.color_palette,
            "typography": mem.typography,
            "visual_style": mem.visual_style,
            "brand_voice": mem.brand_voice,
            "is_provisional": mem.is_provisional,
        }

    async def _save_brand_memory(self, db: AsyncSession, project_id: str, **kwargs) -> dict:
        from app.models.brand_memory import BrandMemory
        existing = await get_brand_memory(db, project_id)
        if existing:
            return await self._update_brand_memory(db, project_id=project_id, updates=kwargs)
        mem = BrandMemory(project_id=project_id, is_provisional=True, **kwargs)
        db.add(mem)
        await db.commit()
        await db.refresh(mem)
        return {"saved": True, "id": str(mem.id)}

    async def _update_brand_memory(self, db: AsyncSession, project_id: str, updates: dict) -> dict:
        mem = await update_brand_memory(db, project_id, updates)
        return {"updated": True} if mem else {"error": "not found"}

    async def init_project_brand(self, db: AsyncSession, project_id: str, website_url: str) -> dict:
        msg = (
            f"Initialize brand memory for project_id={project_id}. "
            f"Website URL: {website_url}. "
            "Steps: (1) crawl_website, (2) extract_brand_signals on the result, "
            "(3) get_brand_memory to check if exists, "
            "(4) save_brand_memory with is_provisional=true if not exists, "
            "else update_brand_memory with new signals. "
            "Return what was saved."
        )
        return {"result": await self.run(msg, db)}
