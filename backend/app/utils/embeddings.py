from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

embed_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=1536,
)

def get_embeddings():
    return embed_model



google_embed_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        output_dimensionality=1536
    )
def get_google_embeddings():
    return google_embed_model