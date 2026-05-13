from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

embed_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=1536,
)

def get_embeddings():
    return embed_model