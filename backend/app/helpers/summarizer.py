from app.models.session_document import SessionDocument

async def generate_session_summary(session_id: str, docs, llm):

    chunk_summaries = []

    for doc in docs:
        for chunk in doc.chunks:

            response = await llm.ainvoke(
                f"""
You are a precise document analyst.

Summarize the following content chunk in detail.
Rules:
- Preserve ALL important facts, numbers, dates, names, and key points.
- Do not skip any important information.
- Keep technical terms as-is.
- Write in clear, structured sentences.
- If the content has lists or steps, preserve their structure.

Content:
{chunk.text}

Detailed Summary:
"""
            )

            chunk_summaries.append(response.content)

    # ✅ Combine all chunk summaries
    combined = "\n\n---\n\n".join(chunk_summaries)

    # ✅ Final summary from all chunk summaries
    final_response = await llm.ainvoke(
        f"""
You are a document summarization expert.

Below are detailed summaries of individual chunks from one or more uploaded files.
Your job is to combine them into one final, coherent, and complete summary.

Rules:
- Merge duplicate or overlapping information.
- Preserve ALL important facts, numbers, dates, names, and key points.
- Structure the summary clearly with logical flow.
- Do not add any information not present in the chunk summaries.
- If multiple files are present, summarize each file separately, then give an overall summary.

Chunk Summaries:
{combined}

Final Detailed Summary:
"""
    )

    # ✅ Save per doc summary + overall session summary
    for doc in docs:
        doc_chunk_text = "\n\n".join(
            chunk.text for chunk in doc.chunks
        )

        doc_summary_response = await llm.ainvoke(
            f"""
Summarize this document in detail.
Preserve all key facts, numbers, names, and important points.

Document: {doc.file_name}
Content:
{doc_chunk_text}

Detailed Summary:
"""
        )

        doc.summary = doc_summary_response.content
        await doc.save()                           # ✅ save per-doc summary

    # ✅ Save overall session summary
    session_doc = await SessionDocument.find_one(
        SessionDocument.session_id == session_id
    )

    if session_doc:
        session_doc.summary = final_response.content
        await session_doc.save()