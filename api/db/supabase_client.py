"""
Supabase istemcisi — singleton pattern.
"""
from supabase import create_client, Client
from api.config import settings

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "SUPABASE_URL veya SUPABASE_SERVICE_KEY eksik. "
                ".env dosyasına veya GitHub Secrets'a ekle."
            )
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client
