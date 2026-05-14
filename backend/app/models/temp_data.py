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
    start: Optional[float] = None   # timestamp start
    end: Optional[float] = None     # timestamp end


class ContentChunk(BaseModel):
    chunk_index: int
    text: str
    metadata: ChunkMetadata


class Utterance(BaseModel):
    start: float
    end: float
    text: str


class TempData(Document):
    temp_id: str 
    user_id: PydanticObjectId
    file_url: str
    file_name: str
    file_type: str 
    content_type: str
    full_text: Optional[str] = None 
    utterances: List[Utterance] = []
    chunks: List[ContentChunk] = [] 
    embedded: bool = False  
    status: str = "processing"             # "processing" | "ready" | "error"
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "temp_data"