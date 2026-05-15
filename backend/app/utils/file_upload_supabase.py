import os
import uuid
import mimetypes
from supabase._async.client import AsyncClient, create_client as async_create_client

from app.core.config import settings

_async_supabase: AsyncClient | None = None

async def get_async_supabase() -> AsyncClient:
    global _async_supabase
    if _async_supabase is None:
        _async_supabase = await async_create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _async_supabase


async def upload_file_to_supabase(file_path: str, bucket_name: str = "documents"):
    client = await get_async_supabase()

    file_name = os.path.basename(file_path)
    unique_filename = f"{uuid.uuid4()}-{file_name}"
    content_type, _ = mimetypes.guess_type(file_path)

    with open(file_path, "rb") as file:
        await client.storage \
            .from_(bucket_name) \
            .upload(
                path=unique_filename,
                file=file,
                file_options={
                    "content-type": (
                        content_type
                        or "application/octet-stream"
                    )
                }
            )

    signed_url_response = await client.storage \
        .from_(bucket_name) \
        .create_signed_url(unique_filename, expires_in=7200)

    return {
        "file_path": unique_filename,
        "signed_url": signed_url_response["signedURL"],
    }


async def get_fresh_signed_url(file_path: str, bucket_name: str = "documents"):
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return file_path

    client = await get_async_supabase()
    response = await client.storage \
        .from_(bucket_name) \
        .create_signed_url(file_path, expires_in=7200)
    return response["signedURL"]