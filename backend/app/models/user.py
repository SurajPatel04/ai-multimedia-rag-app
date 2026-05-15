from beanie import Document, Indexed, Replace, Update, before_event
from pydantic import Field, EmailStr
from typing import Optional, Annotated
from datetime import datetime, timezone

class User(Document):
    first_name: str
    last_name: Optional[str] = None
    email: Annotated[EmailStr, Indexed(unique=True)]
    password: str = Field(min_length=8)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



    @before_event([Replace, Update])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)


    class Settings:
        name = "users"
