from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class QueryRouterState(BaseModel):
    extra_query: Optional[List[str]] = None

    mongo_db_target_files: Optional[List[str]] = None

    mode: Literal[
            "vector_search",
            "mongo_db_retrieve",
            "direct_llm"
        ]