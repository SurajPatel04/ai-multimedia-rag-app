import json
from app.utils.llm import llm, INPUT_COST, OUTPUT_COST


def stream_response(query: str, llm):
    full_response = ""

    for chunk in llm.stream(query):
        if chunk.content:
            full_response += chunk.content
            yield f"data: {json.dumps({'type': 'text', 'data': chunk.content})}\n\n"

        if chunk.usage_metadata:
            prompt_tokens     = chunk.usage_metadata["input_tokens"]
            completion_tokens = chunk.usage_metadata["output_tokens"]
            total_tokens      = prompt_tokens + completion_tokens
            total_cost        = (prompt_tokens * INPUT_COST) + (completion_tokens * OUTPUT_COST)

            yield f"data: {json.dumps({
                'type':              'usage',
                'full_response':     full_response,
                'prompt_tokens':     prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens':      total_tokens,
                'total_cost':        round(total_cost, 6),
            })}\n\n"

    yield "data: [DONE]\n\n"