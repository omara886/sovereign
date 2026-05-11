import base64
import io
import logging
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    import boto3
    from botocore.config import Config
except ModuleNotFoundError:
    boto3 = None
    Config = None

# Max size to store as base64 in DB (user uploads: logos, screenshots)
# Larger files (AI-generated designs) still use /tmp serve
_MAX_BASE64_BYTES = 300 * 1024  # 300 KB

_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif", "image/svg+xml"}


def _has_r2_credentials() -> bool:
    account_id = (settings.R2_ACCOUNT_ID or "").strip()
    access_key = (settings.R2_ACCESS_KEY_ID or "").strip()
    secret_key = (settings.R2_SECRET_ACCESS_KEY or "").strip()
    return bool(account_id and access_key and secret_key and "@" not in account_id and "." not in account_id)


def _get_client():
    """Return boto3 S3 client for Cloudflare R2. None if credentials missing or invalid."""
    if boto3 is None or Config is None:
        return None
    if not _has_r2_credentials():
        return None
    account_id = (settings.R2_ACCOUNT_ID or "").strip()
    access_key = (settings.R2_ACCESS_KEY_ID or "").strip()
    secret_key = (settings.R2_SECRET_ACCESS_KEY or "").strip()
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


def build_r2_url(filename: str) -> str:
    public_base = (settings.R2_PUBLIC_URL or "").strip()
    if public_base:
        return f"{public_base.rstrip('/')}/{filename}"
    backend_base = (settings.BACKEND_PUBLIC_URL or "https://backend-production-37a17.up.railway.app").rstrip("/")
    return f"{backend_base}/api/uploads/r2/{filename}"


def is_r2_configured() -> bool:
    return _get_client() is not None and bool((settings.R2_BUCKET_NAME or "").strip())


async def fetch_r2_object(filename: str) -> tuple[bytes | None, str | None]:
    client = _get_client()
    bucket = (settings.R2_BUCKET_NAME or "").strip()
    if not client or not bucket:
        logger.warning("R2 not configured for fetch: bucket=%s client=%s", bool(bucket), bool(client))
        return None, None

    def _read():
        obj = client.get_object(Bucket=bucket, Key=filename)
        body = obj["Body"].read()
        content_type = obj.get("ContentType")
        return body, content_type

    try:
        import asyncio
        return await asyncio.to_thread(_read)
    except Exception as exc:
        logger.error("R2 fetch failed for %s: %s", filename, exc, exc_info=True)
        return None, None


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
        logger.info("Uploaded to R2 bucket=%s key=%s", bucket, filename)
        return build_r2_url(filename)

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
    return build_r2_url(filename)
