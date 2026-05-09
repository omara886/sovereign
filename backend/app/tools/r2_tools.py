import os
from pathlib import Path

from app.config import get_settings


settings = get_settings()
_LOCAL_R2_DIR = Path("/tmp/sovereign_r2")
_LOCAL_R2_DIR.mkdir(parents=True, exist_ok=True)


async def upload_to_r2(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    target = _LOCAL_R2_DIR / filename
    target.write_bytes(file_bytes)
    base = settings.R2_PUBLIC_URL or "https://local-r2.invalid"
    return f"{base.rstrip('/')}/{filename}"


def get_signed_url(filename: str, expiry_seconds: int = 3600) -> str:
    base = settings.R2_PUBLIC_URL or "https://local-r2.invalid"
    return f"{base.rstrip('/')}/{filename}?exp={expiry_seconds}"
