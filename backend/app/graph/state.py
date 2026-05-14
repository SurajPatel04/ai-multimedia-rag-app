from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class State(BaseModel):

    query: str
    session_id: str
    summary: str = ""
    context: str = ""
    title: str = ""   

    chat_history: List[BaseMessage] = Field(
        default_factory=list
    )  # stores [HumanMessage, AIMessage, HumanMessage, AIMessage ...]

    messages: List[BaseMessage] = Field(
        default_factory=list
    )


    extra_query: Optional[List[str]] = Field(
        default_factory=list
    )
    target_files: Optional[List[str]] = None
    message_index: int = 0

    mode: Optional[
        Literal[
            "vector_search",
            "mongo_db_retrieve",
            "direct_llm"
        ]
    ] = None

    response: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True  # needed for LangChain message types