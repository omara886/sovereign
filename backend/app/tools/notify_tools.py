async def send_email_resend(to: str, subject: str, html: str) -> bool:
    return True


async def send_telegram_notification(chat_id: str, text: str, keyboard=None) -> bool:
    return True


async def setup_telegram_webhook(webhook_url: str) -> bool:
    return True
