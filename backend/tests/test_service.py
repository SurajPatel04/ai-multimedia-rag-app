import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from beanie import PydanticObjectId
from uuid import UUID

from app.services.auth_service import create_access_token, ACCESS_TOKEN_SECRET_KEY, ACCESS_TOKEN_ALGORITHM, create_refresh_token, REFRESH_TOKEN_SECRET_KEY, REFRESH_TOKEN_ALGORITHM, create_both_tokens
from jose import jwt
from app.services.auth_service import create_both_tokens
from app.services.file_processor import generate_temp_id
from app.services.file_processor import process_file
from app.services.file_processor import _process_pdf_file
from app.services.file_processor import _process_audio_video_file
from app.services.file_processor import embed_and_store
from app.services.file_processor import replace_file
from app.services.llm_response_stream import stream_response

@pytest.mark.asyncio
async def test_create_access_token_returns_string():
    token = await create_access_token({"sub": "user123"})
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_create_access_token_payload_decodable():
    token = await create_access_token({"sub": "abc123"})
    payload = jwt.decode(token, ACCESS_TOKEN_SECRET_KEY, algorithms=[ACCESS_TOKEN_ALGORITHM])
    assert payload["sub"] == "abc123"


@pytest.mark.asyncio
async def test_create_access_token_has_expiry():
    token = await create_access_token({"sub": "user1"})
    payload = jwt.decode(token, ACCESS_TOKEN_SECRET_KEY, algorithms=[ACCESS_TOKEN_ALGORITHM])
    assert "exp" in payload

@pytest.mark.asyncio
async def test_create_refresh_token_returns_string():
    token = await create_refresh_token({"sub": "user123", "jti": "some-jti"})
    assert isinstance(token, str)


@pytest.mark.asyncio
async def test_create_refresh_token_payload_decodable():
    token = await create_refresh_token({"sub": "user1", "jti": "test-jti"})
    payload = jwt.decode(token, REFRESH_TOKEN_SECRET_KEY, algorithms=[REFRESH_TOKEN_ALGORITHM])
    assert payload["sub"] == "user1"
    assert payload["jti"] == "test-jti"


@pytest.mark.asyncio
async def test_create_refresh_token_longer_ttl_than_access():
    access  = await create_access_token({"sub": "u"})
    refresh = await create_refresh_token({"sub": "u", "jti": "j"})

    access_exp  = jwt.decode(access,  ACCESS_TOKEN_SECRET_KEY,  algorithms=[ACCESS_TOKEN_ALGORITHM])["exp"]
    refresh_exp = jwt.decode(refresh, REFRESH_TOKEN_SECRET_KEY, algorithms=[REFRESH_TOKEN_ALGORITHM])["exp"]

    assert refresh_exp > access_exp


@pytest.mark.asyncio
async def test_create_both_tokens_returns_both():
    user_id = PydanticObjectId()

    mock_doc = AsyncMock()
    with patch("app.services.auth_service.RefreshToken") as MockRefreshToken:
        MockRefreshToken.return_value = mock_doc
        mock_doc.insert = AsyncMock()
        result = await create_both_tokens(user_id)

    assert "access_token"  in result
    assert "refresh_token" in result
    assert isinstance(result["access_token"],  str)
    assert isinstance(result["refresh_token"], str)


@pytest.mark.asyncio
async def test_create_both_tokens_persists_refresh_doc():
    user_id = PydanticObjectId()

    mock_doc = AsyncMock()
    with patch("app.services.auth_service.RefreshToken") as MockRefreshToken:
        MockRefreshToken.return_value = mock_doc
        mock_doc.insert = AsyncMock()
        await create_both_tokens(user_id)

    mock_doc.insert.assert_called_once()


