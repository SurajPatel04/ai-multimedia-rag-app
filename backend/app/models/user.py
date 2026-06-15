from beanie import Document, Indexed, Replace, Update, before_event
from pydantic import Field, EmailStr
from typing import Optional, Annotated, Literal
from datetime import datetime, timezone

class User(Document):
    first_name: str
    last_name: Optional[str] = None
    email: Annotated[EmailStr, Indexed(unique=True)]
    password: Optional[str] = Field(default=None)
    auth_provider: Literal["local", "google"] = Field(default="local")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



    @before_event([Replace, Update])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)


    class Settings:
        name = "users"
