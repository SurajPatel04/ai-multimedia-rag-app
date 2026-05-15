import React, { useCallback, useEffect, useRef, useState, Fragment } from "react";
import { useSearchParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import ragIcon from "@/assets/rag.png";
import { ArrowDown, Copy, Check } from "lucide-react";
import {
  IconArrowLeft,
  IconDots,
  IconFile,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconLoader2,
  IconMessage,
  IconPaperclip,
  IconPencil,
  IconPlus,
  IconSearch,
  IconTrash,
  IconX,
} from "@tabler/icons-react";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { authService, type User } from "@/services/authService";
import {
  uploadFiles,
  type UploadedFileInfo,
} from "@/services/fileUploadService";
import {
  chatService,
  type ChatSession,
  type ChatMessage,
  type SSEEvent,
} from "@/services/chatService";





const placeholders = [
  "Ask anything about this assignment",
  "Upload a PDF, audio, or video file",
  "Summarize this file",
  "What should we build next?",
];

// Global Media Player
let activeTimeUpdateRef: { element: HTMLMediaElement; listener: () => void } | null = null;

const handlePlayMedia = (startSeconds: number, endSeconds: number) => {
  const mediaElements = Array.from(document.querySelectorAll("video, audio")) as HTMLMediaElement[];
  const mediaElement = mediaElements[mediaElements.length - 1];

  if (!mediaElement) return;

  // Scroll to the player so the user can see it!
  mediaElement.scrollIntoView({ behavior: "smooth", block: "center" });

  if (activeTimeUpdateRef) {
    activeTimeUpdateRef.element.removeEventListener("timeupdate", activeTimeUpdateRef.listener);
  }

  mediaElement.currentTime = startSeconds;
  mediaElement.play().catch(e => console.error("Play failed:", e));

  const listener = () => {
    if (mediaElement.currentTime >= endSeconds) {
      mediaElement.pause();
      mediaElement.removeEventListener("timeupdate", listener);
      activeTimeUpdateRef = null;
    }
  };

  mediaElement.addEventListener("timeupdate", listener);
  activeTimeUpdateRef = { element: mediaElement, listener };
};

const renderTextWithTimestamps = (text: string) => {
  // Matches standard [00:00 - 00:00] OR extended [filename.mp4 | 00:00 – 00:00]
  const regex = /\[(?:.*?\|\s*)?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-–]\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const startHours = match[1] ? parseInt(match[1], 10) : 0;
    const startMins = parseInt(match[2], 10);
    const startSecs = parseInt(match[3], 10);
    const startSeconds = startHours * 3600 + startMins * 60 + startSecs;

    const endHours = match[4] ? parseInt(match[4], 10) : 0;
    const endMins = parseInt(match[5], 10);
    const endSecs = parseInt(match[6], 10);
    const endSeconds = endHours * 3600 + endMins * 60 + endSecs;

    const timeLabel = `[${match[1] ? match[1] + ":" : ""}${match[2]}:${match[3]} - ${match[4] ? match[4] + ":" : ""}${match[5]}:${match[6]}]`;

    parts.push(
      <button
        key={match.index}
        type="button"
        className="mx-1 inline-flex items-center rounded bg-blue-500/20 px-1.5 py-0.5 text-[11px] font-semibold text-blue-400 transition-colors hover:bg-blue-500/30"
        onClick={() => handlePlayMedia(startSeconds, endSeconds)}
      >
        <span className="mr-1 text-[9px]">▶</span> {timeLabel}
      </button>
    );
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length === 1 && typeof parts[0] === "string" ? text : parts;
};

const processMarkdownChildren = (children: React.ReactNode): React.ReactNode => {
  if (typeof children === "string") {
    return renderTextWithTimestamps(children);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => <Fragment key={i}>{processMarkdownChildren(child)}</Fragment>);
  }
  return children;
};

interface AttachedFile {
  file: File;
  status: "uploading" | "uploaded" | "error";
  serverInfo?: UploadedFileInfo;
  error?: string;
}

