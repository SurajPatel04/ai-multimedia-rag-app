import pytest
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from app.helpers.text_splitter import text_splitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
import app.helpers.vector_db as vdb
from langchain_core.documents import Document
from app.helpers.whisper_processor import process_transcript
from app.helpers.whisper_transcriber import merge_utterances
from app.helpers.whisper_transcriber import find_exact_timestamp
from app.helpers.whisper_transcriber import transcribe_audio
from app.helpers.summarizer import generate_session_summary
from app.helpers.summarizer import DIRECT_TOKEN_THRESHOLD
from app.helpers.summarizer import count_tokens
from app.helpers.summarizer import _summarize_text
from app.helpers.summarizer import _summarize_large_doc
from app.helpers.summarizer import _summarize_large_doc, CHUNK_BATCH_TOKEN_LIMIT
from app.helpers.whisper_transcriber import transcribe_audio

class TestTextSplitter:
    def test_returns_splitter_instance(self):
        splitter = text_splitter()
        assert isinstance(splitter, RecursiveCharacterTextSplitter)

    def test_default_chunk_size(self):
        splitter = text_splitter()
        assert splitter._chunk_size == 1000

    def test_default_chunk_overlap(self):
        splitter = text_splitter()
        assert splitter._chunk_overlap == 200

    def test_custom_chunk_size(self):
        splitter = text_splitter(chunk_size=500, chunk_overlap=50)
        assert splitter._chunk_size == 500

    def test_splits_long_text(self):
        splitter = text_splitter(chunk_size=20, chunk_overlap=0)
        docs = splitter.create_documents(["word " * 100])
        assert len(docs) > 1

