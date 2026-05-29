# InsightFlow — Backend API & RAG Engine

InsightFlow's backend is a production-grade FastAPI application powering the AI Retrieval-Augmented Generation (RAG) platform. It manages multi-modal file ingestion (PDFs, Word, Excel, CSVs, audio, video), advanced LangGraph agentic workflows, FAISS vector indexing, and real-time Server-Sent Events (SSE) streaming.

---

## Table of Contents

- [Key Features](#-key-features)
- [Architecture & Data Flow](#-architecture--data-flow)
  - [Upload & Ingestion Pipeline](#1-upload--ingestion-pipeline)
  - [Parallel Processing: Vector Store + Session Persistence](#2-parallel-processing-vector-store--session-persistence)
  - [Content Summarization Strategy](#3-content-summarization-strategy)
  - [Querying & RAG](#4-querying--rag)
  - [Streaming & Citations](#5-streaming--citations)
  - [Long-Term Conversation Memory](#6-long-term-conversation-memory)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Method 1: Local Development](#method-1-local-development)
  - [Method 2: Docker Compose](#method-2-docker-compose)
- [Environment Variables](#-environment-variables)

---

## 🌟 Key Features

### Backend (FastAPI + LangGraph + MongoDB)

- **Agentic RAG Workflow (LangGraph):** Orchestrates multi-turn conversation, context retrieval, and background session summarization for long-context retention.
- **Multi-Modal File Processing:** Supports PDF, Word (.docx), Excel (.xlsx), CSV, audio (MP3, WAV, MPEG), and video (MP4).
- **Cost-Efficient Two-Phase Ingestion:** Files are first stored temporarily and only promoted to the vector store after explicit user confirmation, preventing wasteful embedding of cancelled uploads.
- **Advanced AI & Vector Search:**
  - **Google Gemini & OpenAI** for high-quality vector embeddings and intelligent query completions.
  - **Deepgram API** for highly accurate audio/video transcription with timestamped utterance extraction.
  - **FAISS Vector Store** for high-performance local vector similarity search.
- **Real-Time SSE Streaming:** Streams AI responses, live token usage/cost calculations, and media citation metadata directly to the client via Server-Sent Events.
- **Secure Storage & Authentication:** JWT-based authentication (Access + Refresh tokens) backed by Beanie ODM/MongoDB, with secure file archiving via Supabase Storage.

---

## 🏗️ Architecture & Data Flow

### 1. Upload & Ingestion Pipeline

InsightFlow uses a deliberate **two-phase ingestion model** designed to minimize unnecessary embedding costs and simplify cleanup.

#### Phase 1 — Temporary Storage (Before User Confirmation)

When a user selects and uploads a file, the backend immediately:

1. Stores the file in **Supabase Storage**.
2. Processes the file content:
   - **PDF/Word/Excel/CSV:** Text is extracted and split into chunks.
   - **Audio/Video:** The file is sent to **Deepgram** for transcription. The resulting transcript is broken into utterances, each carrying a precise `start` and `end` timestamp (e.g., `[0:05 - 1:52]`). These timestamped utterances are then chunked for retrieval.
3. Saves all raw chunks — along with metadata such as file URL, file name, and for audio/video the timestamps per chunk — into **MongoDB as temporary documents**.
4. Returns a `temp_id` to the frontend.

At this stage, **no embeddings are generated and nothing is written to the vector store.** This keeps costs at zero for files the user may discard.

#### Phase 1b — Cancellation & Cleanup

If the user deselects or cancels the file before confirming, the frontend sends the `temp_id` to a cleanup endpoint. The backend:

- Deletes the temporary MongoDB documents associated with that `temp_id`.
- Removes the file from Supabase Storage.

This makes cleanup simple, cheap, and reliable with no orphaned data or wasted embedding calls.

---

### 2. Parallel Processing: Vector Store + Session Persistence

Once the user confirms their file selection and sends the `temp_id`, the backend triggers **two parallel operations**:

#### Operation A — Embedding & Vector Indexing

- Temporary chunks are retrieved from MongoDB.
- Embeddings are generated (via OpenAI or Google Gemini) for each chunk.
- Chunks and their embeddings are indexed into the **FAISS vector store**.
- For audio/video chunks, the timestamp metadata (`start`, `end`) is stored alongside each vector so it can be returned at retrieval time.

#### Operation B — Session Data Persistence

- The temporary MongoDB documents are promoted to **permanent session documents**.
- Session records store: file URL, file name, content type, chunk references, and a full content summary (see Summarization Strategy below).
- Temporary records are deleted once the session record is confirmed.

Both operations run concurrently, so the server reaches a ready state as fast as possible.

---

### 3. Content Summarization Strategy

When a file is confirmed, InsightFlow generates a **structured content summary** to give the LLM high-level context about each file. The strategy adapts based on content length:

#### Short Content (under ~6,000 tokens)

If the total extracted text fits within a single prompt, the entire content is sent in **one API call** to produce a unified summary directly.

#### Long Content (over ~6,000 tokens)

For larger files, a **two-pass chunked summarization** approach is used:

1. **Pass 1 — Per-Chunk Summaries:** The content is iterated chunk by chunk. Each chunk is sent to the LLM individually, producing an intermediate summary per chunk.
2. **Pass 2 — Aggregation:** Once all per-chunk summaries are collected, a final LLM call is made that combines them into a single coherent content summary.

This ensures even very large documents or long recordings are accurately summarized without hitting context limits, and the final summary is stored in MongoDB as part of the session record.

---

### 4. Querying & RAG

When a user sends a chat message:

1. The query is embedded and matched against the **FAISS vector store** to retrieve the most relevant chunks.
2. For audio/video files, retrieved chunks include their original `start`/`end` timestamps.
3. **LangGraph** manages the full conversational state: it passes retrieved chunks, session context, conversation history, and the current query to the selected LLM (OpenAI or Gemini).
4. The LLM generates a response grounded in the retrieved content.

---

### 5. Streaming & Citations

The backend streams the LLM response back to the client in real time using **Server-Sent Events (SSE)**. Each streamed event can carry:

- **Response tokens** — displayed as they arrive.
- **Document citations** — chunk references for PDF, Word, and Spreadsheet sources.
- **Media citations** — timestamp ranges (e.g., `[0:05 - 1:52]`) for audio/video sources, rendered on the frontend as clickable pills that seek the media player to that exact moment.
- **Token usage & cost** — live stats computed server-side as the stream progresses.

---

### 6. Long-Term Conversation Memory

InsightFlow uses a **MongoDB-backed LangGraph checkpointer** to persist full conversation state across sessions. To prevent token bloat as conversations grow long, a smart summarization strategy runs automatically:

- After each message, the checkpointer evaluates **both message count and total token usage**.
- When either threshold is exceeded (e.g., message history grows beyond a configured length or cumulative tokens become large), LangGraph triggers a **background summarization node**.
- This node condenses older conversation turns into a compact summary, which replaces the raw history in future context windows.
- The result: the model always has full situational awareness of the conversation without ever exceeding token limits, and costs scale gracefully even in very long sessions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| Agentic orchestration | LangGraph |
| Database & ODM | MongoDB + Beanie |
| Conversation persistence | MongoDB LangGraph Checkpointer |
| Vector store | FAISS |
| File storage | Supabase Storage |
| Transcription | Deepgram |
| Embeddings & LLM | OpenAI, Google Gemini |
| Streaming | Server-Sent Events (SSE) |
| Authentication | JWT (Access + Refresh tokens) |
| Containerization | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (for containerized deployment)
- External API keys: OpenAI, Google Gemini, Deepgram, Supabase, and a MongoDB Atlas URI.

---

### Method 1: Local Development

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
```

Create `backend/.env` (see [Environment Variables](#-environment-variables) below), then start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`.

---

### Method 2: Docker Compose

1. Ensure `backend/.env` is fully configured.
2. From the project root:

```bash
docker compose up --build -d
```

Docker Compose starts the `insightflow-backend` service on port `8000`.

---

## 🔑 Environment Variables

### `backend/.env`

```env
ACCESS_TOKEN_SECRET=your_super_secret_access_key
ACCESS_TOKEN_TTL=60m
REFRESH_TOKEN_SECRET=your_super_secret_refresh_key
REFRESH_TOKEN_TTL=7d

MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/
MONGO_DB_NAME=ai-rag

OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIzaSy...
DEEPGRAM_API_KEY=your_deepgram_key

SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key

ENV=development
```

Refer to `backend/.env-sample` for the full list of required keys.
