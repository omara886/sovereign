from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.approvals import router as approvals_router
from app.routers.assets import router as assets_router
from app.routers.brand import router as brand_router
from app.routers.memory import router as memory_router
from app.routers.plans import router as plans_router
from app.routers.projects import router as projects_router
from app.routers.analytics import router as analytics_router
from app.routers.publish import router as publish_router
from app.routers.webhook import router as webhook_router
from app.routers.pipeline import router as pipeline_router
from app.routers.uploads import router as uploads_router
from app.scheduler.jobs import scheduler


settings = get_settings()


async def _ensure_schema():
    """Run any missing DDL that Alembic may not have applied yet."""
    from app.database import engine
    async with engine.connect() as conn:
        # brand_brief column added post-initial-migration
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE project_memory ADD COLUMN IF NOT EXISTS brand_brief TEXT"
        ))
        await conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _ensure_schema()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Sovereign API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-production-9eea5.up.railway.app",
        "https://backend-production-37a17.up.railway.app",
        "http://localhost:3000",
        settings.NEXT_PUBLIC_API_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(projects_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(brand_router, prefix="/api")
app.include_router(plans_router, prefix="/api")
app.include_router(assets_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(publish_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