@pytest.mark.asyncio
async def test_create_both_tokens_hashes_refresh_token():
    user_id = PydanticObjectId()
    stored_hash = None

    def capture_init(**kwargs):
        nonlocal stored_hash
        stored_hash = kwargs.get("token_hash")
        doc = AsyncMock()
        doc.insert = AsyncMock()
        return doc

    with patch("app.services.auth_service.RefreshToken", side_effect=capture_init):
        result = await create_both_tokens(user_id)

    assert stored_hash != result["refresh_token"]


@pytest.mark.asyncio
async def test_create_both_tokens_unique_jti_each_call():
    user_id = PydanticObjectId()
    jtis = []

    def capture_init(**kwargs):
        jtis.append(kwargs.get("jti"))
        doc = AsyncMock()
        doc.insert = AsyncMock()
        return doc

    with patch("app.services.auth_service.RefreshToken", side_effect=capture_init):
        await create_both_tokens(user_id)
        await create_both_tokens(user_id)

    assert jtis[0] != jtis[1]

def test_generate_temp_id_format():
    tid = generate_temp_id()
    assert tid.startswith("tmp_")
    assert len(tid) > 4


def test_generate_temp_id_unique():
    assert generate_temp_id() != generate_temp_id()


def test_process_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="File not found"):
        process_file("tmp_abc", "/nonexistent/path/file.pdf")


def test_process_file_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_text("dummy")
    with pytest.raises(ValueError, match="Unsupported file type"):
        process_file("tmp_abc", str(f))


def test_process_file_routes_pdf(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"dummy pdf")

    with patch("app.services.file_processor._process_pdf_file", return_value={"file_type": "pdf"}) as mock_pdf:
        result = process_file("tmp_1", str(f))

    mock_pdf.assert_called_once_with("tmp_1", str(f))
    assert result["file_type"] == "pdf"


def test_process_file_routes_audio(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"dummy mp3")

    with patch("app.services.file_processor._process_audio_video_file", return_value={"file_type": "audio"}) as mock_av:
        result = process_file("tmp_2", str(f))

    mock_av.assert_called_once_with("tmp_2", str(f))
    assert result["file_type"] == "audio"


def test_process_file_routes_video(tmp_path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"dummy mp4")

    with patch("app.services.file_processor._process_audio_video_file", return_value={"file_type": "audio"}) as mock_av:
        process_file("tmp_3", str(f))

    mock_av.assert_called_once()


def test_process_pdf_returns_expected_shape(tmp_path):
    fake_doc = MagicMock()
    fake_doc.page_content = "Some PDF text"
    fake_doc.metadata = {
        "page": 1, "total_pages": 2,
        "chunk_method": "semantic", "char_count": 13, "source": "doc.pdf"
    }

    with patch("app.services.file_processor.process_pdf", return_value=[fake_doc]):
        result = _process_pdf_file("tmp_pdf", "/fake/doc.pdf")

    assert result["file_type"]  == "pdf"
    assert result["temp_id"]    == "tmp_pdf"
    assert result["embedded"]   is False
    assert result["status"]     == "ready"
    assert result["utterances"] == []
    assert len(result["chunks"]) == 1

    chunk = result["chunks"][0]
    assert chunk["chunk_index"] == 0
    assert chunk["text"] == "Some PDF text"
    assert "page" in chunk["metadata"]


def test_process_pdf_full_text_joins_chunks(tmp_path):
    docs = []
    for text in ["Hello", "World"]:
        d = MagicMock()
        d.page_content = text
        d.metadata = {"page": 1, "total_pages": 1, "chunk_method": "", "char_count": 5, "source": ""}
        docs.append(d)

    with patch("app.services.file_processor.process_pdf", return_value=docs):
        result = _process_pdf_file("tmp_x", "/fake/doc.pdf")

    assert result["full_text"] == "Hello World"


