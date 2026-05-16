import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from beanie import PydanticObjectId
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.temp_data import TempData
from app.models.chat_message import FileReference
from app.models.session_document import SessionDocument
from app.models.user import User
from langchain_core.messages import HumanMessage
import uuid


async def cleanup_session(session_id: str):
    await ChatMessage.find({"session_id": session_id}).delete()
    await ChatSession.find({"session_id": session_id}).delete()
    await SessionDocument.find({"session_id": session_id}).delete()


MOCK_GRAPH_RESULT = {
    "title": "Test Chat",
    "message_index": 0,
    "chat_history": [],
    "messages": [HumanMessage(content="What is this about?")],
    "media_refs": None,
}

MOCK_STREAM_CHUNK = MagicMock(
    content="This is a test response.",
    usage_metadata={"input_tokens": 10, "output_tokens": 20}
)


async def test_get_sessions_success(authenticated_client):
    res = await authenticated_client.get("/api/v1/chat/sessions?page=1&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "data" in data
    assert "pagination" in data


async def test_get_sessions_unauthenticated(client):
    res = await client.get("/api/v1/chat/sessions")
    assert res.status_code == 401


async def test_get_sessions_pagination(authenticated_client):
    res = await authenticated_client.get("/api/v1/chat/sessions?page=1&limit=5")
    assert res.status_code == 200
    pagination = res.json()["pagination"]
    assert pagination["page"] == 1
    assert pagination["limit"] == 5


async def test_get_session_history_not_found(authenticated_client):
    res = await authenticated_client.get("/api/v1/chat/session/nonexistent_session_id")
    assert res.status_code == 404


async def test_get_session_history_unauthenticated(client):
    res = await client.get("/api/v1/chat/session/some_session_id")
    assert res.status_code == 401


async def test_get_session_history_success(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_history_001"
    session = ChatSession(session_id=session_id, user_id=user.id, title="Test Session")
    await session.insert()

    await ChatMessage(
        session_id=session_id, user_id=user.id,
        role="human", content="Hello", message_index=0,
    ).insert()

    res = await authenticated_client.get(f"/api/v1/chat/session/{session_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["session"]["session_id"] == session_id
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Hello"

    await cleanup_session(session_id)


async def test_get_session_history_returns_multiple_messages(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_history_multi_001"
    await cleanup_session(session_id)

    await ChatSession(session_id=session_id, user_id=user.id, title="Multi").insert()
    for i, (role, content) in enumerate([("human", "Hi"), ("ai", "Hello!"), ("human", "How are you?")]):
        await ChatMessage(
            session_id=session_id, user_id=user.id,
            role=role, content=content, message_index=i
        ).insert()

    res = await authenticated_client.get(f"/api/v1/chat/session/{session_id}")
    assert res.status_code == 200
    messages = res.json()["data"]["messages"]
    assert len(messages) == 3
    assert messages[0]["message_index"] < messages[1]["message_index"]

    await cleanup_session(session_id)


async def test_update_session_title_success(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_update_001"
    await ChatSession(session_id=session_id, user_id=user.id, title="Old Title").insert()

    res = await authenticated_client.patch(
        f"/api/v1/chat/session/{session_id}",
        json={"title": "New Title"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["title"] == "New Title"

    await cleanup_session(session_id)


async def test_update_session_title_not_found(authenticated_client):
    res = await authenticated_client.patch(
        "/api/v1/chat/session/nonexistent_session",
        json={"title": "New Title"}
    )
    assert res.status_code == 404


async def test_update_session_title_empty(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_empty_title_001"
    await ChatSession(session_id=session_id, user_id=user.id, title="Old Title").insert()

    res = await authenticated_client.patch(
        f"/api/v1/chat/session/{session_id}",
        json={"title": ""}
    )
    assert res.status_code == 422

    await cleanup_session(session_id)


async def test_update_session_title_unauthenticated(client):
    res = await client.patch("/api/v1/chat/session/some_id", json={"title": "New Title"})
    assert res.status_code == 401


async def test_update_session_title_persists(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_persist_001"
    await cleanup_session(session_id)

    await ChatSession(session_id=session_id, user_id=user.id, title="Before").insert()

    await authenticated_client.patch(
        f"/api/v1/chat/session/{session_id}",
        json={"title": "After"}
    )
    res = await authenticated_client.get(f"/api/v1/chat/session/{session_id}")
    assert res.json()["data"]["session"]["title"] == "After"

    await cleanup_session(session_id)


async def test_delete_session_success(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_delete_001"
    await cleanup_session(session_id)

    await ChatSession(session_id=session_id, user_id=user.id, title="To Delete").insert()

    res = await authenticated_client.delete(f"/api/v1/chat/session/{session_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True

    session = await ChatSession.find_one({"session_id": session_id})
    assert session is not None
    assert session.is_active is False

    await cleanup_session(session_id)


async def test_delete_session_not_found(authenticated_client):
    res = await authenticated_client.delete("/api/v1/chat/session/ghost_session_999")
    assert res.status_code == 404


async def test_delete_session_unauthenticated(client):
    res = await client.delete("/api/v1/chat/session/some_session_id")
    assert res.status_code == 401


async def test_delete_session_hides_from_sessions_list(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_hidden_001"
    await cleanup_session(session_id)

    await ChatSession(session_id=session_id, user_id=user.id, title="Hidden").insert()
    await authenticated_client.delete(f"/api/v1/chat/session/{session_id}")

    res = await authenticated_client.get("/api/v1/chat/sessions?page=1&limit=100")
    session_ids = [s["session_id"] for s in res.json()["data"]]
    assert session_id not in session_ids

    await cleanup_session(session_id)


async def test_delete_session_already_deleted(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_session_double_delete_001"
    await cleanup_session(session_id)

    await ChatSession(
        session_id=session_id, user_id=user.id,
        title="Already Gone", is_active=False
    ).insert()

    res = await authenticated_client.delete(f"/api/v1/chat/session/{session_id}")
    assert res.status_code == 404

    await cleanup_session(session_id)


async def test_delete_session_does_not_affect_other_sessions(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_a = "test_session_del_a"
    session_b = "test_session_del_b"
    await cleanup_session(session_a)
    await cleanup_session(session_b)

    await ChatSession(session_id=session_a, user_id=user.id, title="A").insert()
    await ChatSession(session_id=session_b, user_id=user.id, title="B").insert()

    await authenticated_client.delete(f"/api/v1/chat/session/{session_a}")

    session = await ChatSession.find_one({"session_id": session_b})
    assert session.is_active is True

    await cleanup_session(session_a)
    await cleanup_session(session_b)


async def test_query_new_session(authenticated_client):
    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([MOCK_STREAM_CHUNK])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value=MOCK_GRAPH_RESULT)), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()):
        res = await authenticated_client.post("/api/v1/chat/query", json={"query": "What is this about?"})
        assert res.status_code == 200
        session_id = res.headers.get("session-id")
        assert session_id is not None
        await cleanup_session(session_id)


async def test_query_existing_session(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_existing_session_001"
    await cleanup_session(session_id)
    await ChatSession(session_id=session_id, user_id=user.id, title="Existing").insert()

    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([MOCK_STREAM_CHUNK])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value={**MOCK_GRAPH_RESULT, "title": "Existing"})), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()):
        res = await authenticated_client.post(
            "/api/v1/chat/query",
            json={"query": "Tell me more", "session_id": session_id}
        )
        assert res.status_code == 200

    await cleanup_session(session_id)


async def test_query_unauthenticated(client):
    res = await client.post("/api/v1/chat/query", json={"query": "Hello"})
    assert res.status_code == 401


async def test_query_missing_query_field(authenticated_client):
    res = await authenticated_client.post("/api/v1/chat/query", json={})
    assert res.status_code == 422


async def test_query_response_has_session_id_header(authenticated_client):
    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([MOCK_STREAM_CHUNK])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value=MOCK_GRAPH_RESULT)), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()):
        res = await authenticated_client.post("/api/v1/chat/query", json={"query": "Any question"})

    assert "session-id" in res.headers
    await cleanup_session(res.headers["session-id"])


async def test_query_creates_chat_session_in_db(authenticated_client):
    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([MOCK_STREAM_CHUNK])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value=MOCK_GRAPH_RESULT)), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()):
        res = await authenticated_client.post("/api/v1/chat/query", json={"query": "Create a session for me"})

    session_id = res.headers.get("session-id")
    session = await ChatSession.find_one({"session_id": session_id})
    assert session is not None
    await cleanup_session(session_id)


async def test_query_temp_id_not_found(authenticated_client):
    with patch("app.router.chat.get_google_llm", return_value=MagicMock()):
        res = await authenticated_client.post(
            "/api/v1/chat/query",
            json={"query": "Hello", "temp_id": "fake_temp_id"}
        )
    assert res.status_code == 404
    assert "No uploaded files found" in res.text


async def test_query_with_valid_temp_id_migration(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    temp_id = "test_migrate_temp_001"

    mock_chunks = [{"text": "Test chunk", "chunk_index": 0, "metadata": {"page": 1}}]

    await TempData(
        temp_id=temp_id, file_id=f"file_{uuid.uuid4().hex}",
        user_id=str(user.id), file_name="test_doc.pdf",
        file_url="http://example.com/test_doc.pdf", file_type="pdf",
        content_type="application/pdf", full_text="Test content",
        chunks=mock_chunks, embedded=False
    ).insert()

    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([MOCK_STREAM_CHUNK])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value=MOCK_GRAPH_RESULT)), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()), \
         patch("app.router.chat.embed_and_store"):
        res = await authenticated_client.post(
            "/api/v1/chat/query",
            json={"query": "Analyze my document", "temp_id": temp_id}
        )
        assert res.status_code == 200
        session_id = res.headers.get("session-id")
        doc = await SessionDocument.find_one({"session_id": session_id})
        assert doc is not None
        assert doc.file_name == "test_doc.pdf"
        await cleanup_session(session_id)


async def test_query_internal_server_error(authenticated_client):
    with patch("app.router.chat.get_google_llm", return_value=MagicMock()), \
         patch("app.router.chat.graph.ainvoke", side_effect=Exception("Critical graph failure!")):
        res = await authenticated_client.post(
            "/api/v1/chat/query",
            json={"query": "Hello"}
        )
    assert res.status_code == 500
    assert "Critical graph failure" in res.text


async def test_query_with_complex_chunks_and_media_refs(authenticated_client):
    graph_result_media = {
        "title": "Media Chat", "message_index": 0,
        "chat_history": [], "messages": [],
        "media_refs": [{
            "document_id": str(PydanticObjectId()),
            "file_name": "demo_video.mp4",
            "file_url": "http://example.com/demo.mp4",
            "file_type": "video"
        }]
    }

    class ComplexChunk:
        content = [{"type": "text", "text": "Multi "}, {"type": "text", "text": "part response"}]
        usage_metadata = {"input_tokens": 100, "output_tokens": 50}

    mock_llm = MagicMock()
    mock_llm.astream = lambda msgs: _async_iter([ComplexChunk()])

    with patch("app.router.chat.graph.ainvoke", new=AsyncMock(return_value=graph_result_media)), \
         patch("app.router.chat.get_openai_llm", return_value=mock_llm), \
         patch("app.router.chat.graph.aupdate_state", new=AsyncMock()):
        res = await authenticated_client.post("/api/v1/chat/query", json={"query": "Show me the video"})
        assert res.status_code == 200
        assert "demo_video.mp4" in res.text
        assert "Multi " in res.text
        assert "part response" in res.text


async def test_get_session_history_with_file_references(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    session_id = "test_history_files_001"
    await cleanup_session(session_id)

    await ChatSession(session_id=session_id, user_id=user.id, title="Files Chat").insert()

    await ChatMessage(
        session_id=session_id, user_id=user.id,
        role="ai", content="Here is the document.", message_index=0,
        file_references=[
            FileReference(
                document_id=PydanticObjectId(),
                file_name="report.pdf",
                file_url="http://example.com/report.pdf",
                file_type="pdf",
                content_type="application/pdf"
            )
        ]
    ).insert()

    with patch("app.router.chat.get_fresh_signed_url", return_value="http://signed-url.com/report.pdf"):
        res = await authenticated_client.get(f"/api/v1/chat/session/{session_id}")
        assert res.status_code == 200
        msg_data = res.json()["data"]["messages"][0]
        assert len(msg_data["file_references"]) == 1
        assert msg_data["file_references"][0]["file_name"] == "report.pdf"
        assert msg_data["file_references"][0]["file_url"] == "http://signed-url.com/report.pdf"

    await cleanup_session(session_id)


async def test_get_sessions_empty_list(authenticated_client, registered_user):
    user = await User.find_one({"email": registered_user["email"]})
    await ChatSession.find({"user_id": user.id}).delete()

    res = await authenticated_client.get("/api/v1/chat/sessions")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 0
    assert data["pagination"]["total_sessions"] == 0


async def _async_iter(items):
    for item in items:
        yield item