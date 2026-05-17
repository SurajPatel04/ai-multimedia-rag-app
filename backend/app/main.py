from contextlib import asynccontextmanager
from app.core.db import init_db
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.exception_handler import add_exception_handlers
from langchain_community.vectorstores import FAISS

from app.router.auth import router as auth_router
from app.router.user import router as user_router
from app.router.chat import router as chat_router
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.router.file_upload import router as upload_router

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db(app)
    yield

app = FastAPI(
    title="AI Multimedia RAG API",
    version="1.0.0",
    lifespan=lifespan
)

add_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "Too many requests. Please try again after some time."
            }
    )


API_V1 = "/api/v1"

app.include_router(auth_router,prefix=API_V1)
app.include_router(user_router,prefix=API_V1)
app.include_router(chat_router,prefix=API_V1)
app.include_router(upload_router,prefix=API_V1)


@app.get("/")
async def root():
    return {
        "message": "Server running"
    }

@app.get("/debug/faiss")
def debug_faiss():

    vectorstore = FAISS.load_local(
        "faiss_indexes/6a053ec9cf1d50cdb308773e",
        GoogleGenerativeAIEmbeddings(
            model="models/embedding-001"
        ),
        allow_dangerous_deserialization=True
    )

    docs = []

    for key, value in vectorstore.docstore._dict.items():

        docs.append({
            "id": key,
            "content": value.page_content,
            "metadata": value.metadata
        })

    return {
        "total_docs": len(docs),
        "documents": docs
    }