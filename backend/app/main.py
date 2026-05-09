from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


settings = get_settings()
app = FastAPI(title="Sovereign API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.NEXT_PUBLIC_API_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
