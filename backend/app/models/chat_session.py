from beanie import Document, PydanticObjectId, Indexed, before_event, Replace, Update
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class ChatSession(Document):
    session_id: Indexed(str, unique=True)
    user_id: Indexed(PydanticObjectId)

    title: Optional[str] = None
    is_active: bool = True

    message_count: int = 0
    last_message_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Replace, Update])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "chat_sessions"