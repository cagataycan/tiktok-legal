"""
Twitter hesap token CRUD işlemleri — Supabase twitter_accounts tablosu.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from api.db.supabase_client import get_client

log = logging.getLogger(__name__)


def get_active_accounts() -> list[dict]:
    res = get_client().table("twitter_accounts").select("*").eq("is_active", True).execute()
    return res.data or []


def upsert_account(
    user_id: str,
    username: str,
    access_token: str,
    refresh_token: str,
    expires_at: str,
) -> dict:
    data = {
        "twitter_user_id":  user_id,
        "twitter_username": username,
        "access_token":     access_token,
        "refresh_token":    refresh_token,
        "token_expires_at": expires_at,
        "is_active":        True,
        "connected_at":     datetime.now(timezone.utc).isoformat(),
    }
    res = (
        get_client()
        .table("twitter_accounts")
        .upsert(data, on_conflict="twitter_user_id")
        .execute()
    )
    row = res.data[0]
    log.info(f"Twitter hesap kaydedildi: @{username} ({user_id})")
    return row


def update_tokens(account_id: str, access_token: str, refresh_token: str, expires_at: str) -> None:
    get_client().table("twitter_accounts").update({
        "access_token":     access_token,
        "refresh_token":    refresh_token,
        "token_expires_at": expires_at,
    }).eq("id", account_id).execute()


def mark_last_used(account_id: str) -> None:
    get_client().table("twitter_accounts").update({
        "last_used_at": datetime.now(timezone.utc).isoformat(),
        "last_error":   None,
    }).eq("id", account_id).execute()


def mark_error(account_id: str, error: str) -> None:
    get_client().table("twitter_accounts").update({
        "last_error": error[:500],
    }).eq("id", account_id).execute()


def deactivate_account(account_id: str) -> None:
    get_client().table("twitter_accounts").update({"is_active": False}).eq("id", account_id).execute()


def is_token_expired(account: dict) -> bool:
    expires_at = account.get("token_expires_at")
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= exp - timedelta(minutes=10)
    except Exception:
        return True
