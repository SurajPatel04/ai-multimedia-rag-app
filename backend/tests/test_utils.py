import pytest
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.utils.embeddings import get_embeddings, get_google_embeddings
import app.utils.file_upload_supabase as module
from app.utils.file_upload_supabase import upload_file_to_supabase
from app.utils.file_upload_supabase import get_fresh_signed_url
from app.utils.llm import get_openai_llm, get_google_llm_lite, get_google_llm, INPUT_COST, OUTPUT_COST
from app.utils.video_to_audio_converter import convert_video_to_audio, VIDEO_EXTENSIONS
import subprocess
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")


@pytest.fixture
def temp_video_file(tmp_path):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"\x00" * 1024)
    return str(video)


@pytest.fixture
def temp_audio_dir(tmp_path):
    audio_dir = tmp_path / "audio_out"
    audio_dir.mkdir()
    return str(audio_dir)


@pytest.fixture
def mock_supabase_client():
    client = AsyncMock()
    upload_mock = AsyncMock(return_value={"Key": "documents/test-file.pdf"})
    signed_url_mock = AsyncMock(return_value={"signedURL": "https://test.supabase.co/signed/test-file.pdf"})
    storage_bucket = MagicMock()
    storage_bucket.upload = upload_mock
    storage_bucket.create_signed_url = signed_url_mock
    client.storage.from_ = MagicMock(return_value=storage_bucket)
    return client


class TestEmbeddings:

    def test_get_embeddings_returns_instance(self, mock_env):
        assert get_embeddings() is not None

    def test_get_embeddings_returns_openai_type(self, mock_env):
        assert isinstance(get_embeddings(), OpenAIEmbeddings)

    def test_get_google_embeddings_returns_instance(self, mock_env):
        assert get_google_embeddings() is not None

    def test_get_google_embeddings_returns_google_type(self, mock_env):
        
        assert isinstance(get_google_embeddings(), GoogleGenerativeAIEmbeddings)

    @pytest.mark.asyncio
    async def test_embed_query_returns_vector(self, mock_env):
        fake_vector = [0.1] * 1536
        with patch("langchain_openai.OpenAIEmbeddings.aembed_query", return_value=fake_vector):
            result = await get_embeddings().aembed_query("hello world")
        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_google_embed_query_returns_vector(self, mock_env):
        fake_vector = [0.2] * 1536
        with patch(
            "langchain_google_genai.GoogleGenerativeAIEmbeddings.aembed_query",
            return_value=fake_vector,
        ):
            result = await get_google_embeddings().aembed_query("test text")
        assert len(result) == 1536

    @patch("app.utils.embeddings.asyncio.sleep")
    def test_get_embeddings_retries_on_quota_error(self, mock_sleep, mock_env):
        with patch("app.utils.embeddings.OpenAIEmbeddings", side_effect=[Exception("429 rate limit"), MagicMock()]) as mock_openai:
            result = get_embeddings(max_retries=2, delay=1.0)
        assert result is not None
        assert mock_openai.call_count == 2
        mock_sleep.assert_called_once()

    def test_get_embeddings_returns_none_on_non_quota_error(self, mock_env):
        with patch("app.utils.embeddings.OpenAIEmbeddings", side_effect=Exception("Invalid API Key")):
            result = get_embeddings(max_retries=2)
        assert result is None

    @patch("app.utils.embeddings.asyncio.sleep")
    def test_get_google_embeddings_retries_on_quota_error(self, mock_sleep, mock_env):
        with patch("app.utils.embeddings.GoogleGenerativeAIEmbeddings", side_effect=[Exception("429 resource_exhausted"), MagicMock()]) as mock_google:
            result = get_google_embeddings(max_retries=2, delay=1.0)
        assert result is not None
        assert mock_google.call_count == 2
        mock_sleep.assert_called_once()

    def test_get_google_embeddings_returns_none_on_non_quota_error(self, mock_env):
        with patch("app.utils.embeddings.GoogleGenerativeAIEmbeddings", side_effect=Exception("Invalid API Key")):
            result = get_google_embeddings(max_retries=2)
        assert result is None


