"""
TikTok OAuth 2.0 Router
========================
GET  /api/auth/tiktok            → TikTok yetkilendirme sayfasına yönlendir
GET  /api/auth/tiktok/callback   → Code'u token ile değiştir, Supabase'e kaydet
DELETE /api/auth/tiktok/disconnect → Hesabı deaktive et
GET  /api/dashboard/me           → Bağlı hesap + son yayınlar
"""
import logging
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse

from api.config import settings
from api.db import user_tokens

log = logging.getLogger(__name__)
router = APIRouter(tags=["TikTok Auth"])

_TT_AUTH_URL  = "https://www.tiktok.com/v2/auth/authorize/"
_TT_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
_TT_USER_URL  = "https://open.tiktokapis.com/v2/user/info/"


# ── 1. OAuth başlat ───────────────────────────────────────────────────────────

@router.get("/api/auth/tiktok")
async def tiktok_auth_start():
    """Kullanıcıyı TikTok yetkilendirme sayfasına yönlendir."""
    if not settings.tiktok_client_key:
        raise HTTPException(500, "TIKTOK_CLIENT_KEY ayarlanmamış.")

    url = (
        f"{_TT_AUTH_URL}"
        f"?client_key={settings.tiktok_client_key}"
        f"&response_type=code"
        f"&scope=user.info.basic,video.publish"
        f"&redirect_uri={settings.tiktok_redirect_uri}"
    )
    return RedirectResponse(url)


# ── 2. OAuth callback ─────────────────────────────────────────────────────────

@router.get("/api/auth/tiktok/callback")
async def tiktok_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    error: str = Query(default=""),
    error_description: str = Query(default=""),
):
    """TikTok'tan gelen code'u token ile değiştir."""
    if error:
        log.warning(f"TikTok OAuth hatası: {error} — {error_description}")
        return RedirectResponse(
            f"{settings.frontend_url}/callback.html"
            f"?error={error}&error_description={error_description}"
        )

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Code → token
        r = await client.post(
            _TT_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key":    settings.tiktok_client_key,
                "client_secret": settings.tiktok_client_secret,
                "code":          code,
                "grant_type":    "authorization_code",
                "redirect_uri":  settings.tiktok_redirect_uri,
            },
        )
        if r.is_error:
            log.error(f"Token değişimi başarısız: {r.status_code} {r.text}")
            return RedirectResponse(
                f"{settings.frontend_url}/callback.html?error=token_exchange_failed"
            )

        token_data   = r.json()
        access_token  = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires_in    = int(token_data.get("expires_in", 86400))
        open_id       = token_data.get("open_id", "")

        if not access_token or not open_id:
            log.error(f"Token yanıtı eksik: {token_data}")
            return RedirectResponse(
                f"{settings.frontend_url}/callback.html?error=invalid_token_response"
            )

        # 2. Kullanıcı adı al
        r2 = await client.get(
            _TT_USER_URL,
            params={"fields": "display_name,avatar_url"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        username = open_id
        if not r2.is_error:
            username = (
                r2.json()
                .get("data", {})
                .get("user", {})
                .get("display_name", open_id)
            )

    # 3. Supabase'e kaydet
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    try:
        user_tokens.upsert_account(open_id, username, access_token, refresh_token, expires_at)
    except Exception as e:
        log.error(f"Supabase kayıt hatası: {e}")
        return RedirectResponse(
            f"{settings.frontend_url}/callback.html?error=db_error"
        )

    log.info(f"Yeni hesap bağlandı: @{username}")
    return RedirectResponse(
        f"{settings.frontend_url}/dashboard.html?connected=1&user={username}"
    )


# ── 3. Disconnect ─────────────────────────────────────────────────────────────

@router.delete("/api/auth/tiktok/disconnect")
async def disconnect(open_id: str = Query(...)):
    """Hesabı deaktive et."""
    accounts = user_tokens.get_active_accounts()
    target = next((a for a in accounts if a["tiktok_open_id"] == open_id), None)
    if not target:
        raise HTTPException(404, "Hesap bulunamadı.")
    user_tokens.deactivate_account(target["id"])
    return {"status": "disconnected"}


# ── 4. Dashboard API ──────────────────────────────────────────────────────────

@router.get("/api/dashboard/me")
async def dashboard_me(open_id: str = Query(...)):
    """Hesap bilgisi + bağlı durum."""
    accounts = user_tokens.get_active_accounts()
    account = next((a for a in accounts if a["tiktok_open_id"] == open_id), None)
    if not account:
        raise HTTPException(404, "Aktif hesap bulunamadı.")
    return {
        "username":     account["tiktok_username"],
        "connected_at": account["connected_at"],
        "last_used_at": account.get("last_used_at"),
        "last_error":   account.get("last_error"),
    }


@router.get("/api/dashboard/stats")
async def dashboard_stats():
    """Toplam bağlı hesap sayısı (public)."""
    accounts = user_tokens.get_active_accounts()
    return {"connected_accounts": len(accounts)}