class TestPdfReader:
    def _make_page(self, content: str, metadata: dict = None):
        page = MagicMock()
        page.page_content = content
        page.metadata = metadata or {}
        return page

    def test_process_pdf_returns_list(self):
        pages = [self._make_page("Hello world " * 50)]

        with patch("app.helpers.pdf_reader.PyMuPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = pages
            from app.helpers.pdf_reader import process_pdf
            result = process_pdf("/fake/doc.pdf")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_process_pdf_chunk_has_metadata(self):
        pages = [self._make_page("Some text " * 30)]

        with patch("app.helpers.pdf_reader.PyMuPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = pages
            from app.helpers.pdf_reader import process_pdf
            chunks = process_pdf("/fake/doc.pdf")

        meta = chunks[0].metadata
        assert meta["page"]         == 1
        assert meta["total_pages"]  == 1
        assert meta["chunk_method"] == "PdfProcessor"
        assert meta["source"]       == "/fake/doc.pdf"
        assert "char_count" in meta

    def test_process_pdf_page_numbers_are_1_indexed(self):
        pages = [
            self._make_page("Page one " * 30),
            self._make_page("Page two " * 30),
        ]

        with patch("app.helpers.pdf_reader.PyMuPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = pages
            from app.helpers.pdf_reader import process_pdf
            chunks = process_pdf("/fake/multi.pdf")

        page_numbers = {c.metadata["page"] for c in chunks}
        assert 1 in page_numbers
        assert 0 not in page_numbers

    def test_process_pdf_total_pages_correct(self):
        pages = [self._make_page(f"Page {i} content " * 30) for i in range(3)]

        with patch("app.helpers.pdf_reader.PyMuPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = pages
            from app.helpers.pdf_reader import process_pdf
            chunks = process_pdf("/fake/three_pages.pdf")

        assert all(c.metadata["total_pages"] == 3 for c in chunks)

    def test_process_pdf_empty_page_returns_no_chunks(self):
        pages = [self._make_page("")]

        with patch("app.helpers.pdf_reader.PyMuPDFLoader") as MockLoader:
            MockLoader.return_value.load.return_value = pages
            from app.helpers.pdf_reader import process_pdf
            result = process_pdf("/fake/empty.pdf")

        assert result == []


class TestVectorDb:
    @pytest.fixture(autouse=True)
    def clean_faiss(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))
        yield

    def _make_docs(self, n=2):
        from langchain_core.documents import Document
        return [
            Document(
                page_content=f"chunk {i}",
                metadata={"session_id": "sess1", "file_name": "doc.pdf"}
            )
            for i in range(n)
        ]

    def _mock_embeddings(self):
        emb = MagicMock()
        emb.embed_documents = MagicMock(return_value=[[0.1] * 1536])
        emb.embed_query     = MagicMock(return_value=[0.1] * 1536)
        return emb

    def test_get_user_index_path_format(self):
        path = vdb.get_user_index_path("user123")
        assert "user123" in path


    def test_store_vectors_creates_index(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        mock_store = MagicMock()
        mock_store.save_local = MagicMock()

        with patch("app.helpers.vector_db.FAISS") as MockFAISS:
            MockFAISS.load_local.side_effect = Exception("no index")
            MockFAISS.from_documents.return_value = mock_store

            vdb.store_vectors("u1", "s1", self._make_docs(), self._mock_embeddings(), "doc.pdf")

        MockFAISS.from_documents.assert_called_once()
        mock_store.save_local.assert_called_once()

    def test_store_vectors_appends_to_existing_index(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u2")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        mock_store = MagicMock()
        mock_store.add_documents = MagicMock()
        mock_store.save_local    = MagicMock()

        with patch("app.helpers.vector_db.FAISS") as MockFAISS:
            MockFAISS.load_local.return_value = mock_store

            vdb.store_vectors("u2", "s1", self._make_docs(), self._mock_embeddings(), "doc.pdf")

        mock_store.add_documents.assert_called_once()
        mock_store.save_local.assert_called_once()

    def test_store_vectors_injects_user_and_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        captured_docs = []

        def capture_from_docs(documents, embedding):
            captured_docs.extend(documents)
            store = MagicMock()
            store.save_local = MagicMock()
            return store

        with patch("app.helpers.vector_db.FAISS") as MockFAISS:
            MockFAISS.load_local.side_effect = Exception("no index")
            MockFAISS.from_documents.side_effect = capture_from_docs

            vdb.store_vectors("myuser", "mysess", self._make_docs(), self._mock_embeddings(), "f.pdf")

        assert all(d.metadata["user_id"]    == "myuser" for d in captured_docs)
        assert all(d.metadata["session_id"] == "mysess" for d in captured_docs)


    def test_load_vector_store_raises_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        with pytest.raises(FileNotFoundError, match="Index not found"):
            vdb.load_vector_store("ghost_user", self._mock_embeddings())

    def test_load_vector_store_returns_store_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u3")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        mock_store = MagicMock()
        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            result = vdb.load_vector_store("u3", self._mock_embeddings())

        assert result is mock_store

    def test_vector_search_returns_empty_when_no_index(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        result = vdb.vector_search("no_user", "sess", "query", self._mock_embeddings())
        assert result == []

    def test_vector_search_returns_top_k(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u4")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        fake_docs = [
            Document(page_content=f"result {i}", metadata={"session_id": "s1"})
            for i in range(5)
        ]
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = fake_docs

        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            result = vdb.vector_search("u4", "s1", "query", self._mock_embeddings(), top_k=3)

        assert len(result) == 3

    def test_vector_search_result_shape(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u5")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = [
            Document(page_content="answer text", metadata={"session_id": "s", "file_name": "f.pdf"})
        ]

        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            result = vdb.vector_search("u5", "s", "q", self._mock_embeddings(), top_k=1)

        assert "text"     in result[0]
        assert "metadata" in result[0]
        assert result[0]["text"] == "answer text"

    def test_vector_search_single_target_file_filter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u6")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []
        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            vdb.vector_search("u6", "s", "q", self._mock_embeddings(), target_files=["only.pdf"])

        _, kwargs = mock_store.similarity_search.call_args
        assert kwargs["filter"]["file_name"] == "only.pdf"

    def test_vector_search_multi_target_file_filter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u7")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []
        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            vdb.vector_search("u7", "s", "q", self._mock_embeddings(), target_files=["a.pdf", "b.pdf"])

        _, kwargs = mock_store.similarity_search.call_args
        assert "$in" in kwargs["filter"]["file_name"]

    def test_delete_session_vectors_no_index_is_noop(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))
        vdb.delete_session_vectors("ghost", "sess", self._mock_embeddings())

    def test_delete_session_vectors_removes_matching_docs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u8")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        keep_doc   = Document(page_content="keep",   metadata={"session_id": "other"})
        delete_doc = Document(page_content="delete", metadata={"session_id": "target"})

        mock_store = MagicMock()
        mock_store.docstore._dict = {"k1": keep_doc, "k2": delete_doc}

        saved_docs = []

        def capture_save(docs, emb):
            saved_docs.extend(docs)
            s = MagicMock()
            s.save_local = MagicMock()
            return s

        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store), \
             patch("app.helpers.vector_db.FAISS.from_documents", side_effect=capture_save):
            vdb.delete_session_vectors("u8", "target", self._mock_embeddings())

        texts = [d.page_content for d in saved_docs]
        assert "keep"   in texts
        assert "delete" not in texts

    def test_delete_session_vectors_removes_dir_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("u9")
        os.makedirs(index_path, exist_ok=True)
        open(os.path.join(index_path, "index.faiss"), "w").close()

        only_doc = Document(page_content="gone", metadata={"session_id": "target"})

        mock_store = MagicMock()
        mock_store.docstore._dict = {"k1": only_doc}

        with patch("app.helpers.vector_db.FAISS.load_local", return_value=mock_store):
            vdb.delete_session_vectors("u9", "target", self._mock_embeddings())

        assert not os.path.exists(index_path)

    def test_delete_user_vectors_removes_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))

        index_path = vdb.get_user_index_path("del_user")
        os.makedirs(index_path, exist_ok=True)

        vdb.delete_user_vectors("del_user")
        assert not os.path.exists(index_path)

    def test_delete_user_vectors_noop_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vdb, "FAISS_BASE_PATH", str(tmp_path / "faiss"))
        vdb.delete_user_vectors("no_such_user")


class TestWhisperProcessor:
    def _make_segment(self, text: str, start: float = 0.0, end: float = 1.0) -> dict:
        return {"text": text, "start": start, "end": end}

    def test_process_transcript_returns_list(self):
        segments = [self._make_segment("Hello world", 0, 1)]
        result = process_transcript(segments, source="audio.mp3")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_process_transcript_metadata_fields(self):
        segments = [self._make_segment("Test segment", 0.5, 2.5)]
        chunks = process_transcript(segments, source="test.mp3")

        meta = chunks[0].metadata
        assert meta["source"]        == "test.mp3"
        assert meta["chunk_method"]  == "WhisperProcessor"
        assert meta["start_time"]    == 0.5
        assert meta["end_time"]      == 2.5
        assert "char_count" in meta

    def test_process_transcript_chunk_indices_sequential(self):
        segments = [self._make_segment(f"Segment {i} " * 10, i, i + 1) for i in range(5)]
        chunks = process_transcript(segments, source="audio.mp3")

        chunk_indices = [c.metadata["chunk_index"] for c in chunks]
        assert chunk_indices == sorted(chunk_indices)

    def test_process_transcript_empty_segments(self):
        result = process_transcript([], source="audio.mp3")
        assert result == []


class TestWhisperTranscriber:
    def _make_utterance(self, text: str, start: float, end: float):
        utt = MagicMock()
        utt.transcript = text
        utt.start      = start
        utt.end        = end
        return utt


    def test_merge_utterances_basic(self):
        utts = [self._make_utterance("one two three", 0, 1)]
        result = merge_utterances(utts, max_words=10)
        assert len(result) == 1
        assert result[0]["text"] == "one two three"

    def test_merge_utterances_splits_on_max_words(self):
        utts = [
            self._make_utterance("one two three four five",   0, 1),
            self._make_utterance("six seven eight nine ten", 1, 2),
        ]
        result = merge_utterances(utts, max_words=5)
        assert len(result) >= 2

    def test_merge_utterances_preserves_timestamps(self):
        utts = [self._make_utterance("hello world", 10.5, 13.2)]
        result = merge_utterances(utts, max_words=20)
        assert result[0]["start"] == 10.5
        assert result[0]["end"]   == 13.2

    def test_merge_utterances_empty_returns_empty(self):
        assert merge_utterances([], max_words=10) == []

    def test_merge_utterances_chunk_has_required_keys(self):
        utts = [self._make_utterance("test content", 0, 5)]
        result = merge_utterances(utts, max_words=10)
        for chunk in result:
            assert "start" in chunk
            assert "end"   in chunk
            assert "text"  in chunk


    def test_find_exact_timestamp_found(self):
        utts = [
            {"start": 5.0,  "end": 8.0,  "text": "Hello world"},
            {"start": 10.0, "end": 15.0, "text": "Introduction to Python"},
        ]
        result = find_exact_timestamp(utts, "python")
        assert result == 10.0

    def test_find_exact_timestamp_case_insensitive(self):
        utts = [{"start": 3.0, "end": 6.0, "text": "MACHINE LEARNING basics"}]
        assert find_exact_timestamp(utts, "machine learning") == 3.0

    def test_find_exact_timestamp_not_found_returns_none(self):
        utts = [{"start": 0.0, "end": 1.0, "text": "nothing relevant"}]
        assert find_exact_timestamp(utts, "quantum physics") is None

    def test_find_exact_timestamp_empty_list_returns_none(self):
        assert find_exact_timestamp([], "anything") is None

    def test_transcribe_audio_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="File not found"):
            transcribe_audio("/nonexistent/audio.mp3")

    def test_transcribe_audio_returns_expected_shape(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake mp3 data")

        fake_utt = self._make_utterance("hello world", 0, 2)
        fake_alt = MagicMock()
        fake_alt.transcript = "hello world"

        fake_response             = MagicMock()
        fake_response.results.channels[0].alternatives[0] = fake_alt
        fake_response.results.utterances = [fake_utt]

        with patch("app.helpers.whisper_transcriber.deepgram") as mock_dg:
            mock_dg.listen.rest.v.return_value.transcribe_file.return_value = fake_response
            from app.helpers.whisper_transcriber import transcribe_audio
            result = transcribe_audio(str(audio))

        assert "full_text"   in result
        assert "rag_chunks"  in result
        assert "utterances"  in result

    def test_transcribe_audio_converts_video_first(self, tmp_path):
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"fake video")
        converted_audio = str(tmp_path / "converted.mp3")

        fake_utt = self._make_utterance("converted audio", 0, 3)
        fake_alt = MagicMock()
        fake_alt.transcript = "converted audio"

        fake_response             = MagicMock()
        fake_response.results.channels[0].alternatives[0] = fake_alt
        fake_response.results.utterances = [fake_utt]

        open(converted_audio, "wb").close()

        with patch(
            "app.helpers.whisper_transcriber.convert_video_to_audio",
            return_value=converted_audio
        ) as mock_convert, patch(
            "app.helpers.whisper_transcriber.deepgram"
        ) as mock_dg:
            mock_dg.listen.rest.v.return_value.transcribe_file.return_value = fake_response
            transcribe_audio(str(video))

        mock_convert.assert_called_once_with(str(video))

    def test_transcribe_audio_raw_utterances_shape(self, tmp_path):
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"wav data")

        fake_utt   = self._make_utterance("segment one", 1.0, 4.0)
        fake_alt   = MagicMock()
        fake_alt.transcript = "segment one"

        fake_response = MagicMock()
        fake_response.results.channels[0].alternatives[0] = fake_alt
        fake_response.results.utterances = [fake_utt]

        with patch("app.helpers.whisper_transcriber.deepgram") as mock_dg:
            mock_dg.listen.rest.v.return_value.transcribe_file.return_value = fake_response
            from app.helpers.whisper_transcriber import transcribe_audio
            result = transcribe_audio(str(audio))

        for utt in result["utterances"]:
            assert "start" in utt
            assert "end"   in utt
            assert "text"  in utt


