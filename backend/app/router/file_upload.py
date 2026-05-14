from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form
from typing import List, Optional
from app.dependencies.auth import get_current_user
from app.utils.file_upload_supabase import upload_file_to_supabase
from app.utils.video_to_audio_converter import VIDEO_EXTENSIONS
from app.services.file_processor import process_file, replace_file, generate_temp_id
from app.models.temp_data import TempData
import shutil
import uuid
import os

router = APIRouter(
    prefix="/upload",
    tags=["upload"]
)

UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = [
    "application/pdf",
    "audio/mpeg",
    "audio/mp3",
    "video/mp4",
    "audio/wav"
]

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


async def save_file_locally(file: UploadFile) -> dict:

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    size = 0

    with open(file_path, "wb") as buffer:

        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)

            if size > MAX_FILE_SIZE:
                buffer.close()
                os.remove(file_path)

                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} exceeds 100MB limit"
                )

            buffer.write(chunk)

    await file.close()

    return {
        "original_name": file.filename,
        "saved_name": unique_filename,
        "content_type": file.content_type,
        "path": file_path
    }

@router.post("")
async def upload_files(
    files: List[UploadFile] = File(...),
    temp_id: Optional[str] = Form(None),     
    changed_files: Optional[str] = Form(None), 
    user=Depends(get_current_user)
):
    try:
        for file in files:
            if file.content_type not in ALLOWED_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} has invalid file type"
                )
        if not temp_id:
            new_temp_id = generate_temp_id()
            uploaded_files = []

            for file in files:
                saved = await save_file_locally(file)

                try:
                    supabase_data = upload_file_to_supabase(saved["path"])
                    result = process_file(new_temp_id, saved["path"])

                    temp_doc = TempData(
                        temp_id=new_temp_id,
                        user_id=user,
                        file_url=supabase_data["public_url"],
                        file_name=file.filename,
                        file_type=result["file_type"],
                        content_type=file.content_type,
                        full_text=result.get("full_text", ""),
                        utterances=result.get("utterances", []),
                        chunks=result["chunks"],
                        embedded=False,
                        status="ready"
                    )
                    await temp_doc.insert()

                    uploaded_files.append({
                        "original_name": file.filename,
                        "saved_name": saved["saved_name"],
                        "content_type": file.content_type,
                    })
                finally:
                    if os.path.exists(saved["path"]):
                        os.remove(saved["path"])

            return {
                "success": True,
                "message": "Files uploaded successfully",
                "temp_id": new_temp_id,
                "data": uploaded_files
            }


        else:
            deleted = await TempData.find(
                TempData.temp_id == temp_id
            ).delete()

            # print("Deleted old docs:", deleted)

            replaced_files = []

            for file in files:

                saved = await save_file_locally(file)

                try:
                    supabase_data = upload_file_to_supabase(saved["path"])
                    result = process_file(temp_id, saved["path"])
                    temp_doc = TempData(
                        temp_id=temp_id,
                        user_id=user,
                        file_url=supabase_data["public_url"],
                        file_name=file.filename,
                        file_type=result["file_type"],
                        content_type=file.content_type,
                        full_text=result.get("full_text", ""),
                        utterances=result.get("utterances", []),
                        chunks=result["chunks"],
                        embedded=False,
                        status="ready"
                    )

                    await temp_doc.insert()

                    replaced_files.append({
                        "original_name": file.filename,
                        "saved_name": saved["saved_name"],
                        "content_type": file.content_type,
                    })

                finally:
                    if os.path.exists(saved["path"]):
                        os.remove(saved["path"])
            return {
                "success": True,
                "message": "Files replaced successfully",
                "temp_id": temp_id,
                "data": replaced_files
            }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )