import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from types import SimpleNamespace

from app.graph.state import State
from app.graph.nodes.context_builder_node import context_builder_node
from app.graph.nodes.router_query_node import router_query_node
from app.graph.workflow import route_query
from app.graph.nodes.title_generator_node import title_generator_node
from app.graph.nodes.mongo_db_retrieve_node import mongo_db_retrieve_node
from app.graph.nodes.vector_search_node import vector_search_node
from app.graph.workflow import should_generate_title
from app.graph.nodes.memory_summarizer_node import run_summarizer_background
from app.graph.nodes.memory_summarizer_node import should_summarize

def make_state(**kwargs):
    defaults = {
        "query": "What is this about?",
        "session_id": "test_session_graph",
        "user_id": "test_user_123",
        "summary": "",
        "context": "",
        "title": "",
        "chat_history": [],
        "messages": [],
        "uploaded_files": [],
        "latest_files": [],
        "extra_query": [],
        "target_files": None,
        "message_index": 0,
        "media_refs": None,
        "mode": None,
        "response": None,
    }
    defaults.update(kwargs)
    return State(**defaults)


async def test_context_builder_direct_llm_mode():
    state = make_state(mode="direct_llm", query="Hello!")
    result = await context_builder_node(state)

    assert "messages" in result
    assert "chat_history" in result
    assert isinstance(result["messages"][0], SystemMessage)
    assert isinstance(result["messages"][-1], HumanMessage)
    assert result["messages"][-1].content == "Hello!"


async def test_context_builder_with_context():
    state = make_state(
        mode="vector_search",
        query="What is Python?",
        context="Python is a programming language."
    )
    result = await context_builder_node(state)

    assert "messages" in result
    system_content = result["messages"][0].content
    assert "Python is a programming language." in system_content


async def test_context_builder_empty_context():
    state = make_state(
        mode="vector_search",
        query="What is this?",
        context=""
    )
    result = await context_builder_node(state)

    system_content = result["messages"][0].content
    assert "No files were uploaded" in system_content


async def test_context_builder_with_summary():
    state = make_state(
        mode="direct_llm",
        query="Tell me more",
        summary="User asked about Python earlier."
    )
    result = await context_builder_node(state)

    system_content = result["messages"][0].content
    assert "User asked about Python earlier." in system_content


async def test_context_builder_updates_chat_history():
    existing_history = [
        HumanMessage(content="Previous question"),
        AIMessage(content="Previous answer"),
    ]
    state = make_state(
        mode="direct_llm",
        query="New question",
        chat_history=existing_history
    )
    result = await context_builder_node(state)

    assert len(result["chat_history"]) == 3
    assert result["chat_history"][-1].content == "New question"


async def test_context_builder_no_empty_context_signals():
    for signal in ["no relevant content found for your query.", "no context available.", ""]:
        state = make_state(
            mode="vector_search",
            query="test",
            context=signal
        )
        result = await context_builder_node(state)
        system_content = result["messages"][0].content
        assert "No files were uploaded" in system_content


async def test_router_returns_vector_search():
    mock_response = MagicMock()
    mock_response.mode = "vector_search"
    mock_response.target_files = ["test.pdf"]
    mock_response.extra_query = ["alternative query"]

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graph.nodes.router_query_node.get_google_llm", return_value=mock_llm):
        state = make_state(query="What is Python?", uploaded_files=["test.pdf"])
        result = await router_query_node(state)

    assert result["mode"] == "vector_search"
    assert result["target_files"] == ["test.pdf"]
    assert result["extra_query"] == ["alternative query"]

async def test_router_returns_direct_llm():
    mock_response = MagicMock()
    mock_response.mode = "direct_llm"
    mock_response.target_files = None
    mock_response.extra_query = None

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graph.nodes.router_query_node.get_google_llm", return_value=mock_llm):
        state = make_state(query="Hello!")
        result = await router_query_node(state)

    assert result["mode"] == "direct_llm"
    assert result["extra_query"] == []


async def test_router_returns_mongo_db_retrieve():
    mock_response = MagicMock()
    mock_response.mode = "mongo_db_retrieve"
    mock_response.target_files = ["resume.pdf"]
    mock_response.extra_query = None

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graph.nodes.router_query_node.get_google_llm", return_value=mock_llm):
        state = make_state(query="Summarize my resume", uploaded_files=["resume.pdf"])
        result = await router_query_node(state)

    assert result["mode"] == "mongo_db_retrieve"


async def test_router_fallback_on_error():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
        side_effect=Exception("LLM error")
    )

    with patch("app.graph.nodes.router_query_node.get_google_llm", return_value=mock_llm):
        state = make_state(query="What is this?")
        result = await router_query_node(state)

    assert result["mode"] == "direct_llm_call"
    assert result["extra_query"] == []
    assert result["target_files"] is None


async def test_title_generator_generates_title():
    mock_response = MagicMock()
    mock_response.title = "Python Resume Analysis"

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graph.nodes.title_generator_node.get_google_llm", return_value=mock_llm), \
         patch("app.graph.nodes.title_generator_node.ChatSession") as mock_session:
        mock_session.find_one.return_value.update = AsyncMock()
        state = make_state(query="Summarize my resume", message_index=0)
        result = await title_generator_node(state)

    assert result["title"] == "Python Resume Analysis"


async def test_title_generator_skips_if_not_first_message():
    with patch("app.graph.nodes.title_generator_node.get_google_llm", return_value=MagicMock()):
        state = make_state(query="Tell me more", message_index=2)
        result = await title_generator_node(state)
    assert result == {}

async def test_mongo_db_retrieve_no_docs():
    with patch(
        "app.graph.nodes.mongo_db_retrieve_node.SessionDocument"
    ) as mock_doc:
        mock_doc.find.return_value.to_list = AsyncMock(return_value=[])

        state = make_state(session_id="empty_session")
        result = await mongo_db_retrieve_node(state)

        assert "No uploaded documents found" in result["context"]


async def test_mongo_db_retrieve_with_docs():
    mock_doc = MagicMock()
    mock_doc.file_name = "test.pdf"
    mock_doc.file_type = "pdf"
    mock_doc.summary = None
    mock_doc.full_text = "This is the document content."

    with patch(
        "app.graph.nodes.mongo_db_retrieve_node.SessionDocument"
    ) as mock_session_doc:
        mock_session_doc.find.return_value.to_list = AsyncMock(
            return_value=[mock_doc]
        )

        state = make_state(session_id="test_session")
        result = await mongo_db_retrieve_node(state)

        assert "test.pdf" in result["context"]
        assert "This is the document content." in result["context"]


async def test_mongo_db_retrieve_uses_summary_over_full_text():
    mock_doc = MagicMock()
    mock_doc.file_name = "test.pdf"
    mock_doc.file_type = "pdf"
    mock_doc.summary = "This is the summary."
    mock_doc.full_text = "This is the full text."

    with patch(
        "app.graph.nodes.mongo_db_retrieve_node.SessionDocument"
    ) as mock_session_doc:
        mock_session_doc.find.return_value.to_list = AsyncMock(
            return_value=[mock_doc]
        )

        state = make_state(session_id="test_session")
        result = await mongo_db_retrieve_node(state)

        assert "This is the summary." in result["context"]
        assert "This is the full text." not in result["context"]


async def test_mongo_db_retrieve_filters_by_target_files():
    mock_doc1 = MagicMock()
    mock_doc1.file_name = "resume.pdf"
    mock_doc1.file_type = "pdf"
    mock_doc1.summary = None
    mock_doc1.full_text = "Resume content"

    mock_doc2 = MagicMock()
    mock_doc2.file_name = "assignment.pdf"
    mock_doc2.file_type = "pdf"
    mock_doc2.summary = None
    mock_doc2.full_text = "Assignment content"

    with patch(
        "app.graph.nodes.mongo_db_retrieve_node.SessionDocument"
    ) as mock_session_doc:
        mock_session_doc.find.return_value.to_list = AsyncMock(
            return_value=[mock_doc1, mock_doc2]
        )

        state = make_state(
            session_id="test_session",
            target_files=["resume.pdf"]
        )
        result = await mongo_db_retrieve_node(state)

        assert "Resume content" in result["context"]
        assert "Assignment content" not in result["context"]

async def test_vector_search_no_results():
    with patch(
        "app.graph.nodes.vector_search_node.vector_search",
        return_value=[]
    ):
        state = make_state(query="What is Python?")
        result = await vector_search_node(state)

        assert "No relevant content" in result["context"]
        assert result["media_refs"] is None


