import base64
import io
from pathlib import Path

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()

# Max size to store as base64 in DB (user uploads: logos, screenshots)
# Larger files (AI-generated designs) still use /tmp serve
_MAX_BASE64_BYTES = 300 * 1024  # 300 KB

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif", "image/svg+xml"}


def _get_client():
    """Return boto3 S3 client for Cloudflare R2. None if credentials missing or invalid."""
    account_id = (settings.R2_ACCOUNT_ID or "").strip()
    access_key = (settings.R2_ACCESS_KEY_ID or "").strip()
    secret_key = (settings.R2_SECRET_ACCESS_KEY or "").strip()
    if not account_id or not access_key or not secret_key:
        return None
    if "@" in account_id or "." in account_id:
        return None
    try:
        return boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    except Exception:
        return None


async def upload_to_r2(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload strategy:
    1. Real R2 bucket → returns public CDN URL (permanent)
    2. Small image without R2 → base64 data URL stored in DB (permanent, survives restarts)
    3. Large file without R2 → /tmp serve URL (ephemeral, breaks on restart — use R2)
    """
    client = _get_client()
    bucket = settings.R2_BUCKET_NAME
    public_base = settings.R2_PUBLIC_URL or ""

    # Strategy 1: Real R2
    if client and bucket:
        import asyncio
        await asyncio.to_thread(
            client.put_object,
            Bucket=bucket,
            Key=filename,
            Body=file_bytes,
            ContentType=content_type,
        )
        return f"{public_base.rstrip('/')}/{filename}"

    # Strategy 2: Small images only → base64 data URL (permanent, survives restarts, no file system)
    # User uploads stay small; large generated images should use /tmp so the browser never gets a multi-MB data URL.
    if content_type in _IMAGE_TYPES and len(file_bytes) <= _MAX_BASE64_BYTES:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return f"data:{content_type};base64,{b64}"

    # Strategy 3: Large or non-image file → /tmp serve (breaks on restart)
    target = Path("/tmp/sovereign_r2") / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)
    backend_base = settings.BACKEND_PUBLIC_URL or "https://backend-production-37a17.up.railway.app"
    return f"{backend_base.rstrip('/')}/api/uploads/serve/{filename}"


def get_signed_url(filename: str, expiry_seconds: int = 3600) -> str:
    client = _get_client()
    bucket = settings.R2_BUCKET_NAME
    if client and bucket:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": filename},
            ExpiresIn=expiry_seconds,
        )
    backend_base = settings.BACKEND_PUBLIC_URL or "https://backend-production-37a17.up.railway.app"
    return f"{backend_base.rstrip('/')}/api/uploads/serve/{filename}"
