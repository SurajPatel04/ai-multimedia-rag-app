import os
import uuid
from app.helpers.pdf_reader import process_pdf
from app.helpers.whisper_transcriber import transcribe_audio
from app.helpers.vector_db import store_vectors, delete_session_vectors
from app.utils.embeddings import get_embeddings
from app.utils.video_to_audio_converter import VIDEO_EXTENSIONS, convert_video_to_audio
from langchain_core.documents import Document as LangchainDocument

embeddings = get_embeddings()

AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac"}
PDF_EXTENSIONS = {"pdf"}


def generate_temp_id() -> str:
    return f"tmp_{uuid.uuid4().hex}"


def process_file(temp_id: str, file_path: str) -> dict:
    """
    Upload time — only transcribe/chunk
    NO vector DB yet — just return raw data for MongoDB
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext in PDF_EXTENSIONS:
        return _process_pdf_file(temp_id, file_path)

    elif ext in AUDIO_EXTENSIONS or ext in VIDEO_EXTENSIONS:
        return _process_audio_video_file(temp_id, file_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _process_pdf_file(temp_id: str, file_path: str) -> dict:
    print(f"Processing PDF: {file_path}")

    langchain_chunks = process_pdf(file_path)

    # convert to raw dicts for MongoDB storage
    chunks = [
        {
            "chunk_index": i,
            "text": chunk.page_content,
            "metadata": {
                "page": chunk.metadata.get("page"),
                "total_pages": chunk.metadata.get("total_pages"),
                "chunk_method": chunk.metadata.get("chunk_method"),
                "char_count": chunk.metadata.get("char_count"),
                "source": chunk.metadata.get("source"),
            }
        }
        for i, chunk in enumerate(langchain_chunks)
    ]

    return {
        "temp_id": temp_id,
        "file_type": "pdf",
        "full_text": " ".join(c["text"] for c in chunks),
        "utterances": [],
        "chunks": chunks,
        "embedded": False,
        "status": "ready"
    }


def _process_audio_video_file(temp_id: str, file_path: str) -> dict:
    print(f"Processing audio/video: {file_path}")

    result = transcribe_audio(file_path)

    # convert rag_chunks to raw dicts for MongoDB
    chunks = [
        {
            "chunk_index": i,
            "text": chunk["text"],
            "metadata": {
                "start": chunk["start"],
                "end": chunk["end"],
            }
        }
        for i, chunk in enumerate(result["rag_chunks"])
    ]

    return {
        "temp_id": temp_id,
        "file_type": "audio",
        "full_text": result["full_text"],
        "utterances": result["utterances"],   # sentence-level for exact timestamps
        "chunks": chunks,
        "embedded": False,
        "status": "ready"
    }


def embed_and_store(session_id: str, temp_id: str, chunks: list, file_type: str, file_name: str = ""):
    """
    First message time — embed chunks and store in FAISS
    """

    documents = []
    for chunk in chunks:
        # Normalize: handle both dict and Pydantic ContentChunk objects
        if hasattr(chunk, "model_dump"):
            chunk = chunk.model_dump()

        documents.append(
            LangchainDocument(
                page_content=chunk["text"],
                metadata={
                    **chunk["metadata"],
                    "chunk_index": chunk["chunk_index"],
                    "file_type": file_type,
                    "file_name": file_name,
                    "session_id": session_id,
                    "temp_id": temp_id
                }
            )
        )

    store_vectors(session_id, documents, embeddings)

    print(
        f"Embedded {len(documents)} chunks "
        f"for session: {session_id}"
    )

def replace_file(temp_id: str, new_file_path: str) -> dict:
    """
    User changed file before sending message
    MongoDB doc deleted by route handler
    No FAISS cleanup needed (not embedded yet)
    """
    print(f"Replacing file for temp: {temp_id}")
    return process_file(temp_id, new_file_path)