class TestLLMModels:

    def test_get_openai_llm_returns_instance(self, mock_env):
        assert get_openai_llm() is not None

    def test_get_google_llm_lite_returns_instance(self, mock_env):
        with patch("app.utils.llm.init_chat_model", return_value=MagicMock()) as mock_init:
            model = get_google_llm_lite()
            assert model is not None
            mock_init.assert_called_once()

    def test_get_google_llm_returns_instance(self, mock_env):
        with patch("app.utils.llm.init_chat_model", return_value=MagicMock()) as mock_init:
            model = get_google_llm()
            assert model is not None
            mock_init.assert_called_once()

    def test_cost_constants_are_positive(self, mock_env):
        assert isinstance(INPUT_COST, float) and INPUT_COST > 0
        assert isinstance(OUTPUT_COST, float) and OUTPUT_COST > 0

    def test_output_more_expensive_than_input(self, mock_env):
        assert OUTPUT_COST > INPUT_COST

    @pytest.mark.asyncio
    async def test_openai_llm_invoke_returns_content(self, mock_env):
        fake_message = MagicMock()
        fake_message.content = "Hello from the mock LLM!"
        model = get_openai_llm()
        with patch.object(type(model), "ainvoke", new_callable=lambda: lambda *a, **kw: AsyncMock(return_value=fake_message)()):
            result = await model.ainvoke([{"role": "user", "content": "Say hi"}])
        assert result.content == "Hello from the mock LLM!"

    @pytest.mark.asyncio
    async def test_google_llm_invoke_returns_content(self, mock_env):
        fake_message = MagicMock()
        fake_message.content = "Gemini response"

        with patch("app.utils.llm.init_chat_model", return_value=MagicMock()):
            model = get_google_llm()
            model.ainvoke = AsyncMock(return_value=fake_message)
            result = await model.ainvoke([{"role": "user", "content": "Say hi"}])

        assert result.content == "Gemini response"


class TestSupabase:
    @pytest.mark.asyncio
    async def test_get_async_supabase_creates_client(self, mock_env):
        module._async_supabase = None
        with patch(
            "app.utils.file_upload_supabase.async_create_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ) as mock_create:
            client1 = await module.get_async_supabase()
            client2 = await module.get_async_supabase()
            mock_create.assert_called_once()
            assert client1 is client2
        module._async_supabase = None

    @pytest.mark.asyncio
    async def test_upload_file_returns_signed_url(self, mock_env, tmp_path, mock_supabase_client):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy content")
        with patch("app.utils.file_upload_supabase.get_async_supabase", return_value=mock_supabase_client):
            result = await upload_file_to_supabase(str(pdf))
        assert "file_path" in result
        assert "signed_url" in result
        assert result["signed_url"].startswith("https://")
        assert result["file_path"].endswith("test.pdf")

    @pytest.mark.asyncio
    async def test_upload_file_generates_unique_names(self, mock_env, tmp_path, mock_supabase_client):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"dummy")
        paths = []
        with patch("app.utils.file_upload_supabase.get_async_supabase", return_value=mock_supabase_client):
            for _ in range(2):
                result = await upload_file_to_supabase(str(pdf))
                paths.append(result["file_path"])
        assert paths[0] != paths[1]

    @pytest.mark.asyncio
    async def test_get_fresh_signed_url_passthrough_for_http(self, mock_env):
        url = "https://already-signed.example.com/file.pdf"
        result = await get_fresh_signed_url(url)
        assert result == url

    @pytest.mark.asyncio
    async def test_get_fresh_signed_url_for_storage_path(self, mock_env, mock_supabase_client):
        with patch("app.utils.file_upload_supabase.get_async_supabase", return_value=mock_supabase_client):
            result = await get_fresh_signed_url("documents/some-file.pdf")
        assert result == "https://test.supabase.co/signed/test-file.pdf"

    @pytest.mark.asyncio
    async def test_upload_file_not_found_raises(self, mock_env, mock_supabase_client):
        with patch("app.utils.file_upload_supabase.get_async_supabase", return_value=mock_supabase_client):
            with pytest.raises((FileNotFoundError, OSError)):
                await upload_file_to_supabase("/tmp/does_not_exist_abc123.pdf")


