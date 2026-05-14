from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import json
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

llm = init_chat_model("openai:gpt-4o-mini", temperature=0, stream_usage=True)
google_llm_lite = init_chat_model(
    "gemini-2.5-flash-lite",
    model_provider="google_genai",
    temperature=0,
    streaming=True
)

google_llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai",
    temperature=0,
    streaming=True,
)

INPUT_COST  = 0.150 / 1_000_000
OUTPUT_COST = 0.600 / 1_000_000


# def stream_response(query: str):
#     full_response = ""

#     for chunk in llm.stream(query):
#         if chunk.content:
#             full_response += chunk.content
#             yield {"type": "text", "data": chunk.content}

#         if chunk.usage_metadata:
#             prompt_tokens     = chunk.usage_metadata["input_tokens"]
#             completion_tokens = chunk.usage_metadata["output_tokens"]
#             total_tokens      = prompt_tokens + completion_tokens
#             total_cost        = (prompt_tokens * INPUT_COST) + (completion_tokens * OUTPUT_COST)

#             yield {
#                 "type":             "usage",
#                 "full_response":    full_response,
#                 "prompt_tokens":    prompt_tokens,
#                 "completion_tokens":completion_tokens,
#                 "total_tokens":     total_tokens,
#                 "total_cost":       round(total_cost, 6),
#             }


# # ── Usage example (run this file directly to test) ─────────────────────
# if __name__ == "__main__":
#     from app.services.llm_response_stream import stream_response
#     for chunk in stream_response("FastAPI", llm):
#         print(chunk)