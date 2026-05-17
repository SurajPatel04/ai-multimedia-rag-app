from app.graph.state import State
from app.utils.embeddings import get_embeddings
from app.services.semantic_cache import get_semantic_cache

embedding = get_embeddings()

async def semantic_cache_check_node(state: State):
    try:
        if state.mode == "direct_llm" or state.skip_cache:
            return {"cache_hit": False, "cached_response": None}
        cached = await get_semantic_cache(
            session_id   = state.session_id,
            query        = state.query,
            embedder     = embedding,
            target_files = state.target_files
        )

        if cached:
            print(f"[cache_node] HIT | session: {state.session_id} | files: {state.target_files}")
            return {"cache_hit": True, "cached_response": cached}

        print(f"[cache_node] MISS | session: {state.session_id} | files: {state.target_files}")
        return {"cache_hit": False, "cached_response": None}

    except Exception as e:
        print(f"[cache_node] Error: {e}")
        return {"cache_hit": False, "cached_response": None}