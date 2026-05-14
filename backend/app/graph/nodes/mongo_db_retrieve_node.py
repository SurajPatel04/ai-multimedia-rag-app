from app.graph.state import State
from app.models.session_document import SessionDocument

MAX_CHARS = 8000  # ~2k tokens — safe for most LLM context windows

async def mongo_db_retrieve_node(state: State):

    print("----- MONGO DB RETRIEVE NODE -----")

    docs = await SessionDocument.find(
        SessionDocument.session_id == state.session_id
    ).to_list()

    if not docs:
        return {
            "context": "No uploaded documents found."
        }

    # ---------------------------------
    # If router selected target files
    # ---------------------------------

    if state.target_files:
        docs = [
            doc
            for doc in docs
            if doc.file_name in state.target_files
        ]

    if not docs:
        return {
            "context": "No matching documents found for the specified files."
        }

    # ---------------------------------
    # Build context
    # ---------------------------------

    context_parts = []

    for doc in docs:

        if doc.summary:
            content = doc.summary

        elif doc.full_text:
            # Truncate to avoid context window overflow
            if len(doc.full_text) > MAX_CHARS:
                content = doc.full_text[:MAX_CHARS] + "\n... [content truncated]"
            else:
                content = doc.full_text

        else:
            content = "No content available"

        context_parts.append(
            f"""
File Name: {doc.file_name}
File Type: {doc.file_type}
Content:
{content}
            """.strip()
        )

    context = "\n\n---\n\n".join(context_parts)

    return {
        "context": context
    }