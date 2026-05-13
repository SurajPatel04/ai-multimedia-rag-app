from app.models.chat_session import ChatSession
from app.models.session_document import SessionDocument

async def generate_session_summary(session_id: str, docs, llm):
    chunk_summaries = []
    for doc in docs:
        for chunk in doc.chunks:
            response = await llm.ainvoke(
                f"""
                Summarize this content briefly
                and preserve important details:

                {chunk.text}
                """
            )
            chunk_summaries.append(
                response.content
            )

    combined = "\n\n".join(chunk_summaries)
    final_response = await llm.ainvoke(
        f"""
        Generate a complete and coherent
        summary of these uploaded files:

        {combined}
        """
    )
    session_doc = await SessionDocument.find_one(
        SessionDocument.session_id == session_id
    )

    if session_doc:
        session_doc.summary = final_response.content
        await session_doc.save()