async def test_vector_search_with_text_results():
    mock_results = [
        {
            "text": "Python is a programming language.",
            "metadata": {"file_name": "test.pdf"}
        }
    ]

    with patch(
        "app.graph.nodes.vector_search_node.vector_search",
        return_value=mock_results
    ):
        state = make_state(query="What is Python?")
        result = await vector_search_node(state)

        assert "Python is a programming language." in result["context"]
        assert result["media_refs"] is None  # no timestamps


async def test_vector_search_with_timestamp_results():

    mock_results = [
        {
            "text": "This is about Python.",
            "metadata": {
                "file_name": "lecture.mp4",
                "start": 135.0,
                "end": 165.0
            }
        }
    ]

    with patch(
        "app.graph.nodes.vector_search_node.vector_search",
        return_value=mock_results
    ):
        state = make_state(query="Python lecture")
        result = await vector_search_node(state)

        assert "02:15" in result["context"]   # 135s → 02:15
        assert result["media_refs"] is not None
        assert len(result["media_refs"]) == 1
        assert result["media_refs"][0]["start"] == 135.0


async def test_vector_search_deduplicates_results():
    mock_results = [
        {"text": "Duplicate content.", "metadata": {"file_name": "test.pdf"}},
        {"text": "Duplicate content.", "metadata": {"file_name": "test.pdf"}},
    ]

    with patch(
        "app.graph.nodes.vector_search_node.vector_search",
        return_value=mock_results
    ):
        state = make_state(query="test")
        result = await vector_search_node(state)

        # deduplicated — appears only once
        assert result["context"].count("Duplicate content.") == 1


async def test_vector_search_uses_extra_queries():
    call_count = 0

    def mock_search(**kwargs):
        nonlocal call_count
        call_count += 1
        return [{"text": f"Result for {kwargs['query']}", "metadata": {}}]

    with patch(
        "app.graph.nodes.vector_search_node.vector_search",
        side_effect=mock_search
    ):
        state = make_state(
            query="main query",
            extra_query=["extra query 1", "extra query 2"]
        )
        result = await vector_search_node(state)

        assert call_count == 3

async def test_should_summarize_by_message_count():
    history = [HumanMessage(content=f"msg {i}") for i in range(8)]
    triggered, reason = should_summarize(history)

    assert triggered is True
    assert "message count" in reason


async def test_should_not_summarize_short_history():
    history = [HumanMessage(content="short msg") for _ in range(3)]
    triggered, _ = should_summarize(history)
    assert triggered is False


async def test_run_summarizer_skips_if_not_triggered():
    state = {
        "chat_history": [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello"),
        ],
        "summary": ""
    }

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()

    with patch("app.graph.nodes.memory_summarizer_node.get_google_llm", return_value=mock_llm):
        await run_summarizer_background(state, config={})

    mock_llm.ainvoke.assert_not_called()


async def test_run_summarizer_generates_summary():
    history = [
        HumanMessage(content=f"Question {i}") for i in range(8)
    ] + [
        AIMessage(content=f"Answer {i}") for i in range(8)
    ]

    mock_response = MagicMock()
    mock_response.content = "Summary of conversation."

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graph.nodes.memory_summarizer_node.get_google_llm", return_value=mock_llm), \
         patch("app.graph.nodes.memory_summarizer_node.graph") as mock_graph:
        mock_graph.aupdate_state = AsyncMock()
        state = {"chat_history": history, "summary": ""}
        await run_summarizer_background(state, config={"configurable": {"thread_id": "test"}})

    mock_llm.ainvoke.assert_called_once()
    mock_graph.aupdate_state.assert_called_once()

def test_should_generate_title_when_title_empty():
    state = make_state(title="")
    assert should_generate_title(state) == "title_generator"


def test_should_skip_title_when_already_set():
    state = make_state(title="Existing Title")
    assert should_generate_title(state) == "router_query"


def test_route_query_vector_search():
    state = make_state(mode="vector_search")
    assert route_query(state) == "vector_search"


def test_route_query_mongo_db_retrieve():
    state = make_state(mode="mongo_db_retrieve")
    assert route_query(state) == "mongo_db_retrieve"


def test_route_query_direct_llm():
    state = make_state(mode="direct_llm")
    assert route_query(state) == "direct_llm"


def test_route_query_fallback_to_direct_llm():
    state = SimpleNamespace(mode="direct_llm_call")
    assert route_query(state) == "direct_llm"


def test_route_query_none_mode_fallback():
    state = make_state(mode=None)
    assert route_query(state) == "direct_llm"