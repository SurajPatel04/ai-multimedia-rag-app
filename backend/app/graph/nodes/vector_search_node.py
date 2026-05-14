from app.graph.state import State
from app.helpers.vector_db import vector_search
from app.utils.embeddings import get_embeddings

embeddings = get_embeddings()

async def vector_search_node(state: State):
    print("----- VECTOR SEARCH NODE -----")

    queries = [state.query, *(state.extra_query or [])]
    all_results = []

    for query in queries:
        results = vector_search(
            user_id      = state.user_id,
            session_id   = state.session_id,
            query        = query,
            embeddings   = embeddings,
            top_k        = 3,
            target_files = state.target_files
        )
        print(f"  [vector] query='{query[:50]}' → {len(results)} results")  # ✅ always prints
        all_results.extend(results)

    print(f"  [vector] total results: {len(all_results)}")  # ✅ always prints

    if not all_results:
        print(f"  [vector] ❌ NO RESULTS — FAISS empty or index missing for session: {state.session_id}")
        return {"context": "No relevant content found for your query.", "media_refs": None}

    unique_results = {r["text"]: r for r in all_results}
    context = "\n\n---\n\n".join(r["text"] for r in unique_results.values())

    media_refs = []
    for r in unique_results.values():
        meta  = r.get("metadata", {})
        start = meta.get("start")
        end   = meta.get("end")
        if start is not None and end is not None:
            media_refs.append({
                "start":     float(start),
                "end":       float(end),
                "file_name": meta.get("file_name", ""),
                "text":      r["text"][:80]
            })

    media_refs = sorted(media_refs, key=lambda x: x["start"]) if media_refs else None

    print(f"  [vector] ✅ context length: {len(context)}")
    print(f"  [vector] context preview: {context[:150]}")
    print(f"  [vector] media_refs: {len(media_refs) if media_refs else 0} timestamp(s)")

    return {
        "context":    context,
        "media_refs": media_refs
    }

    print("----- VECTOR SEARCH NODE -----")

    queries = [
        state.query,
        *(state.extra_query or [])
    ]

    all_results = []

    for query in queries:
        results = vector_search(
            user_id=state.user_id,
            session_id=state.session_id,
            query=query,
            embeddings=embeddings,
            top_k=3,
            target_files=state.target_files
        )
        all_results.extend(results)

    if not all_results:
        return {
            "context": "No relevant content found for your query."
        }

    unique_results = {
        r["text"]: r
        for r in all_results
    }

    context = "\n\n---\n\n".join(
        r["text"]
        for r in unique_results.values()
    )

    print("--------vector-------------", context)
    return {
        "context": context
    }