const CodeBlock = ({ language, value }: { language: string; value: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 overflow-hidden rounded-md border border-neutral-800 text-[13px] bg-[#1e1e1e]">
      <div className="flex items-center justify-between bg-neutral-900 px-4 py-2 text-xs text-neutral-400">
        <span className="font-mono">{language}</span>
        <button onClick={handleCopy} className="flex items-center gap-1.5 hover:text-white transition-colors" type="button">
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied!" : "Copy code"}
        </button>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language}
        PreTag="div"
        customStyle={{ margin: 0, padding: "1rem", backgroundColor: "transparent" }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

const MessageActionToolbar = ({ text, isHuman }: { text: string; isHuman?: boolean }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`mt-0.5 flex items-center gap-2 text-neutral-500 transition-opacity duration-200 ${isHuman ? "opacity-0 group-hover:opacity-100" : "opacity-100"}`}>
      <button
        onClick={handleCopy}
        className="flex items-center justify-center rounded p-1 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
        title="Copy message"
        type="button"
      >
        {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
      </button>
    </div>
  );
};

interface ChatSessionItemProps {
  session: ChatSession;
  isActive: boolean;
  menuOpenSessionId: string | null;
  setMenuOpenSessionId: (id: string | null) => void;
  onSessionClick: (session: ChatSession) => void;
  onRenameSubmit: (sessionId: string, newTitle: string) => Promise<void>;
  onDelete: (sessionId: string) => Promise<void>;
  menuRef: React.RefObject<HTMLDivElement | null>;
}

const ChatSessionItem = ({
  session,
  isActive,
  menuOpenSessionId,
  setMenuOpenSessionId,
  onSessionClick,
  onRenameSubmit,
  onDelete,
  menuRef,
}: ChatSessionItemProps) => {
  const [isRenaming, setIsRenaming] = useState(false);
  const [tempTitle, setTempTitle] = useState(session.title);
  const isMenuOpen = menuOpenSessionId === session.session_id;
  const inputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    setTempTitle(session.title);
  }, [session.title]);

  useEffect(() => {
    if (isRenaming) {
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [isRenaming]);

  useEffect(() => {
    if (!isRenaming) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (formRef.current && !formRef.current.contains(e.target as Node)) {
        setIsRenaming(false);
        setTempTitle(session.title);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isRenaming, session.title]);

  const handleLocalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = tempTitle.trim();
    if (!trimmed || trimmed === session.title) {
      setIsRenaming(false);
      return;
    }
    await onRenameSubmit(session.session_id, trimmed);
    setIsRenaming(false);
  };

  return (
    <div className="group/session relative">
      {isRenaming ? (
        <form
          ref={formRef}
          className="flex items-center gap-1 px-2 py-1.5"
          onSubmit={handleLocalSubmit}
        >
          <input
            ref={inputRef}
            className="flex-1 min-w-0 rounded-md border border-neutral-600 bg-neutral-800 px-2 py-1.5 text-sm text-white outline-none focus:border-blue-500 transition-colors"
            value={tempTitle}
            onChange={(e) => setTempTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setIsRenaming(false);
                setTempTitle(session.title);
              }
            }}
          />
        </form>
      ) : (
        <div className={`flex w-full items-center rounded-lg transition-all duration-200 ${isActive
          ? "bg-[#2f2f2f] text-white shadow-sm"
          : "text-neutral-400 hover:bg-neutral-800/40 hover:text-neutral-200"
          }`}>
          <button
            type="button"
            onClick={() => onSessionClick(session)}
            className={`flex-1 min-w-0 px-2 py-2 pr-8 text-left text-sm outline-none focus:outline-none ${isActive ? "font-medium" : ""}`}
          >
            <span className="line-clamp-1">{session.title}</span>
          </button>

          <button
            type="button"
            className={`absolute right-1.5 shrink-0 p-1 text-neutral-500 transition hover:text-white group-hover/session:opacity-100 ${isActive || isMenuOpen ? "opacity-100" : "opacity-0"
              }`}
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              setMenuOpenSessionId(isMenuOpen ? null : session.session_id);
            }}
          >
            <IconDots className="h-4 w-4" />
          </button>
        </div>
      )}

      {isMenuOpen && (
        <div
          ref={menuRef}
          className="absolute right-1 top-9 z-50 w-36 overflow-hidden rounded-lg border border-neutral-700 bg-neutral-900 shadow-2xl animate-in fade-in slide-in-from-top-1"
        >
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-neutral-300 transition hover:bg-neutral-800 hover:text-white"
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
              setIsRenaming(true);
              setMenuOpenSessionId(null);
            }}
          >
            <IconPencil className="h-4 w-4" />
            Rename
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-400 transition hover:bg-neutral-800 hover:text-red-300"
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onDelete(session.session_id);
              setMenuOpenSessionId(null);
            }}
          >
            <IconTrash className="h-4 w-4" />
            Delete
          </button>
        </div>
      )}
    </div>
  );
};

