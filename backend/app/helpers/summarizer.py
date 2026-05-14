import tiktoken
from app.models.session_document import SessionDocument

# Token thresholds
DIRECT_TOKEN_THRESHOLD   = 6_000   # below this → send full_text in one call
CHUNK_BATCH_TOKEN_LIMIT  = 3_000   # max tokens per batch when chunking large docs

# cl100k_base is close enough to Gemini's tokenizer for safety thresholds
_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Fast local token count — no API call needed."""
    return len(_encoder.encode(text))


# Single summarize call
async def _summarize_text(llm, content: str, label: str = "content") -> str:
    prompt = f"""You are a precise document analyst.

Summarize the following {label} in detail.
Rules:
- Preserve ALL important facts, numbers, dates, names, and key points.
- Keep technical terms as-is.
- Write in clear, structured sentences.
- If the content has lists or steps, preserve their structure.
- Do not add anything not present in the content.

Content:
{content}

Detailed Summary:"""

    response = await llm.ainvoke(prompt)
    return response.content


# Dynamic-batch summarize for large docs
async def _summarize_large_doc(llm, doc) -> str:
    chunks = doc.chunks

    # Deduplicate overlapping chunks
    deduped = [chunks[0]] if chunks else []
    skipped = 0

    for i in range(1, len(chunks)):
        prev_words = set(chunks[i - 1].text.split())
        curr_words = set(chunks[i].text.split())
        overlap_ratio = len(curr_words & prev_words) / max(len(curr_words), 1)

        if overlap_ratio >= 0.6:
            skipped += 1
            # print(f"    [dedup] Chunk {i} skipped — {overlap_ratio:.0%} overlap with previous")
        else:
            deduped.append(chunks[i])

    # print(f"  [dedup] {len(chunks)} chunks → {len(deduped)} kept, {skipped} skipped")

    # Group into token-aware batches
    batches        = []
    current_batch  = []
    current_tokens = 0

    for chunk in deduped:
        chunk_tokens = count_tokens(chunk.text)

        if current_tokens + chunk_tokens > CHUNK_BATCH_TOKEN_LIMIT and current_batch:
            batches.append(current_batch)
            current_batch  = [chunk]
            current_tokens = chunk_tokens
        else:
            current_batch.append(chunk)
            current_tokens += chunk_tokens

    if current_batch:
        batches.append(current_batch)

    # print(f"  [batch] {len(deduped)} deduped chunks → {len(batches)} token-aware batch(es)")

    # Summarize each batch
    batch_summaries = []

    for idx, batch in enumerate(batches):
        combined     = "\n\n".join(chunk.text for chunk in batch)
        batch_tokens = count_tokens(combined)
        # print(f"  [llm-call] Batch {idx + 1}/{len(batches)} → {len(batch)} chunk(s), {batch_tokens} tokens")

        summary = await _summarize_text(
            llm,
            combined,
            label=f"content section (batch {idx + 1})"
        )
        batch_summaries.append(summary)

    # Combine batch summaries if more than one
    if len(batch_summaries) == 1:
        # print(f"  [combine] Single batch — no combine pass needed")
        return batch_summaries[0]

    # print(f"  [combine] Merging {len(batch_summaries)} batch summaries into final summary")

    combined_summaries = "\n\n---\n\n".join(batch_summaries)
    combine_prompt = f"""Combine these section summaries into one coherent, complete summary.
Rules:
- Merge duplicate or overlapping information.
- Preserve ALL facts, numbers, dates, names, and key points.
- Maintain logical flow.
- Do not add anything not present below.

Section Summaries:
{combined_summaries}

Final Summary:"""

    response = await llm.ainvoke(combine_prompt)
    return response.content


# Main entry point 
async def generate_session_summary(session_id: str, docs, llm):

    # print(f"\n{'='*60}")
    # print(f"[summarizer] Starting — session: {session_id}")
    # print(f"[summarizer] Total docs to process: {len(docs)}")
    # print(f"{'='*60}")

    for doc_idx, doc in enumerate(docs, start=1):

        file_name  = doc.file_name
        full_text  = doc.full_text or ""
        token_count = count_tokens(full_text) if full_text else 0

        # print(f"\n[doc {doc_idx}/{len(docs)}] {file_name}")
        # print(f"  full_text : {len(full_text):,} chars / {token_count:,} tokens")
        # print(f"  chunks    : {len(doc.chunks)}")

        # Guard: nothing to summarize 
        if not full_text and not doc.chunks:
            # print(f"  [skip] No content available — skipping")
            continue

        # Strategy A: full_text fits → single LLM call, zero overlap risk 
        if token_count <= DIRECT_TOKEN_THRESHOLD:
            content = full_text or "\n\n".join(chunk.text for chunk in doc.chunks)
            actual_tokens = count_tokens(content)

            # print(f"  [strategy] FULL-TEXT path ({actual_tokens} tokens ≤ {DIRECT_TOKEN_THRESHOLD} threshold)")
            # print(f"  [llm-call] 1 call for entire document")

            doc_summary = await _summarize_text(
                llm,
                content,
                label=f"document '{file_name}'"
            )

        # Strategy B: large doc → dedup + token-aware chunk batches
        else:
            # print(f"  [strategy] CHUNK path ({token_count} tokens > {DIRECT_TOKEN_THRESHOLD} threshold)")
            doc_summary = await _summarize_large_doc(llm, doc)

        # Save per-doc summary
        doc.summary = doc_summary
        await doc.save()

        preview = doc_summary[:120].replace("\n", " ")
        # print(f"  [saved] Summary saved for '{file_name}'")
        # print(f"  [preview] {preview}...")

    # print(f"\n{'='*60}")
    # print(f"[summarizer] Done — {len(docs)} doc(s) processed for session {session_id}")
    # print(f"{'='*60}\n")