# InsightFlow — Frontend Web Application

InsightFlow's frontend is a highly polished, interactive React 19 web application built with TypeScript, Vite, Tailwind CSS, and Shadcn/Aceternity UI components. It provides a seamless, real-time multimedia chat experience with advanced session management, clickable media citations, and background token refreshing.

---

## Table of Contents

- [Key Features](#-key-features)
- [UI Architecture & Experience](#-ui-architecture--experience)
  - [Interactive Chat Sidebar](#1-interactive-chat-sidebar)
  - [Real-Time SSE Streaming Interface](#2-real-time-sse-streaming-interface)
  - [Clickable Media Citations & Playback](#3-clickable-media-citations--playback)
  - [Two-Phase Upload & Attachment Management](#4-two-phase-upload--attachment-management)
  - [Silent Token Refreshing](#5-silent-token-refreshing)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Method 1: Local Development](#method-1-local-development)
  - [Method 2: Docker Compose](#method-2-docker-compose)
- [Environment Variables](#-environment-variables)

---

## 🌟 Key Features
- **Real-Time SSE Chat Interface:** Renders AI streaming text, live token usage/cost metrics, and beautiful inline markdown rendering (`react-markdown` + `react-syntax-highlighter`).
- **Premium UI & Animations:** Built with Tailwind CSS, Framer Motion, and Aceternity/Shadcn UI (featuring Background Ripple, Text Generate effects, and Placeholders/Vanish inputs).
- **Interactive Chat Management:** Collapsible sidebar for organizing, renaming, deleting, and navigating chat sessions with pagination support.
- **Clickable Timestamp Citations:** Audio/video citations render as interactive timestamp pills (e.g., `[0:05 - 1:52]`). Clicking a pill instantly seeks a `plyr-react` media player to the exact second and begins playback.
- **Robust Session Maintenance:** Custom `useSilentTokenRefresh` hook automatically refreshes authentication tokens in the background without interrupting user workflows.

---

## 🖥️ UI Architecture & Experience

### 1. Interactive Chat Sidebar
A ChatGPT-inspired collapsible sidebar that allows users to manage their conversation history:
- **New Chat Generation:** Instantly creates a fresh session context.
- **Inline Renaming & Deletion:** Features a clean three-dot dropdown menu on active sessions to rename chat titles or delete old conversations.
- **Pagination:** Handles large chat histories smoothly via infinite scroll/pagination indicators.

### 2. Real-Time SSE Streaming Interface
When a query is submitted, the frontend listens to Server-Sent Events (`text/event-stream`) to provide instant feedback:
- **Streaming Tokens:** Text appears progressively with smooth animation effects.
- **Live Usage Stats:** Dedicated pill indicators show the exact prompt tokens, completion tokens, total tokens, and estimated cost for every single AI response.
- **Dynamic Guardrails:** Prevents redundant chat history re-fetching when clicking the currently active session and disables form submission while the AI is actively generating.

### 3. Clickable Media Citations & Playback
InsightFlow bridges text and multimedia by rendering interactive citation pills alongside an embedded audio/video player (`plyr-react`):
- When the AI references a specific moment in an uploaded recording, it includes timestamp metadata (`start`, `end`).
- Clicking the citation pill automatically updates the player's seek bar to the exact starting second and plays the relevant audio/video clip.

### 4. Two-Phase Upload & Attachment Management
Users can attach multiple PDF, audio, or video files to their chat:
- Uploads immediately return a temporary identifier (`temp_id`), allowing users to view upload progress or cancel/replace files before submitting their prompt.
- Cancelling an attachment instantly triggers a cleanup call to prevent orphaned backend storage.

### 5. Silent Token Refreshing
To prevent unexpected session timeouts during long research workflows, the `useSilentTokenRefresh` hook operates silently in the background:
- It monitors `VITE_ACCESS_TOKEN_TTL` (configured to `50m`), applying a 10-second safety buffer to preemptively call `/auth/refresh` before the backend token expires.
- If the refresh succeeds, the user remains authenticated indefinitely without disruptive login redirects.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Core framework | React 19, TypeScript, Vite |
| Styling & UI | Tailwind CSS, Framer Motion |
| Component libraries | Shadcn UI, Aceternity UI |
| Icons | Lucide React, Tabler Icons |
| State & Data fetching | Redux Toolkit, Axios, native `fetch` (for SSE) |
| Markdown rendering | `react-markdown`, `react-syntax-highlighter` |
| Media playback | `plyr-react` |
| Notifications | `react-toastify` |
| Containerization | Docker + Nginx |

---

## 🚀 Getting Started

### Prerequisites
- Node.js 20+
- Docker & Docker Compose (for containerized deployment)

---

### Method 1: Local Development

```bash
cd frontend
npm install
```

Create a `frontend/.env` file:

```env
VITE_ACCESS_TOKEN_TTL=50m
VITE_BACKEND_URL=http://localhost:8000/api/v1
```

Start the Vite development server:

:```bash
npm run dev
```

Access the frontend application at `http://localhost:5173`.

---

### Method 2: Docker Compose

1. Ensure `frontend/.env` is fully configured.
2. From the project root:

```bash
docker compose up --build -d
```

Docker Compose builds the optimized React static bundle and serves it via Nginx on port `3000`.

Access the application at `http://localhost:3000`.

---

## 🔑 Environment Variables

### `frontend/.env`

```env
VITE_ACCESS_TOKEN_TTL=50m
VITE_BACKEND_URL=http://localhost:8000/api/v1
```

> **Note:** `VITE_ACCESS_TOKEN_TTL` should be set slightly shorter than the backend's access token expiration (e.g., 50m vs 60m) to allow the silent refresh hook to maintain the session seamlessly.
