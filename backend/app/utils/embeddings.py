from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import asyncio

load_dotenv()


def get_embeddings(max_retries: int = 3, delay: float = 2.0):
    for attempt in range(1, max_retries + 1):
        try:
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                dimensions=1536,
            )
        except Exception as e:
            error_str = str(e).lower()
            is_quota = "429" in error_str or "rate" in error_str

            if is_quota and attempt < max_retries:
                # print(f"[get_embeddings] Quota hit, retrying ({attempt}/{max_retries})")
                asyncio.sleep(delay * attempt)
                continue

            # print(f"[get_embeddings] Failed after {attempt} attempts: {e}")
            return None


def get_google_embeddings(max_retries: int = 3, delay: float = 2.0):
    for attempt in range(1, max_retries + 1):
        try:
            return GoogleGenerativeAIEmbeddings(
                model="gemini-embedding-2-preview",
                output_dimensionality=1536
            )
        except Exception as e:
            error_str = str(e).lower()
            is_quota = "429" in error_str or "resource_exhausted" in error_str or "rate" in error_str

            if is_quota and attempt < max_retries:
                # print(f"[get_google_embeddings] Quota hit, retrying ({attempt}/{max_retries})")
                asyncio.sleep(delay * attempt)
                continue

            # print(f"[get_google_embeddings] Failed after {attempt} attempts: {e}")
            return None