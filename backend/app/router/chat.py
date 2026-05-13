import uuid
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import asyncio

from app.models.temp_data import TempData
from app.schemas.chat import ChatRequest
from app.helpers.vector_db import vector_search
from app.services.file_processor import embed_and_store
from app.utils.embeddings import get_embeddings
from app.utils.llm import llm
from app.services.llm_response_stream import stream_response
from app.helpers.summarizer import generate_session_summary

embeddings = get_embeddings()

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


def generate_session_id():
    return f"session_{uuid.uuid4().hex}"


@router.post("/query")
async def query(payload: ChatRequest):

    try:

        # first message -> create new session
        session_id = (
            payload.session_id
            if payload.session_id
            else generate_session_id()
        )

        # get uploaded temp docs
        docs = await TempData.find(
            TempData.temp_id == payload.temp_id
        ).to_list()

        if not docs:
            raise HTTPException(
                status_code=404,
                detail="No uploaded files found"
            )

        asyncio.create_task(
            generate_session_summary(
                session_id=session_id,
                docs=docs,
                llm=llm
            )
        )

        # embed only first time
        for doc in docs:

            if not doc.embedded:

                embed_and_store(
                    session_id=session_id,
                    temp_id=payload.temp_id,
                    chunks=doc.chunks,
                    file_type=doc.file_type
                )

                doc.embedded = True
                await doc.save()

        # vector retrieval
        results = vector_search(
            session_id=session_id,
            query=payload.query,
            embeddings=embeddings,
            top_k=5
        )

        context = "\n\n".join(
            r["text"] for r in results
        )

        final_prompt = f"""
You are a helpful AI assistant.

Use the provided context to answer the question.

Context:
{context}

User Question:
{payload.query}
"""

        return StreamingResponse(
            stream_response(final_prompt, llm),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "session-id": session_id
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=repr(e)
        )