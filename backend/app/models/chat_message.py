from beanie import Document, PydanticObjectId, Indexed
from pydantic import Field
from typing import Optional, Literal
from datetime import datetime, timezone


class ChatMessage(Document):

    # -------------------------
    # Identity
    # -------------------------
    session_id: str
    user_id: PydanticObjectId

    # -------------------------
    # Message Info
    # -------------------------
    role: Literal["human", "ai"]
    content: str

    # -------------------------
    # Token Usage
    # -------------------------
    prompt_tokens:     Optional[int]   = None
    completion_tokens: Optional[int]   = None
    total_tokens:      Optional[int]   = None
    total_cost:        Optional[float] = None

    # -------------------------
    # Order tracking
    # -------------------------
    message_index: int = 0                        # ✅ 1, 2, 3, 4... per session

    created_at: Indexed(datetime) = Field(        # ✅ indexed for fast sort
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "chat_messages"
        indexes = [
            [("session_id", 1), ("created_at", 1)],   # ✅ compound index
            [("session_id", 1), ("message_index", 1)]
        ]