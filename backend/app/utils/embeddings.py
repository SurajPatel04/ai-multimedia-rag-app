from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()


def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=1536,
    )


def get_google_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        output_dimensionality=1536
    )