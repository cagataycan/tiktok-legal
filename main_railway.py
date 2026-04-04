"""
Railway deployment entry point — TikTok + Twitter OAuth servisi.
Ana pipeline (yt-dlp, whisper, FFmpeg) burada yok.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers.auth_tiktok import router as tiktok_router
from api.routers.auth_twitter import router as twitter_router

app = FastAPI(
    title="PhiloShorts OAuth Service",
    description="TikTok + Twitter OAuth 2.0 + token yönetimi",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tiktok_router)
app.include_router(twitter_router)

# Static HTML dosyaları (terms, privacy, callback, dashboard)
_BASE = Path(__file__).parent


@app.get("/")
def root():
    index = _BASE / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"service": "PhiloShorts OAuth", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/terms.html")
def terms():
    return FileResponse(_BASE / "terms.html")


@app.get("/privacy.html")
def privacy():
    return FileResponse(_BASE / "privacy.html")


@app.get("/callback.html")
def callback():
    return FileResponse(_BASE / "callback.html")


@app.get("/dashboard.html")
def dashboard():
    return FileResponse(_BASE / "dashboard.html")
