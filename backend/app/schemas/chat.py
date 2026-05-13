from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    temp_id: Optional[str] = None
