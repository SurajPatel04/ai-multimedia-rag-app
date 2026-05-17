import pytest
import io
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.models.temp_data import TempData
from app.services.file_processor import generate_temp_id
from app.utils.file_upload_supabase import get_fresh_signed_url
from app.router.file_upload import process_file
from app.router.file_upload import save_file_locally
from fastapi import UploadFile, HTTPException
import os
from beanie import PydanticObjectId
import uuid
from app.models.user import User
from app.router.file_upload import process_and_upload


# shared helpers

def make_pdf_file(filename="test.pdf", size=1024):
    content = b"%PDF-1.4 fake pdf content " + b"x" * size
    return (filename, io.BytesIO(content), "application/pdf")


def make_audio_file(filename="test.mp3", size=1024):
    content = b"ID3 fake audio content " + b"x" * size
    return (filename, io.BytesIO(content), "audio/mpeg")


def _upload_file(content=b"dummy pdf", filename="test.pdf", content_type="application/pdf"):
    return ("files", (filename, io.BytesIO(content), content_type))


MOCK_SUPABASE_RESULT = {
    "file_path": "uuid-test.pdf",
    "signed_url": "https://supabase.co/signed/uuid-test.pdf"
}

MOCK_PROCESS_RESULT = {
    "file_type": "pdf",
    "full_text": "This is test content.",
    "utterances": [],
    "chunks": [
        {
            "chunk_index": 0,
            "text": "This is test content.",
            "metadata": {"page": 1, "total_pages": 1}
        }
    ]
}


# existing integration tests