class TestSummarizer:
    def test_count_tokens_returns_int(self):
        assert isinstance(count_tokens("hello world"), int)

    def test_count_tokens_empty_string(self):
        assert count_tokens("") == 0

    def test_count_tokens_scales_with_length(self):
        short = count_tokens("hello")
        long  = count_tokens("hello " * 100)
        assert long > short

    @pytest.mark.asyncio
    async def test_summarize_text_returns_content(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="This is a summary.")

        result = await _summarize_text(fake_llm, "Some long document content.", label="doc")

        assert result == "This is a summary."
        fake_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_text_prompt_includes_content(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="ok")

        await _summarize_text(fake_llm, "My unique content string 12345")

        prompt = fake_llm.ainvoke.call_args[0][0]
        assert "My unique content string 12345" in prompt

    @pytest.mark.asyncio
    async def test_summarize_large_doc_single_batch(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="batch summary")

        chunk = MagicMock()
        chunk.text = "short chunk"

        doc = MagicMock()
        doc.chunks = [chunk]

        result = await _summarize_large_doc(fake_llm, doc)

        assert fake_llm.ainvoke.call_count == 1
        assert result == "batch summary"

    @pytest.mark.asyncio
    async def test_summarize_large_doc_deduplicates_overlapping_chunks(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="deduped summary")

        words = "alpha beta gamma delta epsilon"
        chunk_a = MagicMock(); chunk_a.text = words
        chunk_b = MagicMock(); chunk_b.text = words

        doc = MagicMock()
        doc.chunks = [chunk_a, chunk_b]

        result = await _summarize_large_doc(fake_llm, doc)

        assert fake_llm.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_summarize_large_doc_combine_pass_for_multiple_batches(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.side_effect = [
            MagicMock(content="summary batch 1"),
            MagicMock(content="summary batch 2"),
            MagicMock(content="final combined"),  # combine pass
        ]

        words_needed = CHUNK_BATCH_TOKEN_LIMIT + 100

        chunk_a = MagicMock()
        chunk_a.text = "apple " * words_needed

        chunk_b = MagicMock()
        chunk_b.text = "banana " * words_needed

        doc = MagicMock()
        doc.chunks = [chunk_a, chunk_b]

        result = await _summarize_large_doc(fake_llm, doc)

        assert fake_llm.ainvoke.call_count == 3
        assert result == "final combined"

    @pytest.mark.asyncio
    async def test_generate_session_summary_skips_empty_doc(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="x")

        doc = MagicMock()
        doc.full_text = ""
        doc.chunks    = []
        doc.file_name = "empty.pdf"
        doc.save      = AsyncMock()

        await generate_session_summary("sess1", [doc], fake_llm)

        fake_llm.ainvoke.assert_not_called()
        doc.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_session_summary_saves_summary(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="The summary.")

        doc = MagicMock()
        doc.full_text = "short doc content"
        doc.chunks    = []
        doc.file_name = "doc.pdf"
        doc.save      = AsyncMock()

        await generate_session_summary("sess1", [doc], fake_llm)

        assert doc.summary == "The summary."
        doc.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_session_summary_uses_chunk_path_for_large_doc(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="large doc summary")

        big_text = "word " * (DIRECT_TOKEN_THRESHOLD + 500)

        chunk = MagicMock()
        chunk.text = "some chunk text"

        doc = MagicMock()
        doc.full_text = big_text
        doc.chunks    = [chunk]
        doc.file_name = "large.pdf"
        doc.save      = AsyncMock()

        with patch(
            "app.helpers.summarizer._summarize_large_doc",
            new=AsyncMock(return_value="large doc summary")
        ) as mock_large:
            await generate_session_summary("sess2", [doc], fake_llm)

        mock_large.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_session_summary_processes_all_docs(self):
        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = MagicMock(content="summary")

        docs = []
        for i in range(3):
            d = MagicMock()
            d.full_text = f"content {i}"
            d.chunks    = []
            d.file_name = f"doc{i}.pdf"
            d.save      = AsyncMock()
            docs.append(d)

        await generate_session_summary("sess3", docs, fake_llm)

        for d in docs:
            d.save.assert_called_once()