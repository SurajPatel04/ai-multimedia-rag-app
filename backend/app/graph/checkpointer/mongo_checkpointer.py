from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from app.core.config import settings


_client = None
_checkpointer = None


def get_checkpointer():

    global _client
    global _checkpointer

    if _checkpointer:
        return _checkpointer

    _client = MongoClient(
        settings.MONGO_URI
    )

    _checkpointer = MongoDBSaver(
        client=_client,
        db_name=settings.MONGO_DB_NAME,
        collection_name="langgraph_checkpoints"
    )

    return _checkpointer