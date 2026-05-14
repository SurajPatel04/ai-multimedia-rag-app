import uuid
import asyncio
import json
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from app.dependencies.auth import get_current_user
from app.models.temp_data import TempData
from app.models.session_document import SessionDocument
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatRequest
from app.helpers.vector_db import vector_search
from app.services.file_processor import embed_and_store
from app.utils.embeddings import get_embeddings
from app.utils.llm import llm, INPUT_COST, OUTPUT_COST
from app.helpers.summarizer import generate_session_summary
from app.graph.workflow import graph
from app.graph.nodes.memory_summarizer_node import run_summarizer_background
from langchain_core.messages import AIMessage

embeddings = get_embeddings()

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


def generate_session_id():
    return f"session_{uuid.uuid4().hex}"


async def get_chat_title(session_id: str) -> str:
    chat_session = await ChatSession.find_one(
        ChatSession.session_id == session_id
    )
    return chat_session.title if chat_session and chat_session.title else ""


async def migrate_temp_to_session(
    temp_id: str,
    session_id: str,
    user_id: str
):
    """Move TempData docs → SessionDocument"""

    docs = await TempData.find(
        TempData.temp_id == temp_id
    ).to_list()

    if not docs:
        raise HTTPException(
            status_code=404,
            detail="No uploaded files found for this temp_id"
        )

    session_docs = []

    for doc in docs:

        # ✅ Check if already migrated
        existing = await SessionDocument.find_one(
            SessionDocument.session_id == session_id,
            SessionDocument.file_name  == doc.file_name
        )

        if existing:
            session_docs.append(existing)
            continue

        # ✅ Create SessionDocument from TempData
        session_doc = SessionDocument(
            session_id   = session_id,
            user_id      = user_id,
            file_name    = doc.file_name,
            file_url     = doc.file_url,
            file_type    = doc.file_type,
            content_type = doc.content_type,
            full_text    = doc.full_text,
            utterances   = [u.model_dump() for u in doc.utterances] if doc.utterances else [],
            chunks       = [c.model_dump() for c in doc.chunks] if doc.chunks else [],
            embedded     = False
        )

        await session_doc.insert()
        session_docs.append(session_doc)

        # ✅ Embed if not embedded
        if not doc.embedded:
            embed_and_store(
                session_id = session_id,
                temp_id    = temp_id,
                chunks     = doc.chunks,
                file_type  = doc.file_type,
                file_name  = doc.file_name
            )
            session_doc.embedded = True
            await session_doc.save()

    return session_docs


@router.post("/query")
async def query(payload: ChatRequest, user_id = Depends(get_current_user)):

    try:

        # -------------------------
        # Session ID
        # -------------------------

        is_new_session = not payload.session_id
        session_id = (
            payload.session_id
            if payload.session_id
            else generate_session_id()     # ✅ create if first message
        )

        user_id = user_id         # pass from auth/request

        # -------------------------
        # Create ChatSession if new
        # -------------------------

        if is_new_session:
            await ChatSession(
                session_id = session_id,
                user_id    = user_id,
                title      = ""            # title_generator_node will fill this
            ).insert()

        # -------------------------
        # Migrate TempData → SessionDocument
        # only when temp_id is provided
        # -------------------------

        session_docs = []

        if payload.temp_id:
            session_docs = await migrate_temp_to_session(
                temp_id    = payload.temp_id,
                session_id = session_id,
                user_id    = user_id
            )

            # ✅ Fire and forget summarizer — only when temp_id given
            asyncio.create_task(
                generate_session_summary(
                    session_id = session_id,
                    docs       = session_docs,
                    llm        = llm
                )
            )

        # -------------------------
        # Run LangGraph
        # -------------------------

        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        result = await graph.ainvoke(
            {
                "query":      payload.query,
                "session_id": session_id,
                "title":      await get_chat_title(session_id),
            },
            config=config
        )

        title = result.get("title") or await get_chat_title(session_id)

        # -------------------------
        # Stream response
        # -------------------------

        # ✅ Save human message to DB immediately
        current_index = result.get("message_index", 0)
        await ChatMessage(
            session_id    = session_id,
            user_id       = user_id,
            role          = "human",
            content       = payload.query,
            message_index = current_index,
        ).insert()

        async def stream_generator():

            full_response     = ""
            prompt_tokens     = 0
            completion_tokens = 0
            total_tokens      = 0
            total_cost        = 0

            yield f"data: {json.dumps({
                'type':       'metadata',
                'session_id': session_id,
                'title':      title,
            })}\n\n"

            async for chunk in llm.astream(result.get("messages", [])):

                if chunk.content:
                    full_response += chunk.content
                    yield f"data: {json.dumps({'type': 'text', 'data': chunk.content})}\n\n"

                if chunk.usage_metadata:
                    prompt_tokens     = chunk.usage_metadata["input_tokens"]
                    completion_tokens = chunk.usage_metadata["output_tokens"]
                    total_tokens      = prompt_tokens + completion_tokens
                    total_cost        = (prompt_tokens * INPUT_COST) + (completion_tokens * OUTPUT_COST)

                    yield f"data: {json.dumps({
                        'type':              'usage',
                        'prompt_tokens':     prompt_tokens,
                        'completion_tokens': completion_tokens,
                        'total_tokens':      total_tokens,
                        'total_cost':        round(total_cost, 6),
                    })}\n\n"

            # ✅ Save AI message to DB after streaming completes
            await ChatMessage(
                session_id        = session_id,
                user_id           = user_id,
                role              = "ai",
                content           = full_response,
                message_index     = current_index + 1,
                prompt_tokens     = prompt_tokens,
                completion_tokens = completion_tokens,
                total_tokens      = total_tokens,
                total_cost        = round(total_cost, 6) if total_cost else None,
            ).insert()

            # ✅ Save AIMessage to chat history via state update, not graph invoke
            new_chat_history = [
                *result.get("chat_history", []),
                AIMessage(content=full_response)
            ]
            
            await graph.aupdate_state(
                config,
                {
                    "message_index": current_index + 2,
                    "chat_history": new_chat_history
                }
            )

            # ✅ Fire and forget summarizer for chat history compression
            # Launching it here prevents race conditions with the stream state update
            if len(new_chat_history) >= 8:
                updated_state = {**result, "chat_history": new_chat_history}
                asyncio.create_task(
                    run_summarizer_background(
                        state  = updated_state,
                        config = config
                    )
                )

            # ✅ Return session_id + title at end of stream
            yield f"data: {json.dumps({
                'type':       'done',
                'session_id': session_id,
                'title':      title,
            })}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control":         "no-cache",
                "X-Accel-Buffering":     "no",
                "Access-Control-Allow-Origin": "*",
                "session-id":            session_id,
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=repr(e)
        )
