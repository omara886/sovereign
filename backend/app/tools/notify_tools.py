import asyncio

import httpx

from app.config import get_settings

settings = get_settings()


async def send_email_resend(to: str, subject: str, html: str) -> bool:
    """Send email via Resend API. Returns True on success."""
    api_key = settings.RESEND_API_KEY
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": settings.RESEND_FROM_EMAIL or "sovereign@notifications.ai",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            return resp.status_code in (200, 201)
    except Exception:
        return False


async def send_telegram_notification(chat_id: str, text: str, keyboard: dict | None = None) -> bool:
    """Send message via Telegram Bot API. Returns True on success."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        return False
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = keyboard
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload,
            )
            return resp.status_code == 200
    except Exception:
        return False


async def setup_telegram_webhook(webhook_url: str) -> bool:
    """Register webhook URL with Telegram Bot API."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": webhook_url},
            )
            return resp.status_code == 200
    except Exception:
        return False
