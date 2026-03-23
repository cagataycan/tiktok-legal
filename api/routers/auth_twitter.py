"""
Twitter/X OAuth 2.0 Router (PKCE)
===================================
GET  /api/auth/twitter            → Twitter yetkilendirme sayfasına yönlendir
GET  /api/auth/twitter/callback   → Code → token, Supabase'e kaydet
DELETE /api/auth/twitter/disconnect → Hesabı deaktive et
"""
import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from api.config import settings
from api.db import twitter_tokens as tt

log = logging.getLogger(__name__)
router = APIRouter(tags=["Twitter Auth"])

_AUTH_URL  = "https://twitter.com/i/oauth2/authorize"
_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
_USER_URL  = "https://api.twitter.com/2/users/me"
_SCOPES    = "tweet.read tweet.write users.read offline.access"

# PKCE state dosyası (tek kullanıcı — lokal geliştirme yeterli)
_PKCE_PATH = Path(settings.tokens_dir) / "twitter_pkce.json"


def _pkce_pair() -> tuple[str, str]:
    """code_verifier + code_challenge (S256) üretir."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ── OAuth başlat ──────────────────────────────────────────────────────────────

@router.get("/api/auth/twitter")
async def twitter_auth_start():
    if not settings.twitter_client_id:
        raise HTTPException(500, "TWITTER_CLIENT_ID ayarlanmamış.")

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    _PKCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PKCE_PATH.write_text(
        json.dumps({"verifier": verifier, "state": state}), encoding="utf-8"
    )

    url = (
        f"{_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={settings.twitter_client_id}"
        f"&redirect_uri={settings.twitter_redirect_uri}"
        f"&scope={_SCOPES.replace(' ', '%20')}"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(url)


# ── OAuth callback ─────────────────────────────────────────────────────────────

@router.get("/api/auth/twitter/callback")
async def twitter_callback(
    code:  str = Query(...),
    state: str = Query(default=""),
    error: str = Query(default=""),
):
    if error:
        log.warning(f"Twitter OAuth hatası: {error}")
        return RedirectResponse(f"{settings.frontend_url}/callback.html?error={error}&platform=twitter")

    # PKCE verifier'ı oku
    verifier = ""
    if _PKCE_PATH.exists():
        pkce = json.loads(_PKCE_PATH.read_text(encoding="utf-8"))
        verifier = pkce.get("verifier", "")
        _PKCE_PATH.unlink(missing_ok=True)

    # Basic Auth header
    creds = f"{settings.twitter_client_id}:{settings.twitter_client_secret}"
    basic = base64.b64encode(creds.encode()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            _TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  settings.twitter_redirect_uri,
                "code_verifier": verifier,
            },
        )
        if r.is_error:
            log.error(f"Twitter token değişimi başarısız: {r.status_code} {r.text}")
            return RedirectResponse(
                f"{settings.frontend_url}/callback.html?error=token_exchange_failed&platform=twitter"
            )

        token_data    = r.json()
        access_token  = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires_in    = int(token_data.get("expires_in", 7200))

        if not access_token:
            return RedirectResponse(
                f"{settings.frontend_url}/callback.html?error=invalid_token_response&platform=twitter"
            )

        # Kullanıcı bilgisi
        r2 = await client.get(
            _USER_URL,
            params={"user.fields": "name,username"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r2.is_error:
            log.error(f"Twitter kullanıcı bilgisi alınamadı: {r2.status_code}")
            return RedirectResponse(
                f"{settings.frontend_url}/callback.html?error=user_info_failed&platform=twitter"
            )

        user_data = r2.json().get("data", {})
        user_id   = user_data.get("id", "")
        username  = user_data.get("username", user_id)

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

    try:
        tt.upsert_account(user_id, username, access_token, refresh_token, expires_at)
    except Exception as e:
        log.error(f"Supabase Twitter kayıt hatası: {e}")
        return RedirectResponse(
            f"{settings.frontend_url}/callback.html?error=db_error&platform=twitter"
        )

    log.info(f"Twitter hesap bağlandı: @{username}")
    return RedirectResponse(
        f"{settings.frontend_url}/dashboard.html?connected=1&user={username}&platform=twitter"
    )


# ── Disconnect ────────────────────────────────────────────────────────────────

@router.delete("/api/auth/twitter/disconnect")
async def disconnect(user_id: str = Query(...)):
    accounts = tt.get_active_accounts()
    target = next((a for a in accounts if a["twitter_user_id"] == user_id), None)
    if not target:
        raise HTTPException(404, "Hesap bulunamadı.")
    tt.deactivate_account(target["id"])
    return {"status": "disconnected"}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/api/dashboard/twitter/stats")
async def twitter_stats():
    accounts = tt.get_active_accounts()
    return {"connected_accounts": len(accounts)}
