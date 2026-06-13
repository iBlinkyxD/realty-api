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


def _normalise_ext(content_type: str) -> str:
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    if ext in (".jpe", ".jpeg"):
        ext = ".jpg"
    return ext


def upload_image(file_bytes: bytes, content_type: str, user_id: str) -> str:
    """Upload a listing image to Supabase Storage and return its public URL."""
    path = f"{user_id}/{uuid.uuid4()}{_normalise_ext(content_type)}"
    client = _get_client()
    client.storage.from_(settings.storage_bucket).upload(
        path,
        file_bytes,
        {"content-type": content_type, "upsert": "false"},
    )
    return client.storage.from_(settings.storage_bucket).get_public_url(path)


def _extract_storage_path(url: str, bucket: str) -> str | None:
    marker = f"/object/public/{bucket}/"
    idx = url.find(marker)
    return url[idx + len(marker):] if idx != -1 else None


def upload_avatar(file_bytes: bytes, content_type: str, user_id: str, old_url: str | None = None) -> str:
    """Upload a user avatar to Supabase Storage and return its public URL.
    Deletes the previous avatar if old_url is provided."""
    path = f"avatars/{user_id}/{uuid.uuid4()}{_normalise_ext(content_type)}"
    client = _get_client()
    client.storage.from_(settings.storage_bucket).upload(
        path,
        file_bytes,
        {"content-type": content_type, "upsert": "false"},
    )
    new_url = client.storage.from_(settings.storage_bucket).get_public_url(path)
    if old_url:
        old_path = _extract_storage_path(old_url, settings.storage_bucket)
        if old_path:
            try:
                client.storage.from_(settings.storage_bucket).remove([old_path])
            except Exception:
                pass
    return new_url
