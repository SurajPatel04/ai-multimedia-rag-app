from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class QueryRouterState(BaseModel):
    extra_query: Optional[List[str]] = None

    target_files: Optional[List[str]] = None

    should_cache: bool = False

    mode: Literal[
            "vector_search",
            "mongo_db_retrieve",
            "direct_llm"
        ]


class MediaReference(BaseModel):
    file_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class AnswerSchema(BaseModel):
    answer: str

    media_references: Optional[
        List[MediaReference]
    ] = None

class TitleGenerationSchema(BaseModel):
    title: str