"""
TikTok hesap token CRUD işlemleri — Supabase tiktok_accounts tablosu.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from api.db.supabase_client import get_client

log = logging.getLogger(__name__)


def get_active_accounts() -> list[dict]:
    """Tüm aktif TikTok hesaplarını döner."""
    res = get_client().table("tiktok_accounts").select("*").eq("is_active", True).execute()
    return res.data or []


def upsert_account(
    open_id: str,
    username: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
) -> dict:
    """Hesabı ekler veya günceller (open_id unique key)."""
    data = {
        "tiktok_open_id":    open_id,
        "tiktok_username":   username,
        "access_token":      access_token,
        "refresh_token":     refresh_token,
        "token_expires_at":  expires_at,
        "is_active":         True,
        "connected_at":      datetime.now(timezone.utc).isoformat(),
    }
    res = (
        get_client()
        .table("tiktok_accounts")
        .upsert(data, on_conflict="tiktok_open_id")
        .execute()
    )
    row = res.data[0]
    log.info(f"Hesap kaydedildi: @{username} ({open_id})")
    return row


def update_tokens(
    account_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
) -> None:
    """Token yenileme sonrası güncelle."""
    get_client().table("tiktok_accounts").update({
        "access_token":     access_token,
        "refresh_token":    refresh_token,
        "token_expires_at": expires_at,
    }).eq("id", account_id).execute()


def mark_last_used(account_id: str) -> None:
    get_client().table("tiktok_accounts").update({
        "last_used_at": datetime.now(timezone.utc).isoformat(),
        "last_error":   None,
    }).eq("id", account_id).execute()


def mark_error(account_id: str, error: str) -> None:
    get_client().table("tiktok_accounts").update({
        "last_error": error[:500],
    }).eq("id", account_id).execute()


def deactivate_account(account_id: str) -> None:
    get_client().table("tiktok_accounts").update({"is_active": False}).eq("id", account_id).execute()
    log.info(f"Hesap deaktive edildi: {account_id}")


def is_token_expired(account: dict, buffer_seconds: int = 3600) -> bool:
    """Token süresi dolmuş veya 1 saat içinde dolacak mı?"""
    expires_at = account.get("token_expires_at")
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= (exp - timedelta(seconds=buffer_seconds))
    except Exception:
        return True
