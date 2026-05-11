import asyncio

import httpx


async def publish_to_linkedin(asset, org_id: str, access_token: str) -> str:
    """Publish to LinkedIn as organization post. Returns post URN."""
    if not access_token or not org_id:
        return "linkedin_not_configured"

    copy = asset.copy_en or asset.copy_ar or ""
    if asset.design_url:
        copy = f"{copy}\n\nPreview: {asset.design_url}".strip()
    payload: dict = {
        "author": f"urn:li:organization:{org_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": copy},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.headers.get("x-restli-id", resp.json().get("id", "unknown"))


async def publish_to_instagram(asset, user_id: str, access_token: str) -> str:
    """Publish to Instagram Business via Meta Graph API. Returns media ID."""
    if not access_token or not user_id:
        return "instagram_not_configured"

    caption = asset.copy_ar or asset.copy_en or ""
    base = "https://graph.facebook.com/v19.0"

    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: Create media container
        container_payload: dict = {
            "caption": caption,
            "access_token": access_token,
        }
        if asset.design_url:
            container_payload["image_url"] = asset.design_url
            container_payload["media_type"] = "IMAGE"
        else:
            container_payload["media_type"] = "IMAGE"
            container_payload["image_url"] = "https://placehold.co/1080x1080"

        r1 = await client.post(f"{base}/{user_id}/media", json=container_payload)
        r1.raise_for_status()
        container_id = r1.json()["id"]

        # Step 2: Publish the container
        r2 = await client.post(
            f"{base}/{user_id}/media_publish",
            json={"creation_id": container_id, "access_token": access_token},
        )
        r2.raise_for_status()
        return r2.json().get("id", "unknown")


async def publish_to_twitter(asset, credentials: dict) -> str:
    """Post to X/Twitter via v2 API. Returns tweet ID."""
    if not credentials.get("access_token"):
        return "twitter_not_configured"

    text = asset.copy_ar or asset.copy_en or ""
    if len(text) > 280:
        text = text[:277] + "..."

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            headers={"Authorization": f"Bearer {credentials['access_token']}", "Content-Type": "application/json"},
            json={"text": text},
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("id", "unknown")
