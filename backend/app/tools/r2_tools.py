import io
from pathlib import Path

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()

_LOCAL_FALLBACK = Path("/tmp/sovereign_r2")


def _get_client():
    """Return boto3 S3 client configured for Cloudflare R2."""
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        return None
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


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

    # Local fallback for development
    _LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
    ((_LOCAL_FALLBACK) / filename).write_bytes(file_bytes)
    return f"file://{_LOCAL_FALLBACK}/{filename}"


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
    return f"file://{_LOCAL_FALLBACK}/{filename}"
