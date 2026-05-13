from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

class ChunkMetadata(BaseModel):
    # PDF metadata
    page: Optional[int] = None
    total_pages: Optional[int] = None
    chunk_method: Optional[str] = None
    char_count: Optional[int] = None
    source: Optional[str] = None
    # audio/video metadata
    start: Optional[float] = None
    end: Optional[float] = None 

class ContentChunk(BaseModel):
    chunk_index: int
    text: str
    metadata: ChunkMetadata


class Utterance(BaseModel):
    start: float
    end: float
    text: str

class SessionDocument(Document):

    session_id: str
    user_id: PydanticObjectId

    file_name: str
    file_url: str
    file_type: str
    content_type: str

    full_text: Optional[str] = None
    utterances: List[Utterance] = []

    chunks: List[ContentChunk] = []
    summary: Optional[str] = None
    embedded: bool = False

    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "session_documents"