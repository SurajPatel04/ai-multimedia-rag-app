import api from "./api";

const API_BASE_URL =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api/v1";

export interface ChatSession {
  session_id: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Pagination {
  page: number;
  limit: number;
  total_sessions: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ChatSessionsResponse {
  success: boolean;
  data: ChatSession[];
  pagination: Pagination;
}

export interface FileReference {
  document_id: string;
  file_name: string;
  file_url: string;
  file_type: string;
  content_type: string;
  chunk_index: number | null;
  timestamp_start: number | null;
  timestamp_end: number | null;
}

export interface ChatMessage {
  role: "human" | "ai";
  content: string;
  message_index: number;
  file_references: FileReference[];
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  total_cost: number | null;
  created_at: string;
}

export interface SessionDetail {
  session: ChatSession;
  messages: ChatMessage[];
  total_messages: number;
}

export interface SessionDetailResponse {
  success: boolean;
  data: SessionDetail;
}

// SSE event types from /chat/query 
export interface SSEMetadataEvent {
  type: "metadata";
  session_id: string;
  title: string;
}

export interface SSEMediaEvent {
  type: "media";
  media_refs: FileReference[];
}

export interface SSETextEvent {
  type: "text";
  data: string;
}

export interface SSEUsageEvent {
  type: "usage";
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  total_cost: number;
}

export interface SSEDoneEvent {
  type: "done";
  session_id: string;
  title: string;
}

export type SSEEvent =
  | SSEMetadataEvent
  | SSEMediaEvent
  | SSETextEvent
  | SSEUsageEvent
  | SSEDoneEvent;

export interface SendQueryParams {
  query: string;
  session_id?: string | null;
  temp_id?: string | null;
}

export const chatService = {
  fetchSessions: async (
    page: number = 1,
    limit: number = 20
  ): Promise<ChatSessionsResponse> => {
    const res = await api.get<ChatSessionsResponse>("/chat/sessions", {
      params: { page, limit },
    });
    return res.data;
  },

  fetchSessionDetail: async (
    sessionId: string
  ): Promise<SessionDetailResponse> => {
    const res = await api.get<SessionDetailResponse>(
      `/chat/session/${sessionId}`
    );
    return res.data;
  },

  sendQuery: async (
    params: SendQueryParams,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const body: Record<string, string> = { query: params.query };
    if (params.session_id) body.session_id = params.session_id;
    if (params.temp_id) body.temp_id = params.temp_id;

    const res = await fetch(`${API_BASE_URL}/chat/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
      signal,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Query failed (${res.status}): ${text}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        const payload = trimmed.slice(6);
        if (payload === "[DONE]") return;

        try {
          const parsed: SSEEvent = JSON.parse(payload);
          onEvent(parsed);
        } catch {
        }
      }
    }
  },

  renameSession: async (
    sessionId: string,
    title: string
  ): Promise<{ success: boolean; data: ChatSession }> => {
    const res = await api.patch<{ success: boolean; data: ChatSession }>(
      `/chat/session/${sessionId}`,
      { title }
    );
    return res.data;
  },

  deleteSession: async (
    sessionId: string
  ): Promise<{ success: boolean }> => {
    const res = await api.delete<{ success: boolean }>(
      `/chat/session/${sessionId}`
    );
    return res.data;
  },
};

