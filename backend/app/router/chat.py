import uuid
import asyncio
import json
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies.auth import get_current_user
from app.models.temp_data import TempData
from app.models.session_document import SessionDocument
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatRequest
from app.helpers.vector_db import vector_search
from app.services.file_processor import embed_and_store
from app.utils.embeddings import get_embeddings, get_google_embeddings
from app.utils.llm import llm, INPUT_COST, OUTPUT_COST, google_llm
from app.helpers.summarizer import generate_session_summary
from app.graph.workflow import graph
from app.graph.nodes.memory_summarizer_node import run_summarizer_background
from langchain_core.messages import AIMessage

embeddings = get_google_embeddings()

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

        existing = await SessionDocument.find_one(
            SessionDocument.session_id == session_id,
            SessionDocument.file_name  == doc.file_name
        )

        if existing:
            session_docs.append(existing)
            continue

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

        if not doc.embedded:
            embed_and_store(
                user_id    = user_id,
                session_id = session_id,
                temp_id    = temp_id,
                chunks     = doc.chunks,
                file_type  = doc.file_type,
                file_name  = doc.file_name
            )
            session_doc.embedded = True
            await session_doc.save()
    await TempData.find(TempData.temp_id == temp_id).delete()

    return session_docs


@router.post("/query")
async def query(payload: ChatRequest, user_id = Depends(get_current_user)):

    try:


        is_new_session = not payload.session_id
        session_id = (
            payload.session_id
            if payload.session_id
            else generate_session_id()
        )

        user_id = user_id

        if is_new_session:
            await ChatSession(
                session_id = session_id,
                user_id    = user_id,
                title      = "" 
            ).insert()


        session_docs = []
        uploaded_file_names = [] 
        if payload.temp_id:
            session_docs = await migrate_temp_to_session(
                temp_id    = payload.temp_id,
                session_id = session_id,
                user_id    = user_id
            )

            uploaded_file_names = [doc.file_name for doc in session_docs]

            asyncio.create_task(
                generate_session_summary(
                    session_id = session_id,
                    docs       = session_docs,
                    llm        = google_llm
                )
            )

        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        result = await graph.ainvoke(
            {
                "query":      payload.query,
                "session_id": session_id,
                "user_id":    user_id,
                "title":      await get_chat_title(session_id),
                "uploaded_files": uploaded_file_names,
                "latest_files":    uploaded_file_names,
            },
            config=config
        )

        title = result.get("title") or await get_chat_title(session_id)

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

            media_refs = result.get("media_refs")
            if media_refs:
                yield f"data: {json.dumps({
                    'type':       'media',
                    'media_refs': media_refs,
                })}\n\n"

            async for chunk in google_llm.astream(result.get("messages", [])):

                content = ""

                if isinstance(chunk.content, str):
                    content = chunk.content

                elif isinstance(chunk.content, list):
                    for item in chunk.content:

                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                content += item.get("text", "")

                        elif hasattr(item, "text"):
                            content += item.text

                if content:
                    full_response += content

                    yield f"data: {json.dumps({
                        'type': 'text',
                        'data': content
                    })}\n\n"

                if chunk.usage_metadata:
                    prompt_tokens = chunk.usage_metadata.get("input_tokens", 0)
                    completion_tokens = chunk.usage_metadata.get("output_tokens", 0)
                    total_tokens = prompt_tokens + completion_tokens

                    if total_tokens > total_tokens:
                        prompt_tokens     = prompt_tokens
                        completion_tokens = completion_tokens
                        total_tokens      = total_tokens
                        total_cost        = (
                            (prompt_tokens * INPUT_COST) +
                            (completion_tokens * OUTPUT_COST)
                        )

                # print("CHUNK =>", chunk)

            # Yield usage only once, after streaming is complete
            yield f"data: {json.dumps({
                'type':              'usage',
                'prompt_tokens':     prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens':      total_tokens,
                'total_cost':        round(total_cost, 6),
            })}\n\n"

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

            if len(new_chat_history) >= 8:
                updated_state = {**result, "chat_history": new_chat_history}
                asyncio.create_task(
                    run_summarizer_background(
                        state  = updated_state,
                        config = config
                    )
                )

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

@router.get("/sessions")
async def get_chat_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_id=Depends(get_current_user)
):
    skip = (page - 1) * limit
    
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"created_at": -1}},
        {"$facet": {
            "sessions": [{"$skip": skip}, {"$limit": limit}],
            "total": [{"$count": "count"}]
        }}
    ]
    
    result = await ChatSession.aggregate(pipeline).to_list()
    
    sessions = result[0]["sessions"] if result else []
    total_sessions = result[0]["total"][0]["count"] if result and result[0]["total"] else 0
    
    total_pages = (total_sessions + limit - 1) // limit
    
    return {
        "success": True,
        "data": [
            {
                "session_id": s.session_id,
                "title": s.title or "New Chat",
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat()
            } for s in sessions
        ],
        "pagination": {
            "page": page, "limit": limit,
            "total_sessions": total_sessions,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }