from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class ChatSession(Document):
    session_id: str                        # links to LangGraph thread_id
    user_id: PydanticObjectId             # which user owns this session

    title: Optional[str] = None
    is_active: bool = True
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "chat_sessions"