async def test_upload_invalid_file_type(authenticated_client):
    res = await authenticated_client.post(
        "/api/v1/upload",
        files={"files": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    )
    assert res.status_code == 400
    assert "invalid file type" in str(res.json()).lower()


async def test_upload_pdf_success(authenticated_client):
    with patch(
        "app.router.file_upload.upload_file_to_supabase",
        new=AsyncMock(return_value=MOCK_SUPABASE_RESULT)
    ), patch(
        "app.router.file_upload.process_file",
        return_value=MOCK_PROCESS_RESULT
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files={"files": make_pdf_file()}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "temp_id" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["original_name"] == "test.pdf"

        await TempData.find({"temp_id": data["temp_id"]}).delete()


async def test_upload_audio_success(authenticated_client):
    with patch(
        "app.router.file_upload.upload_file_to_supabase",
        new=AsyncMock(return_value=MOCK_SUPABASE_RESULT)
    ), patch(
        "app.router.file_upload.process_file",
        return_value={**MOCK_PROCESS_RESULT, "file_type": "audio"}
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files={"files": make_audio_file()}
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

        await TempData.find({"temp_id": res.json()["temp_id"]}).delete()


async def test_upload_replace_files(authenticated_client):
    with patch(
        "app.router.file_upload.upload_file_to_supabase",
        new=AsyncMock(return_value=MOCK_SUPABASE_RESULT)
    ), patch(
        "app.router.file_upload.process_file",
        return_value=MOCK_PROCESS_RESULT
    ):
        res1 = await authenticated_client.post(
            "/api/v1/upload",
            files={"files": make_pdf_file("first.pdf")}
        )
        temp_id = res1.json()["temp_id"]

        res2 = await authenticated_client.post(
            "/api/v1/upload",
            files={"files": make_pdf_file("second.pdf")},
            data={"temp_id": temp_id}
        )
        assert res2.status_code == 200
        assert res2.json()["message"] == "Files replaced successfully"
        assert res2.json()["temp_id"] == temp_id
        assert res2.json()["data"][0]["original_name"] == "second.pdf"

        await TempData.find({"temp_id": temp_id}).delete()


async def test_upload_unauthenticated(client):
    res = await client.post(
        "/api/v1/upload",
        files={"files": make_pdf_file()}
    )
    assert res.status_code == 401


async def test_upload_multiple_files(authenticated_client):
    with patch(
        "app.router.file_upload.upload_file_to_supabase",
        new=AsyncMock(return_value=MOCK_SUPABASE_RESULT)
    ), patch(
        "app.router.file_upload.process_file",
        return_value=MOCK_PROCESS_RESULT
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[
                ("files", make_pdf_file("file1.pdf")),
                ("files", make_pdf_file("file2.pdf")),
            ]
        )
        assert res.status_code == 200
        assert len(res.json()["data"]) == 2

        await TempData.find({"temp_id": res.json()["temp_id"]}).delete()


async def test_save_file_locally():
    content = b"fake pdf content"
    upload_file = UploadFile(
        filename="test.pdf",
        file=io.BytesIO(content),
        headers={"content-type": "application/pdf"}
    )

    result = await save_file_locally(upload_file)

    assert result["original_name"] == "test.pdf"
    assert result["content_type"] == "application/pdf"
    assert os.path.exists(result["path"])

    os.remove(result["path"])


def test_generate_temp_id():
    id1 = generate_temp_id()
    id2 = generate_temp_id()

    assert id1.startswith("tmp_")
    assert id1 != id2
    assert len(id1) > 8


async def test_get_fresh_signed_url_with_full_url():
    full_url = "https://example.supabase.co/storage/v1/object/public/documents/file.pdf"
    result = await get_fresh_signed_url(full_url)
    assert result == full_url


async def test_get_fresh_signed_url_with_file_path():
    with patch(
        "app.utils.file_upload_supabase.get_async_supabase",
        new=AsyncMock(return_value=AsyncMock(
            storage=MagicMock(
                from_=MagicMock(return_value=MagicMock(
                    create_signed_url=AsyncMock(
                        return_value={"signedURL": "https://signed.url/file.pdf"}
                    )
                ))
            )
        ))
    ):
        result = await get_fresh_signed_url("uuid-file.pdf")
        assert result == "https://signed.url/file.pdf"


async def test_upload_internal_server_error(authenticated_client):
    with patch("app.router.file_upload.process_file", side_effect=Exception("Disk Full!")):
        files = {"files": ("test.pdf", b"abc", "application/pdf")}
        res = await authenticated_client.post("/api/v1/upload", files=files)

        assert res.status_code == 500
        assert "Disk Full!" in res.text


async def test_cancel_file_success(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})

    temp_id = "test_cancel_temp_001"
    file_id = f"file_{uuid.uuid4().hex}"

    await TempData(
        temp_id=temp_id,
        file_id=file_id,
        user_id=user.id,
        file_url="http://example.com/test.pdf",
        file_name="test.pdf",
        file_type="pdf",
        content_type="application/pdf",
        full_text="Test content",
        chunks=[],
        embedded=False,
        status="ready"
    ).insert()

    res = await authenticated_client.delete(f"/api/v1/upload/cancel/{temp_id}/{file_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["message"] == "File cancelled successfully"

    doc = await TempData.find_one(TempData.temp_id == temp_id, TempData.file_id == file_id)
    assert doc is None


async def test_cancel_file_not_found(authenticated_client):
    res = await authenticated_client.delete("/api/v1/upload/cancel/fake_temp_id/fake_file_id")
    assert res.status_code == 404
    assert "File not found" in res.text


async def test_cancel_file_unauthenticated(client):
    res = await client.delete("/api/v1/upload/cancel/some_temp_id/some_file_id")
    assert res.status_code == 401


async def test_cancel_file_wrong_user(authenticated_client):
    temp_id = "test_cancel_wrong_user_001"
    file_id = f"file_{uuid.uuid4().hex}"
    other_user_id = PydanticObjectId()

    await TempData(
        temp_id=temp_id,
        file_id=file_id,
        user_id=other_user_id,
        file_url="http://example.com/test.pdf",
        file_name="test.pdf",
        file_type="pdf",
        content_type="application/pdf",
        full_text="Test content",
        chunks=[],
        embedded=False,
        status="ready"
    ).insert()

    res = await authenticated_client.delete(f"/api/v1/upload/cancel/{temp_id}/{file_id}")
    assert res.status_code == 404

    await TempData.find(TempData.temp_id == temp_id).delete()


async def test_cancel_file_wrong_file_id(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})

    temp_id = "test_cancel_wrong_file_001"
    file_id = f"file_{uuid.uuid4().hex}"

    await TempData(
        temp_id=temp_id,
        file_id=file_id,
        user_id=user.id,
        file_url="http://example.com/test.pdf",
        file_name="test.pdf",
        file_type="pdf",
        content_type="application/pdf",
        full_text="Test content",
        chunks=[],
        embedded=False,
        status="ready"
    ).insert()

    res = await authenticated_client.delete(f"/api/v1/upload/cancel/{temp_id}/file_wrongid123")
    assert res.status_code == 404

    await TempData.find(TempData.temp_id == temp_id).delete()


async def test_cancel_file_does_not_delete_other_files(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})

    temp_id = "test_cancel_multi_001"
    file_id_1 = f"file_{uuid.uuid4().hex}"
    file_id_2 = f"file_{uuid.uuid4().hex}"

    for fid, fname in [(file_id_1, "file1.pdf"), (file_id_2, "file2.pdf")]:
        await TempData(
            temp_id=temp_id,
            file_id=fid,
            user_id=user.id,
            file_url=f"http://example.com/{fname}",
            file_name=fname,
            file_type="pdf",
            content_type="application/pdf",
            chunks=[],
            embedded=False,
            status="ready"
        ).insert()

    res = await authenticated_client.delete(f"/api/v1/upload/cancel/{temp_id}/{file_id_1}")
    assert res.status_code == 200

    doc1 = await TempData.find_one(TempData.file_id == file_id_1)
    doc2 = await TempData.find_one(TempData.file_id == file_id_2)
    assert doc1 is None
    assert doc2 is not None

    await TempData.find(TempData.temp_id == temp_id).delete()

async def test_save_file_locally_exceeds_size_limit(tmp_path):
    one_mb = b"x" * (1024 * 1024)
    call_count = 0

    async def big_read(_size):
        nonlocal call_count
        call_count += 1
        return one_mb if call_count <= 51 else b""

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "huge.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.read = big_read
    mock_file.close = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await save_file_locally(mock_file)

    assert exc_info.value.status_code == 400
    assert "exceeds" in exc_info.value.detail

async def test_upload_file_exceeds_size_limit_via_router(authenticated_client):
    with patch(
        "app.router.file_upload.save_file_locally",
        side_effect=HTTPException(status_code=400, detail="big.pdf exceeds 100MB limit"),
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
        )

    assert res.status_code == 400
    assert "exceeds" in res.text.lower()

async def test_upload_disconnected_before_upload_task(authenticated_client):
    with (
        patch("app.router.file_upload.upload_file_to_supabase", new_callable=AsyncMock),
        patch("app.router.file_upload.process_file", return_value=MOCK_PROCESS_RESULT),
        patch("app.router.file_upload.generate_temp_id", return_value="tid-dc-before"),
        patch(
            "starlette.requests.Request.is_disconnected",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("os.path.exists", return_value=False),
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
        )
    assert res.status_code in (200, 499)

async def test_upload_disconnected_during_upload_task(authenticated_client):
    call_n = 0

    async def third_true():
        nonlocal call_n
        call_n += 1
        return call_n == 3

    slow_task = MagicMock()
    slow_task.done.return_value = False
    slow_task.cancel = MagicMock()

    with (
        patch("asyncio.create_task", return_value=slow_task),
        patch("app.router.file_upload.generate_temp_id", return_value="tid-dc-during"),
        patch("app.router.file_upload.TempData"),
        patch("os.path.exists", return_value=False),
        patch("starlette.requests.Request.is_disconnected", side_effect=third_true),
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
        )

    assert res.status_code == 200
    assert res.json()["data"] == []
    slow_task.cancel.assert_called_once()

async def test_upload_disconnected_before_processing():
    call_n = 0
    async def second_true():
        nonlocal call_n
        call_n += 1
        return call_n >= 2

    mock_request = MagicMock()
    mock_request.is_disconnected = second_true

    saved = {"original_name": "t.pdf", "saved_name": "u.pdf", "path": "/tmp/fake_dc.pdf"}
    mock_file = MagicMock()
    mock_file.filename = "t.pdf"

    with (
        patch(
            "app.router.file_upload.upload_file_to_supabase",
            new_callable=AsyncMock,
            return_value={"file_path": "docs/f.pdf", "signed_url": "https://x"},
        ),
        patch("os.path.exists", return_value=False),
    ):
        result = await process_and_upload(
            "tid-before-proc", saved, mock_file, "fake-user-id", mock_request
        )

    assert result is None

async def test_upload_disconnected_during_processing(authenticated_client):
    call_n = 0

    async def fourth_true():
        nonlocal call_n
        call_n += 1
        return call_n == 4

    with (
        patch(
            "app.router.file_upload.upload_file_to_supabase",
            new_callable=AsyncMock,
            return_value={"file_path": "docs/f.pdf", "signed_url": "https://x"},
        ),
        patch("app.router.file_upload.process_file", return_value=MOCK_PROCESS_RESULT),
        patch("app.router.file_upload.generate_temp_id", return_value="tid-dc-during-proc"),
        patch("app.router.file_upload.TempData"),
        patch("os.path.exists", return_value=False),
        patch("starlette.requests.Request.is_disconnected", side_effect=fourth_true),
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
        )

    assert res.status_code == 200
    assert res.json()["data"] == []

async def test_upload_disconnected_before_db_insert(authenticated_client):
    call_n = 0

    async def fifth_true():
        nonlocal call_n
        call_n += 1
        return call_n == 5

    with (
        patch(
            "app.router.file_upload.upload_file_to_supabase",
            new_callable=AsyncMock,
            return_value={"file_path": "docs/f.pdf", "signed_url": "https://x"},
        ),
        patch("app.router.file_upload.process_file", return_value=MOCK_PROCESS_RESULT),
        patch("app.router.file_upload.generate_temp_id", return_value="tid-dc-before-db"),
        patch("app.router.file_upload.TempData"),
        patch("os.path.exists", return_value=False),
        patch("starlette.requests.Request.is_disconnected", side_effect=fifth_true),
    ):
        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
        )

    assert res.status_code == 200
    assert res.json()["data"] == []

async def test_upload_replacement_branch_disconnected(authenticated_client):
    with (
        patch("app.router.file_upload.TempData") as MockTD,
        patch(
            "starlette.requests.Request.is_disconnected",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        MockTD.find.return_value.delete = AsyncMock()

        res = await authenticated_client.post(
            "/api/v1/upload",
            files=[_upload_file()],
            data={"temp_id": "existing-tid-replace"},
        )

    assert res.status_code in (200, 499)
    if res.status_code == 200:
        assert res.json()["data"] == []

async def test_upload_cancelled_error_is_reraised():
    from app.router.file_upload import upload_files

    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "application/pdf"
    mock_file.filename = "t.pdf"

    with (
        patch("app.router.file_upload.save_file_locally", side_effect=asyncio.CancelledError),
        patch("app.router.file_upload.generate_temp_id", return_value="tid-cancel"),
    ):
        with pytest.raises(asyncio.CancelledError):   # must NOT be swallowed as 500
            await upload_files(
                request=mock_request,
                files=[mock_file],
                temp_id=None,
                changed_files=None,
                user="fake-user-id",
            )

async def test_process_and_upload_disconnected_before_upload():
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=True)

    saved = {"original_name": "t.pdf", "saved_name": "u.pdf", "path": "/tmp/fake_dc.pdf"}
    mock_file = MagicMock()
    mock_file.filename = "t.pdf"

    with patch("os.path.exists", return_value=False):
        result = await process_and_upload(
            "tid-before-up", saved, mock_file, "fake-user-id", mock_request
        )

    assert result is None

async def test_process_and_upload_disconnected_before_db_insert():
    call_n = 0
    async def true_before_db():
        nonlocal call_n
        call_n += 1
        return call_n >= 5

    mock_request = MagicMock()
    mock_request.is_disconnected = true_before_db

    saved = {"original_name": "t.pdf", "saved_name": "u.pdf", "path": "/tmp/fake_dc.pdf"}
    mock_file = MagicMock()
    mock_file.filename = "t.pdf"

    with (
        patch(
            "app.router.file_upload.upload_file_to_supabase",
            new_callable=AsyncMock,
            return_value={"file_path": "docs/f.pdf", "signed_url": "https://x"},
        ),
        patch("app.router.file_upload.process_file", return_value=MOCK_PROCESS_RESULT),
        patch("os.path.exists", return_value=False),
    ):
        result = await process_and_upload(
            "tid-before-db", saved, mock_file, "fake-user-id", mock_request
        )

    assert result is None