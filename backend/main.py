from contextlib import asynccontextmanager
from app.core.db import init_db
from fastapi import FastAPI
from app.router.auth import router as auth_router
from app.router.user import router as user_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db(app)
    yield

app = FastAPI(
    title="AI Multimedia RAG API",
    version="1.0.0",
    lifespan=lifespan
)

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

API_V1 = "/api/v1"

app.include_router(auth_router,prefix=API_V1)
app.include_router(user_router,prefix=API_V1)


@app.get("/")
async def root():
    return {
        "message": "Server running"
    }