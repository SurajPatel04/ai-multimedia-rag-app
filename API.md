# AI Multimedia RAG API Documentation

This document provides complete, comprehensive documentation for all backend API endpoints in the AI Multimedia RAG system. It details the required request headers, payloads, expected responses, and possible scenarios (success and error cases) for every route.

---

## Table of Contents

1. [Authentication Endpoints (`/api/v1/auth`)](#1-authentication-endpoints-apiv1auth)
   - [POST `/api/v1/auth/signUp`](#post-apiv1authsignup)
   - [POST `/api/v1/auth/signIn`](#post-apiv1authsignin)
   - [POST `/api/v1/auth/signOut`](#post-apiv1authsignout)
   - [POST `/api/v1/auth/refresh`](#post-apiv1authrefresh)
2. [User Endpoints (`/api/v1/user`)](#2-user-endpoints-apiv1user)
   - [GET `/api/v1/user/me`](#get-apiv1userme)
3. [File Upload Endpoints (`/api/v1/upload`)](#3-file-upload-endpoints-apiv1upload)
   - [POST `/api/v1/upload`](#post-apiv1upload)
   - [DELETE `/api/v1/upload/cancel/{temp_id}/{file_id}`](#delete-apiv1uploadcanceltemp_idfile_id)
4. [Chat Endpoints (`/api/v1/chat`)](#4-chat-endpoints-apiv1chat)
   - [POST `/api/v1/chat/query`](#post-apiv1chatquery)
   - [GET `/api/v1/chat/sessions`](#get-apiv1chatsessions)
   - [GET `/api/v1/chat/session/{session_id}`](#get-apiv1chatsessionsession_id)
   - [PATCH `/api/v1/chat/session/{session_id}`](#patch-apiv1chatsessionsession_id)
   - [DELETE `/api/v1/chat/session/{session_id}`](#delete-apiv1chatsessionsession_id)
5. [System & Debug Endpoints](#5-system--debug-endpoints)
   - [GET `/`](#get-)
   - [GET `/debug/faiss`](#get-debugfaiss)

---

## 1. Authentication Endpoints (`/api/v1/auth`)

### POST `/api/v1/auth/signUp`

Registers a new user account in the system.

- **Rate Limit:** 10 requests per minute.
- **Content-Type:** `application/json`

#### Request Payload

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "password": "securepassword123"
}
```

*Note: `last_name` is optional.*

#### Expected Responses & Scenarios

- **Scenario 1: Successful Registration (201 Created)**
  ```json
  {
    "success": true,
    "message": "Account created successfully"
  }
  ```

- **Scenario 2: User Already Exists (400 Bad Request)**
  Occurs if the provided email is already registered.
  ```json
  {
    "success": false,
    "message": "User already exists"
  }
  ```

- **Scenario 3: Rate Limit Exceeded (429 Too Many Requests)**
  Occurs if more than 10 requests are sent within a minute.
  ```json
  {
    "success": false,
    "message": "Too many requests. Please try again after some time."
  }
  ```

---

### POST `/api/v1/auth/signIn`

Authenticates a user and issues JWT Access and Refresh tokens stored securely in HTTP-only cookies.

- **Rate Limit:** 10 requests per minute.
- **Content-Type:** `application/json`

#### Request Payload

```json
{
  "email": "john.doe@example.com",
  "password": "securepassword123"
}
```

#### Expected Responses & Scenarios

- **Scenario 1: Successful Login (200 OK)**
  Returns user details and sets two HTTP-only cookies: `access_token` (Path: `/`) and `refresh_token` (Path: `/api/v1/auth`).
  ```json
  {
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "userId": "6a053ec9cf1d50cdb308773e"
  }
  ```
  **Response Cookies:**
  - `access_token`: `<jwt_access_token>` (HttpOnly, SameSite=Lax, Max-Age=900)
  - `refresh_token`: `<jwt_refresh_token>` (HttpOnly, SameSite=Lax, Max-Age=604800, Path=/api/v1/auth)

- **Scenario 2: Invalid Credentials (400 Bad Request)**
  Occurs if the email is not found or the password does not match.
  ```json
  {
    "success": false,
    "message": "Invalid email or password"
  }
  ```

- **Scenario 3: Rate Limit Exceeded (429 Too Many Requests)**
  ```json
  {
    "success": false,
    "message": "Too many requests. Please try again after some time."
  }
  ```

---

### POST `/api/v1/auth/signOut`

Logs out the user, revokes their active refresh token in the database, and clears authentication cookies.

- **Request Headers/Cookies:** `refresh_token` cookie (optional, used to identify and revoke the token in the DB).

#### Expected Responses & Scenarios

- **Scenario 1: Successful Sign Out (200 OK)**
  Clears both `access_token` and `refresh_token` cookies from the client browser.
  ```json
  {
    "success": true,
    "message": "Account signed out successfully"
  }
  ```

---

### POST `/api/v1/auth/refresh`

Generates a new access token and rotates the refresh token using a valid, non-revoked refresh token cookie.

- **Request Cookies:** Requires `refresh_token` cookie.

#### Expected Responses & Scenarios

- **Scenario 1: Successful Token Rotation (200 OK)**
  Issues new `access_token` and `refresh_token` cookies.
  ```json
  {
    "success": true,
    "message": "Tokens refreshed successfully"
  }
  ```

- **Scenario 2: Missing Refresh Token Cookie (401 Unauthorized)**
  ```json
  {
    "success": false,
    "message": "No refresh token"
  }
  ```

- **Scenario 3: Token Revoked or Invalid (401 Unauthorized)**
  Occurs if the refresh token has been revoked, expired, or tampered with.
  ```json
  {
    "success": false,
    "message": "Token revoked" 
  }
  ```
  *(or `"Invalid refresh token"` / `"Token not found"`).*

---

## 2. User Endpoints (`/api/v1/user`)

### GET `/api/v1/user/me`

Retrieves the profile information of the currently authenticated user.

- **Request Headers/Cookies:** Requires valid `access_token` cookie or `Authorization: Bearer <token>`.

#### Expected Responses & Scenarios

- **Scenario 1: Successful Profile Fetch (200 OK)**
  ```json
  {
    "success": true,
    "message": "User fetched successfully",
    "data": {
      "id": "6a053ec9cf1d50cdb308773e",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "createdAt": "2026-05-17T10:00:00.000Z",
      "updatedAt": "2026-05-17T10:00:00.000Z"
    }
  }
  ```

- **Scenario 2: Unauthenticated (401 Unauthorized)**
  Occurs if the access token is missing, expired, or invalid.
  ```json
  {
    "success": false,
    "message": "Not authenticated"
  }
  ```

- **Scenario 3: User Not Found (404 Not Found)**
  Occurs if the user record no longer exists in the database.
  ```json
  {
    "success": false,
    "message": "User not found"
  }
  ```

---

## 3. File Upload Endpoints (`/api/v1/upload`)

### POST `/api/v1/upload`

Uploads one or more multimedia files (PDF, audio, video). The endpoint saves files locally, uploads them to Supabase Storage, processes/chunks the content (including Whisper transcription for audio/video), and stores temporary metadata in MongoDB. Supports initial uploads and replacing existing temporary uploads.

- **Request Headers/Cookies:** Requires valid `access_token`.
- **Content-Type:** `multipart/form-data`

#### Request Payload (Form Data)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `files` | `List[UploadFile]` | **Yes** | The files to upload. Allowed MIME types: `application/pdf`, `audio/mpeg`, `audio/mp3`, `video/mp4`, `audio/wav`. Max size: 50MB per file. |
| `temp_id` | `str` | No | Existing temporary batch ID. Provided when replacing files in an unsubmitted chat prompt. |
| `changed_files` | `str` | No | Optional metadata regarding modified files. |

#### Expected Responses & Scenarios

- **Scenario 1: Successful Initial Upload (200 OK)**
  Occurs when uploading files for a new chat prompt (`temp_id` omitted). Generates a new `temp_id`.
  ```json
  {
    "success": true,
    "message": "Files uploaded successfully",
    "temp_id": "tmp_a1b2c3d4e5f6g7h8",
    "data": [
      {
        "file_id": "file_1234567890abcdef",
        "original_name": "document.pdf",
        "saved_name": "uuid1234.pdf",
        "content_type": "application/pdf"
      }
    ]
  }
  ```

- **Scenario 2: Successful File Replacement (200 OK)**
  Occurs when `temp_id` is provided in the form data. Deletes the previous temporary records and replaces them with the new files.
  ```json
  {
    "success": true,
    "message": "Files replaced successfully",
    "temp_id": "tmp_a1b2c3d4e5f6g7h8",
    "data": [
      {
        "file_id": "file_fedcba0987654321",
        "original_name": "v2_document.pdf",
        "saved_name": "uuid5678.pdf",
        "content_type": "application/pdf"
      }
    ]
  }
  ```

- **Scenario 3: Invalid File Type (400 Bad Request)**
  Occurs if any uploaded file has an unsupported MIME type.
  ```json
  {
    "success": false,
    "message": "archive.zip has invalid file type"
  }
  ```

- **Scenario 4: File Size Exceeded (400 Bad Request)**
  Occurs if a file exceeds the 50MB limit during upload.
  ```json
  {
    "success": false,
    "message": "large_video.mp4 exceeds 100MB limit"
  }
  ```

- **Scenario 5: Client Disconnected (499 Client Closed Request)**
  Occurs if the user aborts the upload or disconnects before processing completes.
  ```json
  {
    "success": false,
    "message": "Client disconnected"
  }
  ```

---

### DELETE `/api/v1/upload/cancel/{temp_id}/{file_id}`

Cancels and deletes a specific uploaded file from a temporary upload batch before it is attached to a chat session.

- **Request Headers/Cookies:** Requires valid `access_token`.

#### Path Parameters

- `temp_id` (`str`): The temporary batch ID (`tmp_...`).
- `file_id` (`str`): The specific file identifier (`file_...`).

#### Expected Responses & Scenarios

- **Scenario 1: Successful Cancellation (200 OK)**
  Removes the temporary file record from the database.
  ```json
  {
    "success": true,
    "message": "File cancelled successfully"
  }
  ```

- **Scenario 2: File Not Found (404 Not Found)**
  Occurs if the file does not exist or does not belong to the authenticated user.
  ```json
  {
    "success": false,
    "message": "File not found"
  }
  ```

---

## 4. Chat Endpoints (`/api/v1/chat`)

### POST `/api/v1/chat/query`

Submits a user prompt to the AI multimedia RAG pipeline. This endpoint migrates any newly uploaded temporary files (`temp_id`) to the active chat session, checks the Redis semantic cache for identical/similar previous queries, executes the LangGraph workflow (vector retrieval, LLM synthesis, summarization, title generation), and streams the AI response back via Server-Sent Events (SSE).

- **Request Headers/Cookies:** Requires valid `access_token`.
- **Content-Type:** `application/json`

#### Request Payload

```json
{
  "query": "What are the key takeaways from the uploaded video and PDF?",
  "session_id": "session_a1b2c3d4",
  "temp_id": "tmp_a1b2c3d4e5f6g7h8"
}
```

*Notes:*
- `session_id`: Optional. If omitted, a new chat session is automatically created.
- `temp_id`: Optional. Required only when attaching newly uploaded files to the chat prompt.

#### Expected Responses & Scenarios (Streaming SSE - `text/event-stream`)

This endpoint responds with a stream of Server-Sent Events. Each event payload is formatted as `data: <json_string>\n\n`.

- **Scenario 1: Cache Miss / Normal RAG Execution (SSE Stream)**
  When the query is new or new files are attached, the full RAG pipeline executes and streams the following sequence of events:

  1. **Metadata Event** (Initial session state & title):
     ```json
     data: {"type": "metadata", "session_id": "session_a1b2c3d4", "title": "Key Takeaways from Video"}
     ```
  2. **Media Citations Event** (Proactively streams video/audio citations before text):
     ```json
     data: {"type": "media", "media_refs": [{"document_id": "6a053ec...", "file_name": "lecture.mp4", "file_url": "https://...", "start": 10, "end": 45}]}
     ```
  3. **Text Chunk Events** (Streamed AI response tokens):
     ```json
     data: {"type": "text", "data": "The "}
     data: {"type": "text", "data": "key "}
     data: {"type": "text", "data": "takeaways "}
     ```
  4. **Usage & Cost Metric Event** (Final LLM token usage and calculated pricing):
     ```json
     data: {"type": "usage", "prompt_tokens": 1250, "completion_tokens": 340, "total_tokens": 1590, "total_cost": 0.00521}
     ```
  5. **Done Event & Stream Termination**:
     ```json
     data: {"type": "done", "session_id": "session_a1b2c3d4", "title": "Key Takeaways from Video"}
     ```
     ```text
     data: [DONE]
     ```

- **Scenario 2: Semantic Cache Hit (SSE Stream)**
  If an identical or highly similar query (≥95% cosine similarity) was previously asked within the session (and no new files were attached), the endpoint bypasses the LLM/RAG pipeline and streams the cached answer instantly.
  ```json
  data: {"type": "metadata", "session_id": "session_a1b2c3d4", "title": "Key Takeaways from Video"}
  ```
  ```json
  data: {"type": "text", "data": "The ", "cached": true}
  data: {"type": "text", "data": "key ", "cached": true}
  data: {"type": "text", "data": "takeaways ", "cached": true}
  ```
  ```json
  data: {"type": "usage", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "total_cost": 0}
  ```
  ```json
  data: {"type": "done", "session_id": "session_a1b2c3d4", "title": "Key Takeaways from Video"}
  ```
  ```text
  data: [DONE]
  ```

- **Scenario 3: Invalid Temporary ID (404 Not Found)**
  Occurs if `temp_id` is provided but no corresponding temporary files exist in the database.
  ```json
  {
    "success": false,
    "message": "No uploaded files found for this temp_id"
  }
  ```

---

### GET `/api/v1/chat/sessions`

Retrieves a paginated list of active chat sessions belonging to the authenticated user.

- **Request Headers/Cookies:** Requires valid `access_token`.

#### Query Parameters

| Parameter | Type | Default | Validation | Description |
| :--- | :--- | :--- | :--- | :--- |
| `page` | `int` | `1` | `>= 1` | The page number to fetch. |
| `limit` | `int` | `10` | `1` to `100` | Number of sessions per page. |

#### Expected Responses & Scenarios

- **Scenario 1: Successful Fetch (200 OK)**
  Returns active sessions sorted by creation date descending, along with pagination metadata.
  ```json
  {
    "success": true,
    "data": [
      {
        "session_id": "session_a1b2c3d4",
        "title": "Key Takeaways from Video",
        "is_active": true,
        "created_at": "2026-05-17T10:00:00.000Z",
        "updated_at": "2026-05-17T10:05:00.000Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total_sessions": 25,
      "total_pages": 3,
      "has_next": true,
      "has_previous": false
    }
  }
  ```

---

### GET `/api/v1/chat/session/{session_id}`

Retrieves the complete chat history, messages, media citations, and metadata for a specific chat session.

- **Request Headers/Cookies:** Requires valid `access_token`.
- **Path Parameters:** `session_id` (`str`).

#### Expected Responses & Scenarios

- **Scenario 1: Successful History Fetch (200 OK)**
  Returns session details and all associated human/AI messages sorted chronologically by `message_index`.
  ```json
  {
    "success": true,
    "data": {
      "session": {
        "session_id": "session_a1b2c3d4",
        "title": "Key Takeaways from Video",
        "is_active": true,
        "created_at": "2026-05-17T10:00:00.000Z",
        "updated_at": "2026-05-17T10:05:00.000Z"
      },
      "messages": [
        {
          "role": "human",
          "content": "What are the key takeaways from the uploaded video?",
          "message_index": 0,
          "file_references": [
            {
              "document_id": "6a053ec9cf1d50cdb308773e",
              "file_name": "lecture.mp4",
              "file_url": "https://supabase.co/storage/v1/object/public/...",
              "file_type": "video",
              "content_type": "video/mp4",
              "chunk_index": null,
              "timestamp_start": null,
              "timestamp_end": null
            }
          ],
          "prompt_tokens": null,
          "completion_tokens": null,
          "total_tokens": null,
          "total_cost": null,
          "created_at": "2026-05-17T10:01:00.000Z"
        },
        {
          "role": "ai",
          "content": "The key takeaways are...",
          "message_index": 1,
          "file_references": [
            {
              "document_id": "6a053ec9cf1d50cdb308773e",
              "file_name": "lecture.mp4",
              "file_url": "https://supabase.co/storage/v1/object/public/...",
              "file_type": "video",
              "content_type": "video/mp4",
              "chunk_index": 2,
              "timestamp_start": 10,
              "timestamp_end": 45
            }
          ],
          "prompt_tokens": 1250,
          "completion_tokens": 340,
          "total_tokens": 1590,
          "total_cost": 0.00521,
          "created_at": "2026-05-17T10:01:05.000Z"
        }
      ],
      "total_messages": 2
    }
  }
  ```

- **Scenario 2: Session Not Found (404 Not Found)**
  Occurs if the session does not exist or belongs to another user.
  ```json
  {
    "success": false,
    "message": "Session not found"
  }
  ```

---

### PATCH `/api/v1/chat/session/{session_id}`

Updates the title of a specific chat session.

- **Request Headers/Cookies:** Requires valid `access_token`.
- **Content-Type:** `application/json`
- **Path Parameters:** `session_id` (`str`).

#### Request Payload

```json
{
  "title": "Updated Chat Title"
}
```

*Validation: `title` must be between 1 and 100 characters.*

#### Expected Responses & Scenarios

- **Scenario 1: Successful Title Update (200 OK)**
  ```json
  {
    "success": true,
    "message": "Session title updated",
    "data": {
      "session_id": "session_a1b2c3d4",
      "title": "Updated Chat Title",
      "updated_at": "2026-05-17T10:10:00.000Z"
    }
  }
  ```

- **Scenario 2: Session Not Found (404 Not Found)**
  ```json
  {
    "success": false,
    "message": "Session not found"
  }
  ```

- **Scenario 3: Validation Error (422 Unprocessable Entity)**
  Occurs if `title` is empty or exceeds 100 characters.
  ```json
  {
    "success": false,
    "message": "Field required" 
  }
  ```

---

### DELETE `/api/v1/chat/session/{session_id}`

Soft-deletes a chat session by setting `is_active: false`.

- **Request Headers/Cookies:** Requires valid `access_token`.
- **Path Parameters:** `session_id` (`str`).

#### Expected Responses & Scenarios

- **Scenario 1: Successful Deletion (200 OK)**
  ```json
  {
    "success": true,
    "message": "Session deleted successfully"
  }
  ```

- **Scenario 2: Session Not Found (404 Not Found)**
  Occurs if the session is already deleted or does not exist.
  ```json
  {
    "success": false,
    "message": "Session not found"
  }
  ```

---

## 5. System & Debug Endpoints

### GET `/`

Root health check endpoint to verify server status.

#### Expected Response (200 OK)

```json
{
  "message": "Server running"
}
```

---

### GET `/debug/faiss`

Debug endpoint to inspect the contents and structure of the FAISS vector index store.

#### Expected Response (200 OK)

```json
{
  "total_docs": 15,
  "documents": [
    {
      "id": "doc_id_1",
      "content": "Sample chunk text stored in vector database...",
      "metadata": {
        "page": 1,
        "total_pages": 5
      }
    }
  ]
}
```