export default function ChatPage() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  // Chat sessions state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionPage, setSessionPage] = useState(1);
  const [hasMoreSessions, setHasMoreSessions] = useState(true);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const scrollSentinelRef = useRef<HTMLDivElement>(null);

  // Active session state
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [activeMessages, setActiveMessages] = useState<ChatMessage[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastLoadedSessionIdRef = useRef<string | null>(null);

  const [menuOpenSessionId, setMenuOpenSessionId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenSessionId(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () =>
      document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleRenameSession = useCallback(async (sessionId: string, newTitle: string) => {
    const trimmed = newTitle.trim();
    if (!trimmed) {
      return;
    }
    try {
      const res = await chatService.renameSession(sessionId, trimmed);
      if (res.success) {
        setSessions((prev) =>
          prev.map((s) => s.session_id === sessionId ? { ...s, title: res.data.title } : s)
        );
        if (activeSession?.session_id === sessionId) {
          setActiveSession((prev) => prev ? { ...prev, title: res.data.title } : prev);
        }
      }
    } catch (err) {
      console.error("Failed to rename session", err);
    } finally {
      // No-op
    }
  }, [activeSession]);

  // Delete session handler
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await chatService.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSession?.session_id === sessionId) {
        setActiveSession(null);
        setSessionId(null);
        setActiveMessages([]);
        setSearchParams({}, { replace: true });
        lastLoadedSessionIdRef.current = null;
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    } finally {
      setMenuOpenSessionId(null);
    }
  }, [activeSession, setSearchParams]);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      setShowScrollToBottom(scrollHeight - scrollTop - clientHeight > 100);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Input & request state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const queryRef = useRef("");
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const uploadAbortControllerRef = useRef<AbortController | null>(null);
  const tempIdSentRef = useRef(false);

  // File‑upload state
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [tempId, setTempId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch user profile
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await authService.fetchProfile();
        setUser(userData);
      } catch (err) {
        console.error("Failed to load user profile", err);
      }
    };
    loadUser();
  }, []);

  const fetchSessions = useCallback(
    async (page: number) => {
      if (isLoadingSessions) return;
      setIsLoadingSessions(true);
      try {
        const res = await chatService.fetchSessions(page, 20);
        setSessions((prev) =>
          page === 1 ? res.data : [...prev, ...res.data]
        );
        setHasMoreSessions(res.pagination.has_next);
        setSessionPage(page);
      } catch (err) {
        console.error("Failed to load chat sessions", err);
      } finally {
        setIsLoadingSessions(false);
      }
    },
    [isLoadingSessions]
  );

  useEffect(() => {
    fetchSessions(1);
  }, []);
  useEffect(() => {
    const sentinel = scrollSentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMoreSessions && !isLoadingSessions) {
          fetchSessions(sessionPage + 1);
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMoreSessions, isLoadingSessions, sessionPage, fetchSessions]);

  const loadSession = useCallback(async (session: ChatSession) => {
    lastLoadedSessionIdRef.current = session.session_id;
    setActiveSession(session);
    setSessionId(session.session_id);
    setIsLoadingMessages(true);
    setActiveMessages([]);
    setTempId(null);
    tempIdSentRef.current = false;
    setAttachedFiles([]);
    try {
      const res = await chatService.fetchSessionDetail(session.session_id);
      if (res.success) {
        setActiveMessages(res.data.messages);
      }
    } catch (err) {
      console.error("Failed to load session messages", err);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  const handleSessionClick = useCallback(
    (session: ChatSession) => {
      if (session.session_id === lastLoadedSessionIdRef.current) return;
      setSearchParams({ session: session.session_id }, { replace: false });
      loadSession(session);
    },
    [setSearchParams, loadSession]
  );

  useEffect(() => {
    const urlSessionId = searchParams.get("session");

    if (!urlSessionId) {
      if (!isSending && !isUploading && (activeSession !== null || activeMessages.length > 0)) {
        setActiveSession(null);
        setSessionId(null);
        setActiveMessages([]);
        setTempId(null);
        tempIdSentRef.current = false;
        setAttachedFiles([]);
        lastLoadedSessionIdRef.current = null;
      }
      return;
    }

    if (
      !isSending &&
      !isUploading &&
      urlSessionId !== lastLoadedSessionIdRef.current &&
      sessions.length > 0
    ) {
      const found = sessions.find((s) => s.session_id === urlSessionId);
      if (found) {
        loadSession(found);
      }
    }
  }, [searchParams, sessions, isSending, isUploading, loadSession, activeSession, activeMessages.length]);



  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
    } finally {
      document.cookie.split(";").forEach((c) => {
        const name = c.split("=")[0].trim();
        document.cookie = `${name}=;expires=${new Date(0).toUTCString()};path=/`;
      });
      window.location.href = "/login";
    }
  };

  const getInitials = (user: User) => {
    const first = user.first_name?.[0] || "";
    const last = user.last_name?.[0] || "";
    return (first + last).toUpperCase() || "U";
  };

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const fileList = event.target.files;
      if (!fileList || fileList.length === 0) return;

      const newFiles = Array.from(fileList);
      const existingFiles = attachedFiles.filter(
        (af) => af.status === "uploaded"
      );
      const pendingNew: AttachedFile[] = newFiles.map((f) => ({
        file: f,
        status: "uploading" as const,
      }));
      setAttachedFiles([...existingFiles, ...pendingNew]);
      setIsUploading(true);

      const allFiles = [
        ...existingFiles.map((af) => af.file),
        ...newFiles,
      ];

      const controller = new AbortController();
      uploadAbortControllerRef.current = controller;

      try {
        const response = await uploadFiles(allFiles, tempId, controller.signal);

        if (response.success) {
          setTempId(response.temp_id);
          tempIdSentRef.current = false;

          setAttachedFiles(
            allFiles.map((f, idx) => ({
              file: f,
              status: "uploaded" as const,
              serverInfo: response.data[idx],
            }))
          );
        }
      } catch (err: unknown) {
        // @ts-ignore
        if (err?.name === "CanceledError" || err?.message === "canceled" || err?.code === "ERR_CANCELED") {
          setAttachedFiles([...existingFiles]);
          return;
        }

        const message =
          err instanceof Error ? err.message : "Upload failed";
        setAttachedFiles([
          ...existingFiles,
          ...newFiles.map((f) => ({
            file: f,
            status: "error" as const,
            error: message,
          })),
        ]);
      } finally {
        setIsUploading(false);
        uploadAbortControllerRef.current = null;
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [tempId, attachedFiles]
  );

  const handleRemoveFiles = useCallback(() => {
    if (uploadAbortControllerRef.current) {
      uploadAbortControllerRef.current.abort();
    }
    setAttachedFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // Remove a single file
  const handleRemoveSingleFile = useCallback((index: number) => {
    setAttachedFiles((prev) => {
      const fileToRemove = prev[index];
      if (fileToRemove?.status === "uploading" && uploadAbortControllerRef.current) {
        uploadAbortControllerRef.current.abort();
      }
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const query = queryRef.current.trim();
      if (!query || isSending || isUploading) return;

      const userMessage: ChatMessage = {
        role: "human",
        content: query,
        message_index: activeMessages.length,
        file_references: attachedFiles
          .filter((af) => af.status === "uploaded" && af.serverInfo)
          .map((af) => ({
            document_id: "",
            file_name: af.serverInfo!.original_name,
            file_url: URL.createObjectURL(af.file),
            file_type: af.serverInfo!.content_type,
            content_type: af.serverInfo!.content_type,
            chunk_index: null,
            timestamp_start: null,
            timestamp_end: null,
          })),
        prompt_tokens: null,
        completion_tokens: null,
        total_tokens: null,
        total_cost: null,
        created_at: new Date().toISOString(),
      };

      setActiveMessages((prev) => [...prev, userMessage]);
      queryRef.current = "";
      setIsSending(true);
      setAttachedFiles([]);

      const shouldSendTempId = tempId && !tempIdSentRef.current;

      const aiPlaceholder: ChatMessage = {
        role: "ai",
        content: "",
        message_index: activeMessages.length + 1,
        file_references: [],
        prompt_tokens: null,
        completion_tokens: null,
        total_tokens: null,
        total_cost: null,
        created_at: new Date().toISOString(),
      };

      setActiveMessages((prev) => [...prev, aiPlaceholder]);

      setTimeout(() => {
        scrollToBottom();
      }, 50);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await chatService.sendQuery(
          {
            query,
            session_id: sessionId || activeSession?.session_id || undefined,
            temp_id: shouldSendTempId ? tempId : undefined,
          },
          (event: SSEEvent) => {
            switch (event.type) {
              case "metadata": {
                setSessionId(event.session_id);
                lastLoadedSessionIdRef.current = event.session_id;

                setActiveSession((prev) => {
                  if (prev) {
                    return { ...prev, title: event.title || prev.title };
                  }
                  return {
                    session_id: event.session_id,
                    title: event.title || "New Chat",
                    is_active: true,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  };
                });

                setSearchParams(
                  { session: event.session_id },
                  { replace: true }
                );
                break;
              }

              case "media": {
                setActiveMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "ai") {
                    updated[updated.length - 1] = {
                      ...last,
                      file_references: event.media_refs,
                    };
                  }
                  return updated;
                });
                break;
              }

              case "text": {
                setActiveMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "ai") {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + event.data,
                    };
                  }
                  return updated;
                });
                break;
              }

              case "usage": {
                setActiveMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === "ai") {
                    updated[updated.length - 1] = {
                      ...last,
                      prompt_tokens: event.prompt_tokens,
                      completion_tokens: event.completion_tokens,
                      total_tokens: event.total_tokens,
                      total_cost: event.total_cost,
                    };
                  }
                  return updated;
                });
                break;
              }

              case "done": {
                setActiveSession((prev) => {
                  if (prev) {
                    return {
                      ...prev,
                      title: event.title || prev.title,
                    };
                  }
                  return prev;
                });

                fetchSessions(1);
                break;
              }
            }
          },
          controller.signal
        );

        if (shouldSendTempId) {
          tempIdSentRef.current = true;
        }
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") return;

        setActiveMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "ai" && !last.content) {
            updated.pop();
          }
          updated.push({
            role: "ai",
            content: `Error: ${(err as Error).message || "Failed to get response"}`,
            message_index: updated.length,
            file_references: [],
            prompt_tokens: null,
            completion_tokens: null,
            total_tokens: null,
            total_cost: null,
            created_at: new Date().toISOString(),
          });
          return updated;
        });
        console.error("Query error:", err);
      } finally {
        setIsSending(false);
        abortRef.current = null;
      }
    },
    [
      isSending,
      isUploading,
      activeMessages,
      attachedFiles,
      sessionId,
      activeSession,
      tempId,
      setSearchParams,
      fetchSessions,
    ]
  );

  const handleStopChat = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      setIsSending(false);
      setActiveMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "ai" && !last.content) {
          return prev.slice(0, -1);
        }
        return prev;
      });
    }
  }, []);

  //icon for file type
  const fileIcon = (file: File) => {
    if (file.type.startsWith("audio/"))
      return <span className="text-purple-400 text-xs">♪</span>;
    if (file.type.startsWith("video/"))
      return <span className="text-blue-400 text-xs">▶</span>;
    return <IconFile className="h-4 w-4 text-neutral-400" />;
  };

  return (
    <section className="flex h-screen w-full overflow-hidden bg-black">
      <Sidebar autoOpen={false} open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-6 border-r border-neutral-800 bg-black">
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className={`group/sidebar-toggle relative z-20 flex h-16 items-center gap-2 py-1 ${open ? "justify-start" : "justify-center"}`}>
              <Link
                aria-label="AI Chat"
                className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-transparent outline-none focus:outline-none"
                to="/chat"
              >
                <img src={ragIcon} alt="RAG Icon" className="h-full w-full object-contain" />
              </Link>
              {open ? (
                <span className="text-sm font-medium text-white">AI Chat</span>
              ) : null}
              <button
                aria-label={open ? "Collapse sidebar" : "Open sidebar"}
                className={
                  open
                    ? "ml-auto flex h-8 w-8 items-center justify-center rounded-md text-neutral-300 transition hover:bg-neutral-900 hover:text-white outline-none focus:outline-none focus:bg-neutral-900 active:bg-neutral-800"
                    : "absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-md bg-neutral-900/90 text-neutral-300 opacity-0 transition group-hover/sidebar-toggle:opacity-100 hover:text-white backdrop-blur-sm outline-none focus:outline-none active:bg-neutral-800"
                }
                onClick={() => setOpen((value) => !value)}
                type="button"
              >
                {open ? (
                  <IconLayoutSidebarLeftCollapse className="h-5 w-5" />
                ) : (
                  <IconLayoutSidebarLeftExpand className="h-5 w-5" />
                )}
              </button>
            </div>

            <div className="mt-1 flex flex-col gap-2">
              <SidebarLink
                link={{
                  label: "New chat",
                  href: "/chat",
                  icon: <IconPlus className="h-5 w-5 shrink-0 text-neutral-200" />,
                }}
              />
              <SidebarLink
                link={{
                  label: "Search chats",
                  href: "/chat",
                  icon: <IconSearch className="h-5 w-5 shrink-0 text-neutral-200" />,
                }}
              />

            </div>

            {open && (
              <div className="mt-8 flex min-h-0 flex-1 flex-col border-t border-neutral-800 pt-4">
                <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wide text-neutral-500">
                  Recent
                </p>
                <div className="flex flex-1 flex-col gap-1 overflow-y-auto pr-2 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-neutral-800 hover:scrollbar-thumb-neutral-700">
                  {sessions.length === 0 && !isLoadingSessions ? (
                    <p className="px-2 py-2 text-sm text-neutral-500">
                      No recent chats
                    </p>
                  ) : (
                    sessions.map((session) => (
                      <ChatSessionItem
                        key={session.session_id}
                        session={session}
                        isActive={activeSession?.session_id === session.session_id}
                        menuOpenSessionId={menuOpenSessionId}
                        setMenuOpenSessionId={setMenuOpenSessionId}
                        onSessionClick={handleSessionClick}
                        onRenameSubmit={handleRenameSession}
                        onDelete={handleDeleteSession}
                        menuRef={menuRef}
                      />
                    ))
                  )}

                  {/* Scroll sentinel for infinite loading */}
                  <div className="h-1" ref={scrollSentinelRef} />

                  {isLoadingSessions && (
                    <div className="flex items-center justify-center py-3">
                      <IconLoader2 className="h-4 w-4 animate-spin text-neutral-500" />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="relative flex flex-col gap-2">
            {isProfileMenuOpen && user && (
              <div className="absolute bottom-12 left-0 z-50 w-64 rounded-xl border border-neutral-800 bg-neutral-900 p-2 shadow-2xl">
                <div className="mb-2 truncate px-2 py-1.5 text-sm font-medium text-neutral-300">
                  {user.email}
                </div>
                <div className="h-px bg-neutral-800 mb-2"></div>
                <button
                  className="flex w-full items-center justify-start gap-2 rounded-lg px-2 py-2 text-sm text-red-400 transition hover:bg-neutral-800 hover:text-red-300"
                  onClick={handleLogout}
                  type="button"
                >
                  <IconArrowLeft className="h-4 w-4 shrink-0" />
                  <span>Logout</span>
                </button>
              </div>
            )}

            <button
              className="group flex w-full items-center gap-3 rounded-lg p-2 transition hover:bg-neutral-900"
              onClick={() => {
                if (open) {
                  setIsProfileMenuOpen((prev) => !prev);
                } else {
                  setOpen(true);
                  setIsProfileMenuOpen(true);
                }
              }}
              type="button"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-xs font-medium text-white transition group-hover:bg-neutral-700">
                {user ? getInitials(user) : "..."}
              </div>
              {open && (
                <div className="flex flex-1 flex-col items-start overflow-hidden text-sm">
                  <span className="truncate font-medium text-neutral-200">
                    {user ? `${user.first_name} ${user.last_name || ""}`.trim() : "Loading..."}
                  </span>
                </div>
              )}
            </button>
          </div>
        </SidebarBody>
      </Sidebar>

      <div className="flex min-w-0 flex-1 flex-col bg-neutral-950">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-800 px-4 md:px-6">
          <div>
            <h1 className="text-sm font-semibold text-white">
              {activeSession ? activeSession.title : "Chat"}
            </h1>
          </div>
        </header>

        <div className="relative flex-1 min-h-0">
          <div
            className="h-full overflow-y-auto px-4 py-6 md:px-10 [overflow-anchor:auto]"
            ref={scrollContainerRef}
            onScroll={handleScroll}
          >
            <div className="mx-auto flex max-w-3xl flex-col gap-6">
              {/* Empty state */}
              {!activeSession && !isLoadingMessages && activeMessages.length === 0 && (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-900">
                    <IconMessage className="h-7 w-7 text-neutral-500" />
                  </div>
                  <p className="text-base font-medium text-neutral-400">Select a chat to view messages</p>
                  <p className="mt-1 text-sm text-neutral-600">Or start a new conversation</p>
                </div>
              )}

              {/* Loading spinner */}
              {isLoadingMessages && (
                <div className="flex items-center justify-center py-24">
                  <IconLoader2 className="h-6 w-6 animate-spin text-neutral-500" />
                </div>
              )}

              {/* Messages */}
              {activeMessages.map((message, index) => (
                <div
                  key={`${message.role}-${index}-${message.created_at}`}
                  className={message.role === "human" ? "group flex justify-end" : "group flex justify-start"}
                >
                  <div className={`flex flex-col gap-2 ${message.role === "human" ? "max-w-[80%] items-end" : "w-full"}`}>
                    {/* File references */}
                    {message.role === "human" && message.file_references.length > 0 && (
                      <div className="flex flex-col items-end gap-2">
                        {message.file_references.map((ref, idx) => {
                          const isVideo = ref.content_type?.startsWith("video/") || ref.file_type?.startsWith("video");
                          const isAudio = ref.content_type?.startsWith("audio/") || ref.file_type?.startsWith("audio");
                          const mediaUrl = ref.file_url?.startsWith("http") || ref.file_url?.startsWith("blob:")
                            ? ref.file_url
                            : ref.file_url
                              ? `${import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || "http://localhost:8000"}${ref.file_url.startsWith("/") ? "" : "/"}${ref.file_url}`
                              : "";

                          if (isVideo && mediaUrl) {
                            return (
                              <div key={ref.document_id || idx} className="flex max-w-sm flex-col gap-2 overflow-hidden rounded-2xl border border-neutral-800 bg-black p-2 shadow-sm">
                                <video src={mediaUrl} controls className="max-h-64 w-full rounded-lg bg-black object-contain" />
                                <span className="truncate px-2 pb-1 text-xs font-medium text-neutral-400">{ref.file_name}</span>
                              </div>
                            );
                          }

                          if (isAudio && mediaUrl) {
                            return (
                              <div key={ref.document_id || idx} className="flex w-72 max-w-full flex-col gap-2 overflow-hidden rounded-2xl border border-neutral-800 bg-black p-2 shadow-sm">
                                <audio src={mediaUrl} controls className="h-10 w-full" />
                                <span className="truncate px-2 pb-1 text-xs font-medium text-neutral-400">{ref.file_name}</span>
                              </div>
                            );
                          }

                          return (
                            <div
                              key={ref.document_id || idx}
                              className="flex w-fit max-w-full items-center gap-3 rounded-2xl border border-neutral-800 bg-black p-2 pr-4 shadow-sm"
                            >
                              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-red-500/90 text-white shadow-inner">
                                <IconFile className="h-6 w-6" />
                              </div>
                              <div className="flex flex-col overflow-hidden">
                                <span className="truncate text-sm font-semibold text-white">
                                  {ref.file_name}
                                </span>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                                  {ref.file_type || "Document"}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <div
                      className={
                        message.role === "human"
                          ? "rounded-2xl rounded-tr-sm bg-neutral-800 px-4 py-2.5 text-sm text-neutral-100"
                          : "flex-1 text-sm text-neutral-100"
                      }
                    >
                      {/* Typing indicator for empty AI message while streaming */}
                      {message.role === "ai" && !message.content && isSending ? (
                        <div className="flex items-center gap-1 py-2">
                          <span className="h-2 w-2 animate-pulse rounded-full bg-neutral-500" style={{ animationDelay: "0ms" }} />
                          <span className="h-2 w-2 animate-pulse rounded-full bg-neutral-500" style={{ animationDelay: "150ms" }} />
                          <span className="h-2 w-2 animate-pulse rounded-full bg-neutral-500" style={{ animationDelay: "300ms" }} />
                        </div>
                      ) : (
                        <>
                          {/* Message content — ReactMarkdown */}
                          <ReactMarkdown
                            components={{
                              p: ({ children }) => <p className="mb-1 text-sm leading-relaxed">{processMarkdownChildren(children)}</p>,
                              ul: ({ children }) => <ul className="mb-1 list-disc space-y-0.5 pl-5 text-sm">{processMarkdownChildren(children)}</ul>,
                              ol: ({ children }) => <ol className="mb-1 list-decimal space-y-0.5 pl-5 text-sm">{processMarkdownChildren(children)}</ol>,
                              li: ({ children }) => <li className="leading-relaxed">{processMarkdownChildren(children)}</li>,
                              strong: ({ children }) => <strong className="font-semibold text-white">{processMarkdownChildren(children)}</strong>,
                              em: ({ children }) => <em className="italic text-neutral-300">{processMarkdownChildren(children)}</em>,
                              code: ({ className, children, ...props }) => {
                                const match = /language-(\w+)/.exec(className || "");
                                return match ? (
                                  <CodeBlock language={match[1]} value={String(children).replace(/\n$/, "")} />
                                ) : (
                                  <code className="rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-[13px] text-emerald-400" {...props}>
                                    {children}
                                  </code>
                                );
                              },
                              h1: ({ children }) => <h1 className="mb-1 text-lg font-bold text-white">{children}</h1>,
                              h2: ({ children }) => <h2 className="mb-1 text-base font-semibold text-white">{children}</h2>,
                              h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold text-neutral-200">{children}</h3>,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                          {/* Blinking cursor while AI response is streaming */}
                          {message.role === "ai" && isSending && index === activeMessages.length - 1 && (
                            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400" />
                          )}
                        </>
                      )}
                    </div>

                    {/* Action Toolbar & Token usage */}
                    <div className={`flex flex-col ${message.role === "human" ? "items-end" : "items-start"}`}>
                      {message.content && !(isSending && index === activeMessages.length - 1) && (
                        <MessageActionToolbar text={message.content} isHuman={message.role === "human"} />
                      )}

                      {/* Token usage footer for AI messages */}
                      {message.role === "ai" && message.completion_tokens != null && (
                        <p className="mt-1.5 text-[11px] text-neutral-600">
                          <span className="text-neutral-500">Completion:</span>{" "}
                          {message.completion_tokens.toLocaleString()} tokens
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              <div ref={messagesEndRef} />
            </div>

            {showScrollToBottom && (
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
                <button
                  onClick={scrollToBottom}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-800 border border-neutral-700 text-neutral-300 shadow-2xl hover:bg-neutral-700 hover:text-white transition-all pointer-events-auto active:scale-95"
                  aria-label="Scroll to bottom"
                >
                  <ArrowDown className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-neutral-800 p-4">
          <div className="mx-auto max-w-3xl">
            {attachedFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap items-center gap-2">
                {attachedFiles.map((af, idx) => (
                  <div
                    key={`${af.file.name}-${idx}`}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-colors ${af.status === "error"
                      ? "border-red-700 bg-red-950/40 text-red-300"
                      : af.status === "uploading"
                        ? "border-neutral-700 bg-neutral-900 text-neutral-400"
                        : "border-neutral-800 bg-black text-neutral-300"
                      }`}
                  >
                    {af.status === "uploading" ? (
                      <IconLoader2 className="h-4 w-4 animate-spin text-neutral-500" />
                    ) : (
                      fileIcon(af.file)
                    )}
                    <span className="max-w-[140px] truncate">
                      {af.file.name}
                    </span>
                    {af.status === "uploaded" && (
                      <span className="text-emerald-400">✓</span>
                    )}
                    {af.status === "error" && (
                      <span title={af.error}>✗</span>
                    )}
                    <button
                      className="ml-1 shrink-0 text-neutral-500 transition hover:text-white"
                      onClick={() => handleRemoveSingleFile(idx)}
                      type="button"
                      aria-label={`Remove ${af.file.name}`}
                    >
                      <IconX className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}

                {/* Clear all button */}
                {attachedFiles.length > 1 && (
                  <button
                    className="rounded-md px-2 py-1 text-xs text-neutral-500 transition hover:bg-neutral-800 hover:text-white"
                    onClick={handleRemoveFiles}
                    type="button"
                  >
                    Clear all
                  </button>
                )}
              </div>
            )}

            <PlaceholdersAndVanishInput
              className="max-w-none border border-neutral-800 bg-black shadow-none dark:bg-black"
              disabled={isUploading}
              leftSlot={
                <label
                  className={`flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl transition-opacity duration-200 ${isUploading
                    ? "pointer-events-none opacity-30"
                    : "opacity-100 text-neutral-300 hover:bg-neutral-900 hover:text-white"
                    }`}
                >
                  <IconPaperclip className="h-5 w-5" />
                  <input
                    ref={fileInputRef}
                    accept="application/pdf,video/*,audio/*"
                    className="sr-only"
                    multiple
                    onChange={handleFileChange}
                    type="file"
                    disabled={isUploading}
                  />
                </label>
              }
              onChange={(e) => { queryRef.current = e.target.value; }}
              onSubmit={handleSubmit}
              onStop={handleStopChat}
              isStreaming={isSending}
              placeholders={placeholders}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
