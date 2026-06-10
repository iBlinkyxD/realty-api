import uuid
import mimetypes
from supabase import create_client, Client
from config import settings

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def upload_image(file_bytes: bytes, content_type: str, user_id: str) -> str:
    """Upload a single image to Supabase Storage and return its public URL."""
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    # guess_extension can return .jpe for jpeg; normalise
    if ext in (".jpe", ".jpeg"):
        ext = ".jpg"
    path = f"{user_id}/{uuid.uuid4()}{ext}"

    client = _get_client()
    client.storage.from_(settings.storage_bucket).upload(
        path,
        file_bytes,
        {"content-type": content_type, "upsert": "false"},
    )
    return client.storage.from_(settings.storage_bucket).get_public_url(path)
