from app.graph.state import State
from app.helpers.vector_db import vector_search
from app.utils.embeddings import get_embeddings

embeddings = get_embeddings()

async def vector_search_node(state: State):

    print("----- VECTOR SEARCH NODE -----")

    queries = [
        state.query,
        *(state.extra_query or [])
    ]

    all_results = []

    for query in queries:
        results = vector_search(
            session_id=state.session_id,
            query=query,
            embeddings=embeddings,
            top_k=3
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

    return {
        "context": context
    }