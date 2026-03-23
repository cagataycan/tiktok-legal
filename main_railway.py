"""
Railway deployment entry point — TikTok + Twitter OAuth servisi.
Ana pipeline (yt-dlp, whisper, FFmpeg) burada yok.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
def root():
    return {"service": "PhiloShorts OAuth", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