def test_process_pdf_chunk_indices_are_sequential():
    docs = []
    for i in range(5):
        d = MagicMock()
        d.page_content = f"chunk {i}"
        d.metadata = {"page": i, "total_pages": 5, "chunk_method": "", "char_count": 7, "source": ""}
        docs.append(d)

    with patch("app.services.file_processor.process_pdf", return_value=docs):
        result = _process_pdf_file("tmp_y", "/fake/doc.pdf")

    indices = [c["chunk_index"] for c in result["chunks"]]
    assert indices == list(range(5))


def test_process_audio_video_returns_expected_shape():
    fake_transcription = {
        "utterances": [{"speaker": "A", "text": "Hello"}],
        "rag_chunks": [
            {"start": 0.0,  "end": 5.0,  "text": "Hello there"},
            {"start": 5.0,  "end": 10.0, "text": "How are you"},
        ]
    }

    with patch("app.services.file_processor.transcribe_audio", return_value=fake_transcription):
        result = _process_audio_video_file("tmp_av", "/fake/audio.mp3")

    assert result["file_type"]  == "audio"
    assert result["temp_id"]    == "tmp_av"
    assert result["embedded"]   is False
    assert result["status"]     == "ready"
    assert len(result["chunks"]) == 2
    assert result["utterances"]  == fake_transcription["utterances"]


def test_process_audio_full_text_has_timestamps():
    fake_transcription = {
        "utterances": [],
        "rag_chunks": [{"start": 65.0, "end": 130.0, "text": "Some speech"}]
    }

    with patch("app.services.file_processor.transcribe_audio", return_value=fake_transcription):
        result = _process_audio_video_file("tmp_ts", "/fake/audio.mp3")

    assert "[1:05 - 2:10]" in result["full_text"]
    assert "Some speech"    in result["full_text"]


def test_process_audio_chunk_metadata_has_start_end():
    fake_transcription = {
        "utterances": [],
        "rag_chunks": [{"start": 10.0, "end": 20.0, "text": "Segment one"}]
    }

    with patch("app.services.file_processor.transcribe_audio", return_value=fake_transcription):
        result = _process_audio_video_file("tmp_meta", "/fake/audio.mp3")

    meta = result["chunks"][0]["metadata"]
    assert meta["start"] == 10.0
    assert meta["end"]   == 20.0

def test_embed_and_store_calls_store_vectors():
    chunks = [
        {"chunk_index": 0, "text": "Hello", "metadata": {"page": 1}},
        {"chunk_index": 1, "text": "World", "metadata": {"page": 2}},
    ]

    with patch("app.services.file_processor.store_vectors") as mock_store:
        embed_and_store(
            user_id="user1", session_id="sess1",
            temp_id="tmp1", chunks=chunks,
            file_type="pdf", file_name="doc.pdf"
        )

    mock_store.assert_called_once()
    _, _, docs, _, _ = mock_store.call_args[0]
    assert len(docs) == 2


def test_embed_and_store_injects_metadata():
    chunks = [{"chunk_index": 0, "text": "chunk text", "metadata": {}}]

    with patch("app.services.file_processor.store_vectors") as mock_store:
        embed_and_store(
            user_id="u1", session_id="s1",
            temp_id="t1", chunks=chunks,
            file_type="pdf", file_name="test.pdf"
        )

    docs = mock_store.call_args[0][2]
    meta = docs[0].metadata
    assert meta["session_id"] == "s1"
    assert meta["temp_id"]    == "t1"
    assert meta["file_type"]  == "pdf"
    assert meta["file_name"]  == "test.pdf"


def test_embed_and_store_accepts_pydantic_chunks():
    pydantic_chunk = MagicMock()
    pydantic_chunk.model_dump.return_value = {
        "chunk_index": 0, "text": "Pydantic chunk", "metadata": {}
    }

    with patch("app.services.file_processor.store_vectors") as mock_store:
        embed_and_store("u", "s", "t", [pydantic_chunk], "pdf", "file.pdf")

    pydantic_chunk.model_dump.assert_called_once()
    docs = mock_store.call_args[0][2]
    assert docs[0].page_content == "Pydantic chunk"


