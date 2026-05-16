from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import json
import os

load_dotenv()   


INPUT_COST  = 0.30  / 1_000_000
OUTPUT_COST = 2.50  / 1_000_000 


def get_openai_llm():
    return init_chat_model("openai:gpt-4o-mini", temperature=0, stream_usage=True)

def get_google_llm_lite():
    return init_chat_model(
        "gemini-2.5-flash-lite",
        model_provider="google_vertexai",
        temperature=0,
        streaming=True
    )

def get_google_llm():
    return init_chat_model(
        "gemini-2.5-flash",
        model_provider="google_vertexai",
        temperature=0,
        streaming=True,
    )


