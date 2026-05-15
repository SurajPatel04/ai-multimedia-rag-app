import pytest
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.utils.embeddings import get_embeddings, embed_model, get_google_embeddings, google_embed_model
import app.utils.file_upload_supabase as module
from app.utils.file_upload_supabase import upload_file_to_supabase
from app.utils.file_upload_supabase import get_fresh_signed_url

from app.utils.llm import llm
from app.utils.llm import google_llm_lite
from app.utils.llm import google_llm

from app.utils.llm import INPUT_COST, OUTPUT_COST
from app.utils.video_to_audio_converter import convert_video_to_audio, VIDEO_EXTENSIONS
import subprocess
from app.utils.video_to_audio_converter import convert_video_to_audio

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
        with patch("langchain_openai.OpenAIEmbeddings.__init__", return_value=None):
            model = get_embeddings()
            assert model is not None

    def test_get_embeddings_is_singleton(self, mock_env):
        from app.utils.embeddings import get_embeddings, embed_model
        assert get_embeddings() is embed_model

    def test_get_google_embeddings_returns_instance(self, mock_env):
        assert get_google_embeddings() is google_embed_model

    def test_get_google_embeddings_is_singleton(self, mock_env):
        first  = get_google_embeddings()
        second = get_google_embeddings()
        assert first is second

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
        """Each upload should store the file under a different UUID-prefixed name."""
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


class TestLLMModels:
    def test_llm_is_not_none(self, mock_env):
        assert llm is not None

    def test_google_llm_lite_is_not_none(self, mock_env):
        assert google_llm_lite is not None

    def test_google_llm_is_not_none(self, mock_env):
        assert google_llm is not None

    def test_cost_constants_are_positive(self, mock_env):
        assert isinstance(INPUT_COST,  float) and INPUT_COST  > 0
        assert isinstance(OUTPUT_COST, float) and OUTPUT_COST > 0

    def test_output_more_expensive_than_input(self, mock_env):
        assert OUTPUT_COST > INPUT_COST

    @pytest.mark.asyncio
    async def test_llm_invoke_returns_content(self, mock_env):
        fake_message = MagicMock()
        fake_message.content = "Hello from the mock LLM!"

        from app.utils.llm import llm
        with patch.object(type(llm), "ainvoke", new_callable=lambda: lambda *a, **kw: AsyncMock(return_value=fake_message)()):
            result = await llm.ainvoke([{"role": "user", "content": "Say hi"}])

        assert result.content == "Hello from the mock LLM!"

    @pytest.mark.asyncio
    async def test_google_llm_invoke_returns_content(self, mock_env):
        fake_message = MagicMock()
        fake_message.content = "Gemini response"

        with patch.object(type(google_llm), "ainvoke", new_callable=lambda: lambda *a, **kw: AsyncMock(return_value=fake_message)()):
            result = await google_llm.ainvoke([{"role": "user", "content": "Say hi"}])

        assert result.content == "Gemini response"

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
            from app.utils.video_to_audio_converter import convert_video_to_audio
            convert_video_to_audio(temp_video_file, output_dir=temp_audio_dir)

        assert "ffmpeg"  in called_cmd
        assert "-vn"     in called_cmd
        assert "-ac"     in called_cmd
        assert "1"       in called_cmd
        assert "-ar"     in called_cmd
        assert "16000"   in called_cmd
        assert "-b:a"    in called_cmd
        assert "32k"     in called_cmd