class TestVideoConverter:

    def test_convert_video_to_audio_success(self, temp_video_file, temp_audio_dir):
        fake_audio_path = os.path.join(temp_audio_dir, "fixed-uuid.mp3")
        def fake_run(cmd, **kwargs):
            open(fake_audio_path, "wb").close()
        with patch("subprocess.run", side_effect=fake_run) as mock_run, \
             patch("uuid.uuid4", return_value=MagicMock(hex="fixed-uuid")):
            result = convert_video_to_audio(temp_video_file, output_dir=temp_audio_dir)
        mock_run.assert_called_once()
        assert not os.path.exists(temp_video_file)
        assert result.endswith(".mp3")

    def test_convert_video_missing_file_raises(self, temp_audio_dir):
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            convert_video_to_audio("/tmp/ghost_video.mp4", output_dir=temp_audio_dir)

    def test_convert_video_ffmpeg_failure_cleans_up(self, temp_video_file, temp_audio_dir):
        partial_audio = os.path.join(temp_audio_dir, "fixed-uuid.mp3")
        def fake_fail(cmd, **kwargs):
            open(partial_audio, "wb").close()
            raise subprocess.CalledProcessError(1, cmd)
        with patch("subprocess.run", side_effect=fake_fail), \
             patch("uuid.uuid4", return_value=MagicMock(hex="fixed-uuid")):
            with pytest.raises(RuntimeError, match="ffmpeg conversion failed"):
                convert_video_to_audio(temp_video_file, output_dir=temp_audio_dir)
        assert not os.path.exists(partial_audio)

    def test_convert_video_ffmpeg_not_installed_raises(self, temp_video_file, temp_audio_dir):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
                convert_video_to_audio(temp_video_file, output_dir=temp_audio_dir)

    def test_convert_creates_output_dir_if_missing(self, temp_video_file, tmp_path):
        new_dir = str(tmp_path / "brand_new_dir")
        fake_audio = os.path.join(new_dir, "fixed-uuid.mp3")
        def fake_run(cmd, **kwargs):
            open(fake_audio, "wb").close()
        with patch("subprocess.run", side_effect=fake_run), \
             patch("uuid.uuid4", return_value=MagicMock(hex="fixed-uuid")):
            convert_video_to_audio(temp_video_file, output_dir=new_dir)
        assert os.path.isdir(new_dir)

    def test_video_extensions_constant(self):
        for ext in ("mp4", "mkv", "mov", "avi", "webm", "flv"):
            assert ext in VIDEO_EXTENSIONS

    def test_ffmpeg_command_structure(self, temp_video_file, temp_audio_dir):
        called_cmd = []
        def capture_cmd(cmd, **kwargs):
            called_cmd.extend(cmd)
            output = cmd[cmd.index("-y") + 1]
            open(output, "wb").close()
        with patch("subprocess.run", side_effect=capture_cmd):
            convert_video_to_audio(temp_video_file, output_dir=temp_audio_dir)
        assert "ffmpeg" in called_cmd
        assert "-vn"    in called_cmd
        assert "-ac"    in called_cmd
        assert "1"      in called_cmd
        assert "-ar"    in called_cmd
        assert "16000"  in called_cmd
        assert "-b:a"   in called_cmd
        assert "32k"    in called_cmd


class TestRouterHistory:

    def test_trim_by_tokens_short(self):
        from app.utils.router_history import trim_by_tokens
        text = "Hello world"
        assert trim_by_tokens(text, max_tokens=10) == "Hello world"

    def test_trim_by_tokens_long(self):
        from app.utils.router_history import trim_by_tokens
        text = "This is a very long text that needs trimming"
        trimmed = trim_by_tokens(text, max_tokens=3)
        assert trimmed.endswith("...")
        assert len(trimmed) < len(text) + 3

    def test_build_router_history_empty(self):
        from app.utils.router_history import build_router_history
        assert build_router_history([]) == ""

    def test_build_router_history_basic(self):
        from app.utils.router_history import build_router_history
        from langchain_core.messages import HumanMessage, AIMessage
        history = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello! How can I help?"),
            HumanMessage(content="What is RAG?")
        ]
        res = build_router_history(history)
        assert "User: Hi" in res
        assert "Assistant: Hello! How can I help?" in res
        assert "User: What is RAG?" in res

    def test_build_router_history_ai_trimming(self):
        from app.utils.router_history import build_router_history
        from langchain_core.messages import HumanMessage, AIMessage
        long_ai_text = "A" * 1000
        history = [
            HumanMessage(content="Explain"),
            AIMessage(content=long_ai_text)
        ]
        res = build_router_history(history, ai_char_limit=10)
        assert "Assistant: AAAAAAAAAA..." in res

    def test_build_router_history_human_limit(self):
        from app.utils.router_history import build_router_history
        from langchain_core.messages import HumanMessage
        history = [
            HumanMessage(content="First"),
            HumanMessage(content="Second"),
            HumanMessage(content="Third"),
            HumanMessage(content="Fourth")
        ]
        res = build_router_history(history, human_message_limit=2)
        assert "User: Third" in res
        assert "User: Fourth" in res
        assert "User: First" not in res
        assert "User: Second" not in res