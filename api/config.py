from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API Keys
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""   # GitHub Actions: Secret olarak set et
    anthropic_api_key: str = ""
    pexels_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "onwK4e9ZLuTAKqWW03F9"  # Daniel - derin, otoriter
    openai_api_key: str = ""
    openai_tts_voice: str = "onyx"  # onyx: derin erkek sesi
    jamendo_client_id: str = ""
    instagram_user_id: str = ""
    instagram_access_token: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    tiktok_access_token: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_refresh_token: str = ""
    tiktok_redirect_uri: str = ""   # Örn: https://your-backend.railway.app/api/auth/tiktok/callback

    # Twitter/X
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    twitter_redirect_uri: str = ""  # Örn: https://your-backend.railway.app/api/auth/twitter/callback

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Frontend URL (OAuth sonrası yönlendirme)
    frontend_url: str = "https://cagataycan.github.io/tiktok-legal"

    # Storage
    storage_dir: str = "storage"
    downloads_dir: str = "storage/downloads"
    processed_dir: str = "storage/processed"
    tokens_dir: str = "storage/tokens"

    # İşlem limitleri
    min_view_count: int = 100000
    max_duration_seconds: int = 1200  # 20 dakika

    # FFmpeg tam yolu (PATH'te yoksa .env ile override et)
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def ensure_dirs(self):
        for d in [self.downloads_dir, self.processed_dir, self.tokens_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
