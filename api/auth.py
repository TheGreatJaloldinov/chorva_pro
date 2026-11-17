"""Telegram Mini App initData verification and development-only local auth."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from app.config import BOT_TOKEN


def verify_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> dict:
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Serverda BOT_TOKEN sozlanmagan")
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash")
        auth_date = int(parsed.get("auth_date", "0"))
    except Exception:
        raise HTTPException(status_code=401, detail="Telegram tasdiqlash ma'lumoti noto'g'ri")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Telegram imzosi tasdiqlanmadi")
    now = int(time.time())
    if auth_date > now + 60 or now - auth_date > max_age_seconds:
        raise HTTPException(status_code=401, detail="Telegram sessiyasi eskirgan. Ilovani qayta oching.")
    try:
        user = json.loads(parsed["user"])
        telegram_id = int(user["id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Telegram foydalanuvchisi topilmadi")
    return {
        "telegram_id": telegram_id,
        "full_name": " ".join(x for x in [user.get("first_name", ""), user.get("last_name", "")] if x).strip(),
        "username": user.get("username", ""),
    }


async def telegram_identity(
    x_telegram_init_data: str | None = Header(default=None),
    x_dev_telegram_id: str | None = Header(default=None),
) -> dict:
    # This bypass is deliberately available only in local development.
    if os.getenv("APP_ENV", "production").lower() == "development" and x_dev_telegram_id:
        try:
            return {"telegram_id": int(x_dev_telegram_id), "full_name": "Mahalliy sinov foydalanuvchisi", "username": ""}
        except ValueError:
            raise HTTPException(status_code=400, detail="X-Dev-Telegram-Id noto'g'ri")
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Telegram Mini App orqali kiring")
    return verify_telegram_init_data(x_telegram_init_data)
