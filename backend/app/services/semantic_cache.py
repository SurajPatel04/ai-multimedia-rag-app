import json
import asyncio
import numpy as np
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)


def cosine_similarity(vec1, vec2) -> float:
    a, b = np.array(vec1), np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_file_fingerprint(target_files: list | None) -> str:
    if not target_files:
        return "no_files"
    return str(abs(hash(tuple(sorted(target_files)))))


async def _embed_with_retry(embedder, text: str, max_retries: int = 3) -> list | None:
    for attempt in range(1, max_retries + 1):
        try:
            return await embedder.aembed_query(text)
        except Exception as e:
            error_str = str(e).lower()
            is_quota  = "429" in error_str or "resource_exhausted" in error_str or "rate" in error_str

            if is_quota and attempt < max_retries:
                wait = 2.0 * attempt
                print(f"[semantic_cache] Quota hit, retrying in {wait}s ({attempt}/{max_retries})")
                await asyncio.sleep(wait)
                continue

            print(f"[semantic_cache] Embed failed after {attempt} attempts: {e}")
            return None


async def get_semantic_cache( session_id: str, query: str, embedder, target_files: list = None, threshold: float = 0.90 ):
    try:
        query_embedding = await _embed_with_retry(embedder, query)
        if not query_embedding:
            return None

        file_fingerprint = get_file_fingerprint(target_files)
        pattern          = f"rag_cache:{session_id}:{file_fingerprint}:*"
        keys             = await redis_client.keys(pattern)

        for key in keys:
            cached_data = await redis_client.get(key)
            if not cached_data:
                continue

            cached     = json.loads(cached_data)
            similarity = cosine_similarity(query_embedding, cached["embedding"])

            if similarity >= threshold:
                print(f"[semantic_cache] Cache hit — similarity: {similarity:.4f} | files: {target_files}")
                return cached["response"]

        return None

    except Exception as e:
        print(f"[semantic_cache] get error: {e}")
        return None


async def set_semantic_cache( session_id: str, query: str, response: str, embedder, target_files: list = None ):
    try:
        query_embedding = await _embed_with_retry(embedder, query)
        if not query_embedding:
            return

        file_fingerprint = get_file_fingerprint(target_files)
        cache_key        = f"rag_cache:{session_id}:{file_fingerprint}:{query.strip().lower()[:50]}"

        await redis_client.setex(
            cache_key,
            7200,
            json.dumps({
                "query":        query,
                "embedding":    query_embedding,
                "response":     response,
                "target_files": target_files or []
            })
        )
        print(f"[semantic_cache] Stored | session: {session_id} | files: {target_files}")

    except Exception as e:
        print(f"[semantic_cache] set error: {e}")


async def invalidate_session_cache(session_id: str):
    try:
        keys = await redis_client.keys(f"rag_cache:{session_id}:*")
        if keys:
            await redis_client.delete(*keys)
            print(f"[semantic_cache] Invalidated {len(keys)} keys for session: {session_id}")
    except Exception as e:
        print(f"[semantic_cache] invalidate error: {e}")