import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form, Request
from typing import List, Optional
from app.dependencies.auth import get_current_user
from app.utils.file_upload_supabase import upload_file_to_supabase
from app.services.file_processor import process_file, generate_temp_id
from app.models.temp_data import TempData
from beanie import PydanticObjectId
import uuid
import os

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = [
    "application/pdf",
    "audio/mpeg",
    "audio/mp3",
    "video/mp4",
    "audio/wav"
]

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


async def save_file_locally(file: UploadFile) -> dict:
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    size = 0

    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
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


async def process_and_upload(temp_id: str, saved: dict, file: UploadFile, user, request: Request):
    loop = asyncio.get_event_loop()

    try:
        if await request.is_disconnected():
            print(f"[CANCELLED] Before upload: {saved['original_name']}")
            return None
        upload_task = asyncio.create_task(upload_file_to_supabase(saved["path"]))

        while not upload_task.done():
            if await request.is_disconnected():
                upload_task.cancel()
                print(f"[CANCELLED] During upload: {saved['original_name']}")
                return None
            await asyncio.sleep(0.5)

        supabase_data = await upload_task

        if await request.is_disconnected():
            print(f"[CANCELLED] Before processing: {saved['original_name']}")
            return None

        process_task = loop.run_in_executor(None, process_file, temp_id, saved["path"])

        while not process_task.done():
            if await request.is_disconnected():
                print(f"[CANCELLED] During processing: {saved['original_name']}")
                return None
            await asyncio.sleep(0.5)

        result = await process_task

        if await request.is_disconnected():
            print(f"[CANCELLED] Before DB insert: {saved['original_name']}")
            return None

        temp_doc = TempData(
            temp_id=temp_id,
            file_id=f"file_{uuid.uuid4().hex}",
            user_id=user,
            file_url=supabase_data["file_path"],
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

        return {
            "file_id": temp_doc.file_id,
            "original_name": file.filename,
            "saved_name": saved["saved_name"],
            "content_type": file.content_type,
        }

    finally:
        if os.path.exists(saved["path"]):
            os.remove(saved["path"])


@router.post("")
async def upload_files(
    request: Request,
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

            saved_files = []
            for file in files:
                if await request.is_disconnected():
                    raise HTTPException(status_code=499, detail="Client disconnected")
                saved = await save_file_locally(file)
                saved_files.append((file, saved))

            results = await asyncio.gather(*[
                process_and_upload(new_temp_id, saved, file, user, request)
                for file, saved in saved_files
            ])

            successful = [r for r in results if r is not None]

            return {
                "success": True,
                "message": "Files uploaded successfully",
                "temp_id": new_temp_id,
                "data": successful
            }

        else:
            await TempData.find(TempData.temp_id == temp_id).delete()

            saved_files = []
            for file in files:
                if await request.is_disconnected():
                    raise HTTPException(status_code=499, detail="Client disconnected")
                saved = await save_file_locally(file)
                saved_files.append((file, saved))

            results = await asyncio.gather(*[
                process_and_upload(temp_id, saved, file, user, request)
                for file, saved in saved_files
            ])

            successful = [r for r in results if r is not None]

            return {
                "success": True,
                "message": "Files replaced successfully",
                "temp_id": temp_id,
                "data": successful
            }

    except HTTPException:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/cancel/{temp_id}/{file_id}")
async def cancel_file(
    temp_id: str,
    file_id: str,
    user=Depends(get_current_user)
):
    temp_file = await TempData.find_one(
        TempData.temp_id == temp_id,
        TempData.file_id == file_id,
        TempData.user_id == PydanticObjectId(user)
    )

    if not temp_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # delete db document
    await temp_file.delete()

    return {
        "success": True,
        "message": "File cancelled successfully"
    }