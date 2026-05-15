from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    temp_id: Optional[str] = None


class UpdateSessionTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)