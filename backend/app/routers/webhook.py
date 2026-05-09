from fastapi import APIRouter

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/telegram")
async def telegram_webhook(payload: dict) -> dict:
    return {"ok": True, "received": bool(payload)}
