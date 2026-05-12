from beanie import Document, Indexed, PydanticObjectId 
from datetime import datetime, timezone
from typing import Annotated
from pydantic import Field


class RefreshToken(Document):
    user_id: Annotated[PydanticObjectId, Indexed()]
    token_hash: Annotated[str, Indexed(unique=True)]
    jti: Annotated[str, Indexed(unique=True)]
    expires_at: datetime = Field(..., index=True)
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "refresh_tokens"