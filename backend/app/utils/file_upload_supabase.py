import os
import uuid
import mimetypes

from supabase import create_client


supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def upload_file_to_supabase(file_path: str, bucket_name: str = "documents"):

    file_name = os.path.basename(file_path)

    unique_filename = (
        f"{uuid.uuid4()}-{file_name}"
    )

    content_type, _ = mimetypes.guess_type(file_path)

    with open(file_path, "rb") as file:

        supabase.storage \
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

    public_url = supabase.storage \
        .from_(bucket_name) \
        .get_public_url(unique_filename)

    return {
        "file_path": unique_filename,
        "public_url": public_url
    }