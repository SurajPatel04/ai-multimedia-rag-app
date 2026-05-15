from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import json
import os

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

llm = init_chat_model("openai:gpt-4o-mini", temperature=0, stream_usage=True)
google_llm_lite = init_chat_model(
    "gemini-2.5-flash-lite",
    model_provider="google_vertexai",
    temperature=0,
    streaming=True
)

google_llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_vertexai",
    temperature=0,
    streaming=True,
)

INPUT_COST  = 0.30  / 1_000_000
OUTPUT_COST = 2.50  / 1_000_000 
