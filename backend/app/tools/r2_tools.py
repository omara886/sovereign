import io
from pathlib import Path

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()

_LOCAL_FALLBACK = Path("/tmp/sovereign_r2")


def _get_client():
    """Return boto3 S3 client configured for Cloudflare R2. Returns None if any credential is missing or invalid."""
    account_id = (settings.R2_ACCOUNT_ID or "").strip()
    access_key = (settings.R2_ACCESS_KEY_ID or "").strip()
    secret_key = (settings.R2_SECRET_ACCESS_KEY or "").strip()

    # Require all three — and account_id must look like a Cloudflare ID (not an email)
    if not account_id or not access_key or not secret_key:
        return None
    if "@" in account_id or "." in account_id:
        # Misconfigured — account ID should be a hex string, not an email/URL
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
    """Upload to Cloudflare R2. Falls back to /tmp if credentials not set."""
    client = _get_client()
    bucket = settings.R2_BUCKET_NAME
    public_base = settings.R2_PUBLIC_URL or ""

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

    # Local fallback — create subdirs since filename includes slashes e.g. therapia/logo/uuid.png
    target = _LOCAL_FALLBACK / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)
    backend_base = settings.BACKEND_PUBLIC_URL or "https://backend-production-37a17.up.railway.app"
    return f"{backend_base.rstrip('/')}/api/uploads/serve/{filename}"


def get_signed_url(filename: str, expiry_seconds: int = 3600) -> str:
    """Generate presigned URL for private R2 object."""
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