def test_replace_file_delegates_to_process_file(tmp_path):
    f = tmp_path / "new.pdf"
    f.write_bytes(b"content")

    with patch("app.services.file_processor.process_file", return_value={"file_type": "pdf"}) as mock_pf:
        result = replace_file("tmp_old", str(f))

    mock_pf.assert_called_once_with("tmp_old", str(f))
    assert result["file_type"] == "pdf"


def _make_mock_llm(chunks: list):
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(return_value=iter(chunks))
    return mock_llm


def _make_chunk(content: str = "", usage: dict | None = None):
    chunk = MagicMock()
    chunk.content        = content
    chunk.usage_metadata = usage
    return chunk


def _collect(gen) -> list[dict]:
    events = []
    for line in gen:
        if line.startswith("data: ") and line.strip() != "data: [DONE]":
            events.append(json.loads(line[len("data: "):]))
    return events


def test_stream_yields_text_events():
    mock_llm = _make_mock_llm([_make_chunk("Hello")])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        events = _collect(stream_response("q", mock_llm))
    text_events = [e for e in events if e["type"] == "text"]
    assert len(text_events) == 1
    assert text_events[0]["data"] == "Hello"


def test_stream_yields_done_sentinel():
    mock_llm = _make_mock_llm([_make_chunk("Hi")])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        raw = list(stream_response("q", mock_llm))
    assert any(line.strip() == "data: [DONE]" for line in raw)


def test_stream_skips_empty_content_chunks():
    mock_llm = _make_mock_llm([_make_chunk(""), _make_chunk("Hi")])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        events = _collect(stream_response("q", mock_llm))
    text_events = [e for e in events if e["type"] == "text"]
    assert len(text_events) == 1
    assert text_events[0]["data"] == "Hi"


def test_stream_concatenates_multiple_chunks():
    mock_llm = _make_mock_llm([
        _make_chunk("Hello "),
        _make_chunk("World"),
        _make_chunk("", usage={"input_tokens": 5, "output_tokens": 3}),
    ])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        events = _collect(stream_response("q", mock_llm))
    usage = next(e for e in events if e["type"] == "usage")
    assert usage["full_response"] == "Hello World"


def test_stream_yields_usage_event_with_correct_fields():
    mock_llm = _make_mock_llm([
        _make_chunk("text"),
        _make_chunk("", usage={"input_tokens": 10, "output_tokens": 20}),
    ])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        events = _collect(stream_response("q", mock_llm))
    usage = next(e for e in events if e["type"] == "usage")
    assert usage["prompt_tokens"]     == 10
    assert usage["completion_tokens"] == 20
    assert usage["total_tokens"]      == 30
    assert "total_cost" in usage

def test_stream_total_cost_is_positive():
    mock_llm = _make_mock_llm([
        _make_chunk("response"),
        _make_chunk("", usage={"input_tokens": 100, "output_tokens": 200}),
    ])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        events = _collect(stream_response("q", mock_llm))
    usage = next(e for e in events if e["type"] == "usage")
    assert usage["total_cost"] > 0


def test_stream_no_usage_chunk_still_completes():
    mock_llm = _make_mock_llm([_make_chunk("Hi")])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        raw = list(stream_response("q", mock_llm))
    assert any("data: [DONE]" in line for line in raw)

def test_stream_event_order():
    mock_llm = _make_mock_llm([
        _make_chunk("Hello"),
        _make_chunk("", usage={"input_tokens": 1, "output_tokens": 1}),
    ])
    with patch("app.services.llm_response_stream.get_google_llm", return_value=mock_llm):
        raw = list(stream_response("q", mock_llm))
    types = []
    for line in raw:
        if line.startswith("data: [DONE]"):
            types.append("done")
        elif line.startswith("data: "):
            try:
                types.append(json.loads(line[6:])["type"])
            except Exception:
                pass
    assert types.index("text")  < types.index("usage")
    assert types.index("usage") < types.index("done")