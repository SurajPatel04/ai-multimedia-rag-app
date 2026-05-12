from beanie import Document, Indexed, Replace, Update, before_event
from pydantic import Field, EmailStr
from typing import Optional, Annotated
from datetime import datetime, timezone

class User(Document):
    first_name: str
    last_name: Optional[str] = None
    email: Annotated[EmailStr, Indexed(unique=True)]
    password: str = Field(min_length=8)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


    @before_event([Replace, Update])
    def update_timestamp(self):
        self.updatedAt = datetime.now(timezone.utc)


    class Settings:
        name = "users"
