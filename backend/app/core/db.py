from pymongo import AsyncMongoClient
from dotenv import load_dotenv
import os
from beanie import init_beanie
from app.models import RefreshToken, User, TempData, ChatSession, ChatMessage, SessionDocument
from app.core.config import settings
load_dotenv()

async def init_db(app):
    client = AsyncMongoClient(settings.MONGO_URI)
    await init_beanie(database=client[settings.MONGO_DB_NAME], document_models=[RefreshToken, User, TempData, ChatSession, ChatMessage, SessionDocument])
    app.state.mongo_client = client