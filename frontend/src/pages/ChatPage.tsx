import React, { useCallback, useEffect, useRef, useState, Fragment } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import ragIcon from "@/assets/rag.png";
import { motion, AnimatePresence } from "motion/react";
import { ArrowDown, Copy, Check } from "lucide-react";
import {
  IconArrowLeft,
  IconBrandGithub,
  IconDots,
  IconFile,
  IconFileText,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconLoader2,
  IconMessage,
  IconMusic,
  IconPaperclip,
  IconPencil,
  IconPlus,
  IconTrash,
  IconVideo,
  IconX,
} from "@tabler/icons-react";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { authService, type User } from "@/services/authService";
import {
  uploadFiles,
  cancelFile,
  type UploadedFileInfo,
} from "@/services/fileUploadService";
import {
  chatService,
  type ChatSession,
  type ChatMessage,
  type SSEEvent,
} from "@/services/chatService";
import { ConfirmationModal } from "@/components/ui/confirmation-modal";
import { showToast } from "@/lib/toast";





const placeholders = [
  "Ask anything about this assignment",
  "Upload a PDF, audio, or video file",
  "Summarize this file",
  "What should we build next?",
];

// Global Media Player
let activeTimeUpdateRef: { element: HTMLMediaElement; listener: () => void } | null = null;

const handlePlayMedia = (startSeconds: number, endSeconds: number, event?: React.MouseEvent) => {
  let mediaElement: HTMLMediaElement | null = null;

  if (event) {
    const button = event.currentTarget as HTMLElement;
    // 1. Target the player in the immediate message container first
    const container = button.closest(".chat-message-group");
    if (container) {
      mediaElement = container.querySelector("video, audio") as HTMLMediaElement;
    }

    // 2. If not found in current message, find the nearest player ABOVE this button
    if (!mediaElement) {
      const allPlayers = Array.from(document.querySelectorAll("video, audio")) as HTMLMediaElement[];
      // Filter players that are physically above the button in the DOM
      const previousPlayers = allPlayers.filter(p =>
        p.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING
      );
      if (previousPlayers.length > 0) {
        mediaElement = previousPlayers[previousPlayers.length - 1]; // Pick the closest one above
      }
    }
  }

  // 3. Fallback to the very first player if no previous ones found
  if (!mediaElement) {
    mediaElement = document.querySelector("video, audio") as HTMLMediaElement;
  }

  if (!mediaElement) return;

  // Scroll to the player so the user can see it
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

const renderTextWithEnhancements = (text: string, fileNames: string[] = []) => {
  // 1. Matches timestamps: [00:00 - 00:00] or 00:00 - 00:00
  const timestampRegex = /(?:\[(?:.*?\|\s*)?)?\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-–]\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b(?:\])?/g;

  // 2. Matches known filenames exactly, fallback to common regex
  const escapedNames = fileNames
    .map(name => name.trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

  const knownFilesRegex = escapedNames.length > 0 
    ? new RegExp(`(?<=^|\\s|["'\\[\\(\\{])(${escapedNames.join("|")})(?=$|\\s|["'\\]\\)\\},:;.!?])`, 'gi')
    : null;

  const fallbackFileRegex = /\b([\w-]+\.(?:pdf|mp4|mp3|wav|mov|avi|doc|docx|txt))\b/gi;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  const matches: { index: number; length: number; content: React.ReactNode }[] = [];

  // Find Timestamps
  let tMatch;
  while ((tMatch = timestampRegex.exec(text)) !== null) {
    const startHours = tMatch[1] ? parseInt(tMatch[1], 10) : 0;
    const startMins = parseInt(tMatch[2], 10);
    const startSecs = parseInt(tMatch[3], 10);
    const startSeconds = startHours * 3600 + startMins * 60 + startSecs;

    const endHours = tMatch[4] ? parseInt(tMatch[4], 10) : 0;
    const endMins = parseInt(tMatch[5], 10);
    const endSecs = parseInt(tMatch[6], 10);
    const endSeconds = endHours * 3600 + endMins * 60 + endSecs;

    const timeLabel = `[${tMatch[1] ? tMatch[1] + ":" : ""}${tMatch[2]}:${tMatch[3]} - ${tMatch[4] ? tMatch[4] + ":" : ""}${tMatch[5]}:${tMatch[6]}]`;

    matches.push({
      index: tMatch.index,
      length: tMatch[0].length,
      content: (
        <button
          key={`ts-${tMatch.index}`}
          type="button"
          className="mx-1 inline-flex items-center rounded border border-white/20 bg-white/10 px-1.5 py-0.5 text-[11px] font-bold text-white transition-colors hover:bg-white/20"
          onClick={(e) => handlePlayMedia(startSeconds, endSeconds, e)}
        >
          <span className="mr-1 text-[9px]">▶</span> {timeLabel}
        </button>
      )
    });
  }

  // Find Known Filenames
  if (knownFilesRegex) {
    let kMatch;
    while ((kMatch = knownFilesRegex.exec(text)) !== null) {
      if (matches.some(m => kMatch!.index >= m.index && kMatch!.index < m.index + m.length)) continue;

      matches.push({
        index: kMatch.index,
        length: kMatch[0].length,
        content: (
          <span
            key={`file-k-${kMatch.index}`}
            className="mx-0.5 rounded-none bg-white/10 border border-white/30 px-1.5 py-0.5 font-mono text-[12px] font-bold text-white shadow-sm"
          >
            {kMatch[1]}
          </span>
        )
      });
    }
  }

  // Find Fallback Filenames
  let fMatch;
  while ((fMatch = fallbackFileRegex.exec(text)) !== null) {
    if (matches.some(m => fMatch!.index >= m.index && fMatch!.index < m.index + m.length)) continue;

    matches.push({
      index: fMatch.index,
      length: fMatch[0].length,
      content: (
        <span
          key={`file-${fMatch.index}`}
          className="mx-0.5 rounded-none bg-white/10 border border-white/30 px-1.5 py-0.5 font-mono text-[12px] font-bold text-white shadow-sm"
        >
          {fMatch[0]}
        </span>
      )
    });
  }

  // Sort matches by index
  matches.sort((a, b) => a.index - b.index);

  // Build the final parts array
  matches.forEach(match => {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    parts.push(match.content);
    lastIndex = match.index + match.length;
  });

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length === 0 ? text : parts;
};

const processMarkdownChildren = (children: React.ReactNode, fileNames: string[] = []): React.ReactNode => {
  if (typeof children === "string") {
    return renderTextWithEnhancements(children, fileNames);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => <Fragment key={i}>{processMarkdownChildren(child, fileNames)}</Fragment>);
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
    <div className="my-4 overflow-hidden rounded-none border border-white/20 text-[13px] bg-black shadow-[4px_4px_0px_0px_rgba(255,255,255,0.05)]">
      <div className="flex items-center justify-between border-b border-white/10 bg-neutral-900/50 px-4 py-2 text-xs font-bold uppercase tracking-widest text-neutral-400">
        <span className="font-mono">{language}</span>
        <button onClick={handleCopy} className="flex items-center gap-1.5 hover:text-white transition-colors" type="button">
          {copied ? <Check className="h-3.5 w-3.5 text-white" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied!" : "Copy code"}
        </button>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: "1.25rem",
          backgroundColor: "transparent",
          fontSize: "13px",
          lineHeight: "1.6",
        }}
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
    <div className={`mt-0.5 flex items-center gap-2 text-neutral-500 transition-opacity duration-200 ${isHuman ? "opacity-100 sm:opacity-0 sm:group-hover:opacity-100" : "opacity-100"}`}>
      <button
        onClick={handleCopy}
        className="flex items-center justify-center rounded p-1 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
        title="Copy message"
        type="button"
      >
        {copied ? <Check className="h-4 w-4 text-white" /> : <Copy className="h-4 w-4" />}
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
    setIsRenaming(false);
    onRenameSubmit(session.session_id, trimmed);
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
  const [open, setOpen] = useState(window.innerWidth >= 768);
  const [user, setUser] = useState<User | null>(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isMobileProfileMenuOpen, setIsMobileProfileMenuOpen] = useState(false);
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
  const knownFileNames = Array.from(
    new Set(
      activeMessages.flatMap((m) => m.file_references.map((r) => r.file_name))
    )
  ).filter(Boolean);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isScrolledUpRef = useRef(false);
  const lastLoadedSessionIdRef = useRef<string | null>(null);

  const [menuOpenSessionId, setMenuOpenSessionId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const profileToggleRef = useRef<HTMLButtonElement>(null);
  const mobileProfileMenuRef = useRef<HTMLDivElement>(null);
  const mobileProfileToggleRef = useRef<HTMLButtonElement>(null);

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    isDanger?: boolean;
    confirmText?: string;
  }>({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: () => { },
  });

  const showConfirmation = (config: Omit<typeof confirmModal, "isOpen">) => {
    setConfirmModal({ ...config, isOpen: true });
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenSessionId(null);
      }

      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(e.target as Node) &&
        profileToggleRef.current &&
        !profileToggleRef.current.contains(e.target as Node)
      ) {
        setIsProfileMenuOpen(false);
      }

      if (
        mobileProfileMenuRef.current &&
        !mobileProfileMenuRef.current.contains(e.target as Node) &&
        mobileProfileToggleRef.current &&
        !mobileProfileToggleRef.current.contains(e.target as Node)
      ) {
        setIsMobileProfileMenuOpen(false);
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

    // Store old title for potential revert
    const oldSession = sessions.find(s => s.session_id === sessionId);
    const oldTitle = oldSession?.title || "";

    // Optimistic Update
    setSessions((prev) =>
      prev.map((s) => s.session_id === sessionId ? { ...s, title: trimmed } : s)
    );
    if (activeSession?.session_id === sessionId) {
      setActiveSession((prev) => prev ? { ...prev, title: trimmed } : prev);
    }

    try {
      const res = await chatService.renameSession(sessionId, trimmed);
      if (res.success) {
        showToast.success("Chat renamed");
        // Update with server returned title just in case it's different
        setSessions((prev) =>
          prev.map((s) => s.session_id === sessionId ? { ...s, title: res.data.title } : s)
        );
        if (activeSession?.session_id === sessionId) {
          setActiveSession((prev) => prev ? { ...prev, title: res.data.title } : prev);
        }
      }
    } catch (err) {
      showToast.error("Failed to rename session");
      // Revert on failure
      setSessions((prev) =>
        prev.map((s) => s.session_id === sessionId ? { ...s, title: oldTitle } : s)
      );
      if (activeSession?.session_id === sessionId) {
        setActiveSession((prev) => prev ? { ...prev, title: oldTitle } : prev);
      }
      console.error("Failed to rename session", err);
    }
  }, [sessions, activeSession]);

  // Delete session handler
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    const sessionToDelete = sessions.find(s => s.session_id === sessionId);
    const sessionTitle = sessionToDelete?.title || "this chat";

    showConfirmation({
      title: "Delete Chat",
      message: `Are you sure you want to delete "${sessionTitle}"? This action cannot be undone.`,
      confirmText: "Delete",
      isDanger: true,
      onConfirm: async () => {
        try {
          await chatService.deleteSession(sessionId);
          showToast.success("Chat deleted");
          setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
          if (activeSession?.session_id === sessionId) {
            setActiveSession(null);
            setSessionId(null);
            setActiveMessages([]);
            setSearchParams({}, { replace: true });
            lastLoadedSessionIdRef.current = null;
          }
        } catch (err) {
          showToast.error("Failed to delete chat");
          console.error("Failed to delete session", err);
        } finally {
          setMenuOpenSessionId(null);
        }
      }
    });
  }, [activeSession, sessions, setSearchParams]);

  const handleScroll = () => {
    if (scrollContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
      // Only show button if content is actually scrollable and we are far from bottom
      const canScroll = scrollHeight > clientHeight + 10;
      const isScrolledUp = canScroll && (scrollHeight - scrollTop - clientHeight > 100);
      isScrolledUpRef.current = isScrolledUp;
      setShowScrollToBottom(isScrolledUp);
    }
  };

  const scrollToBottom = () => {
    isScrolledUpRef.current = false;
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
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [tempId, setTempId] = useState<string | null>(null);

  // Clear tempId if no files are attached
  useEffect(() => {
    if (attachedFiles.length === 0 && tempId) {
      setTempId(null);
      tempIdSentRef.current = false;
    }
  }, [attachedFiles.length, tempId]);

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

  // Auto-scroll logic for streaming and session load
  useEffect(() => {
    if (isSending && !isScrolledUpRef.current) {
      // Use "auto" for streaming to keep it snappy and locked to bottom
      messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [activeMessages.length, isSending]);

  // Handle auto-scroll on content updates (streaming text)
  useEffect(() => {
    if (isSending && activeMessages.length > 0 && !isScrolledUpRef.current) {
      const lastMessage = activeMessages[activeMessages.length - 1];
      if (lastMessage.role === "ai") {
        messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
      }
    }
  }, [activeMessages[activeMessages.length - 1]?.content]);

  useEffect(() => {
    if (!isLoadingMessages && activeMessages.length > 0) {
      // Smooth scroll only on initial load or navigation
      isScrolledUpRef.current = false;
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [isLoadingMessages]);
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
      if (res.success && lastLoadedSessionIdRef.current === session.session_id) {
        setActiveMessages(res.data.messages);
      }
    } catch (err) {
      console.error("Failed to load session messages", err);
    } finally {
      if (lastLoadedSessionIdRef.current === session.session_id) {
        setIsLoadingMessages(false);
      }
    }
  }, []);

  const closeSidebarOnMobile = useCallback(() => {
    if (window.innerWidth < 768) {
      setOpen(false);
    }
  }, [setOpen]);

  const handleSessionClick = useCallback(
    (session: ChatSession) => {
      if (session.session_id === lastLoadedSessionIdRef.current) {
        closeSidebarOnMobile();
        return;
      }
      setSearchParams({ session: session.session_id }, { replace: false });
      loadSession(session);
      closeSidebarOnMobile();
    },
    [setSearchParams, loadSession, closeSidebarOnMobile]
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



  const handleLogout = () => {
    showConfirmation({
      title: "Logout",
      message: "Are you sure you want to log out of your account?",
      confirmText: "Logout",
      isDanger: true,
      onConfirm: async () => {
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
      }
    });
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
      const MAX_SIZE = 50 * 1024 * 1024; // 50MB
      const ALLOWED_TYPES = ["application/pdf", "video/", "audio/"];

      const validFiles: File[] = [];
      for (const file of newFiles) {
        const isTypeAllowed = ALLOWED_TYPES.some((type) =>
          file.type.startsWith(type)
        );

        if (!isTypeAllowed) {
          showToast.error(`File type not allowed: ${file.name}. Please upload PDF, Video, or Audio.`);
          continue;
        }

        if (file.size > MAX_SIZE) {
          showToast.error(`File too large: ${file.name}. Max size is 50MB.`);
          continue;
        }

        // Check for duplicates (same name and size)
        const isDuplicate = attachedFiles.some(
          (af) => af.file.name === file.name && af.file.size === file.size
        );

        if (isDuplicate) {
          showToast.warning(`File "${file.name}" is already uploaded.`);
          continue;
        }

        validFiles.push(file);
      }

      if (validFiles.length === 0) {
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      const existingFiles = attachedFiles.filter(
        (af) => af.status === "uploaded"
      );
      const pendingNew: AttachedFile[] = validFiles.map((f) => ({
        file: f,
        status: "uploading" as const,
      }));
      setAttachedFiles([...existingFiles, ...pendingNew]);
      setIsUploading(true);

      const allFiles = [
        ...existingFiles.map((af) => af.file),
        ...validFiles,
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
        showToast.error(message);
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

  // Remove a single file
  const handleRemoveSingleFile = useCallback(async (index: number) => {
    const fileToRemove = attachedFiles[index];
    if (!fileToRemove) return;

    // 1. Abort if still uploading
    if (fileToRemove.status === "uploading" && uploadAbortControllerRef.current) {
      uploadAbortControllerRef.current.abort();
    }

    // 2. Remove from UI state
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));

    // 3. If already uploaded, notify backend
    if (fileToRemove.status === "uploaded" && tempId && fileToRemove.serverInfo?.file_id) {
      try {
        await cancelFile(tempId, fileToRemove.serverInfo.file_id);
      } catch (err) {
        console.error("Failed to cancel file on server", err);
      }
    }
  }, [attachedFiles, tempId]);

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
        isScrolledUpRef.current = false;
        scrollToBottom();
      }, 350);

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

  const getFileInfo = (file: File) => {
    const type = file.type;
    const name = file.name.toLowerCase();
    if (type.startsWith("audio/")) return { icon: <IconMusic className="h-4 w-4" />, color: "bg-neutral-800", label: "Audio" };
    if (type.startsWith("video/")) return { icon: <IconVideo className="h-4 w-4" />, color: "bg-neutral-800", label: "Video" };
    if (type === "application/pdf") return { icon: <IconFileText className="h-4 w-4" />, color: "bg-neutral-800", label: "PDF" };
    if (type.includes("spreadsheet") || name.endsWith(".xlsx") || name.endsWith(".xls") || name.endsWith(".csv"))
      return { icon: <IconFile className="h-4 w-4" />, color: "bg-neutral-800", label: "Spreadsheet" };
    return { icon: <IconFile className="h-4 w-4" />, color: "bg-neutral-800", label: "File" };
  };

  return (
    <section className="flex h-screen w-full flex-col md:flex-row overflow-hidden bg-black">
      <Sidebar autoOpen={false} open={open} setOpen={setOpen}>
        <SidebarBody
          className="justify-between gap-6 border-r border-neutral-800 bg-black"
          centerContent={
            <span className="text-sm font-semibold text-white truncate max-w-[200px]">
              {activeSession ? activeSession.title : "Chat"}
            </span>
          }
          rightContent={
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/SurajPatel04"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-neutral-400 hover:text-white transition-colors"
                title="GitHub Repository"
              >
                <IconBrandGithub className="h-5 w-5" />
              </a>
              {user ? (
                <div className="relative">
                  <button
                    ref={mobileProfileToggleRef}
                    onClick={() => setIsMobileProfileMenuOpen((prev) => !prev)}
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-800 text-xs font-medium text-white border border-neutral-700 hover:bg-neutral-700 transition"
                    type="button"
                  >
                    {getInitials(user)}
                  </button>
                  <AnimatePresence>
                    {isMobileProfileMenuOpen && (
                      <motion.div
                        ref={mobileProfileMenuRef}
                        initial={{ opacity: 0, y: -10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.95 }}
                        transition={{ duration: 0.15, ease: "easeOut" }}
                        className="absolute top-12 right-0 z-50 w-64 rounded-xl border border-neutral-800 bg-neutral-900 p-2 shadow-2xl"
                      >
                        <div className="mb-2 truncate px-2 py-1.5 text-sm font-medium text-neutral-300 text-left">
                          {user.email}
                        </div>
                        <div className="h-px bg-neutral-800 mb-2"></div>
                        <button
                          className="flex w-full items-center justify-start gap-2 rounded-lg px-2 py-2 text-sm text-red-400 transition hover:bg-neutral-800 hover:text-red-300"
                          onClick={() => {
                            setIsMobileProfileMenuOpen(false);
                            handleLogout();
                          }}
                          type="button"
                        >
                          <IconArrowLeft className="h-4 w-4 shrink-0" />
                          <span>Logout</span>
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ) : null}
            </div>
          }
        >
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className={`group/sidebar-toggle relative z-20 flex h-16 items-center gap-2 py-1 ${open ? "justify-start" : "justify-center"}`}>
              <Link
                aria-label="InsightFlow"
                className="flex h-12 shrink-0 items-center justify-start rounded-lg bg-transparent outline-none focus:outline-none -ml-1"
                to="/chat"
              >
                <img src={ragIcon} alt="RAG Icon" className="h-10 w-10 object-contain" />
              </Link>
              {open ? (
                <span className="text-sm font-semibold text-white">InsightFlow</span>
              ) : null}
              <button
                aria-label={open ? "Collapse sidebar" : "Open sidebar"}
                className={
                  cn(
                    "ml-auto h-9 w-9 items-center justify-center rounded-md text-neutral-300 transition hover:bg-neutral-900 hover:text-white outline-none focus:outline-none focus:bg-neutral-900 active:bg-neutral-800 hidden md:flex",
                    !open && "absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-neutral-900/90 opacity-0 group-hover/sidebar-toggle:opacity-100 backdrop-blur-sm"
                  )
                }
                onClick={() => setOpen((value) => !value)}
                type="button"
              >
                {open ? (
                  <IconLayoutSidebarLeftCollapse className="h-6 w-6" />
                ) : (
                  <IconLayoutSidebarLeftExpand className="h-6 w-6" />
                )}
              </button>
            </div>

            <div className="mt-1 flex flex-col gap-2">
              <SidebarLink
                link={{
                  label: "New chat",
                  href: "/chat",
                  icon: <IconPlus className="h-6 w-6 shrink-0 text-neutral-200" />,
                }}
                onClick={closeSidebarOnMobile}
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
            <AnimatePresence>
              {isProfileMenuOpen && user && (
                <motion.div
                  ref={profileMenuRef}
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute bottom-14 left-0 z-50 w-full rounded-xl border border-neutral-800 bg-neutral-900 p-2 shadow-2xl"
                >
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
                </motion.div>
              )}
            </AnimatePresence>

            <button
              ref={profileToggleRef}
              className={`group flex items-center transition-all duration-200 hover:bg-neutral-900 ${open
                ? "w-full gap-3 rounded-lg p-2"
                : "h-10 w-10 justify-center rounded-full mx-auto"
                }`}
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

      <div className="flex min-w-0 flex-1 flex-col h-full bg-neutral-950 overflow-hidden">
        <header className="hidden md:flex h-14 shrink-0 items-center justify-between border-b border-neutral-800 px-4 md:px-6 bg-black z-10">
          <div>
            <h1 className="text-sm font-semibold text-white truncate max-w-[500px]">
              {activeSession ? activeSession.title : "Chat"}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/SurajPatel04"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
              title="GitHub Repository"
            >
              <IconBrandGithub className="h-5 w-5" />
              <span className="text-xs font-medium">GitHub</span>
            </a>
          </div>
        </header>

        <div className="relative flex-1 min-h-0">
          <div
            className="h-full overflow-y-auto px-2 py-6 sm:px-4 md:px-10 [overflow-anchor:auto]"
            ref={scrollContainerRef}
            onScroll={handleScroll}
          >
            <div className={cn(
              "mx-auto flex max-w-3xl flex-col gap-6",
              (!activeSession && activeMessages.length === 0) ? "h-full justify-center" : ""
            )}>
              {/* Empty state */}
              {!activeSession && !isLoadingMessages && activeMessages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className="flex flex-col items-center justify-center py-4 md:py-8 text-center px-4"
                >


                  <h2 className="bg-gradient-to-br from-white to-neutral-500 bg-clip-text text-2xl md:text-5xl font-bold tracking-tight text-transparent mb-2 md:mb-4">
                    What can I help with?
                  </h2>
                  <p className="max-w-md text-sm md:text-base text-neutral-400 mb-6 md:mb-12">
                    Analyze documents, extract insights from media, and chat with your project's knowledge base.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-4xl px-2">
                    {[
                      {
                        title: "Document RAG",
                        desc: "Analyze PDFs for key information",
                        icon: <IconFile className="h-5 w-5 text-neutral-400" />,
                        bg: "hover:border-neutral-700"
                      },
                      {
                        title: "Media Intelligence",
                        desc: "Insights from video and audio content.",
                        icon: <IconVideo className="h-5 w-5 text-neutral-400" />,
                        bg: "hover:border-neutral-700"
                      },
                      {
                        title: "Project Memory",
                        desc: "Consistent context across all sessions.",
                        icon: <IconMessage className="h-5 w-5 text-neutral-400" />,
                        bg: "hover:border-neutral-700"
                      }
                    ].map((feature, i) => (
                      <motion.div
                        key={feature.title}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 * i + 0.3 }}
                        className={`flex flex-col items-start p-4 md:p-5 rounded-2xl border border-neutral-800 bg-neutral-900/50 backdrop-blur-sm transition-all duration-300 ${feature.bg} text-left group cursor-default`}
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 rounded-lg bg-neutral-800 group-hover:bg-neutral-700 transition-colors duration-300">
                            {feature.icon}
                          </div>
                          <h3 className="font-semibold text-white">{feature.title}</h3>
                        </div>
                        <p className="text-sm text-neutral-500 leading-snug">{feature.desc}</p>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Loading spinner */}
              {isLoadingMessages && (
                <div className="flex items-center justify-center py-24">
                  <IconLoader2 className="h-6 w-6 animate-spin text-neutral-500" />
                </div>
              )}

              {/* Messages */}
              <AnimatePresence initial={false}>
                {activeMessages.map((message, index) => (
                  <motion.div
                    key={`${message.role}-${message.message_index || index}`}
                    initial={{ opacity: 0, y: message.role === "human" ? 0 : 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.2,
                      delay: message.role === "human" ? 0.3 : 0,
                      ease: "easeOut"
                    }}
                    className={cn(
                      "chat-message-group",
                      message.role === "human" ? "group flex justify-end" : "group flex justify-start"
                    )}
                  >
                    <div className={`flex flex-col gap-2 ${message.role === "human" ? "max-w-[80%] items-end" : "w-full"}`}>
                      {/* File references */}
                      {message.role === "human" && message.file_references.length > 0 && (
                        <div className={`flex flex-col gap-2 ${message.role === "human" ? "items-end" : "items-start"}`}>
                          {Array.from(new Map(message.file_references.map(ref => [ref.file_name, ref])).values()).map((ref, idx) => {
                            const fileName = ref.file_name.toLowerCase().trim();
                            const isVideo = ref.content_type?.toLowerCase().includes("video") || ref.file_type?.toLowerCase().includes("video") || fileName.endsWith(".mp4") || fileName.endsWith(".mov") || fileName.endsWith(".webm");
                            const isAudio = ref.content_type?.toLowerCase().includes("audio") || ref.file_type?.toLowerCase().includes("audio") || fileName.endsWith(".mp3") || fileName.endsWith(".wav") || fileName.endsWith(".m4a") || fileName.includes("audio");
                            let mediaUrl = ref.file_url?.startsWith("http") || ref.file_url?.startsWith("blob:")
                              ? ref.file_url
                              : ref.file_url
                                ? `${import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || "http://localhost:8000"}${ref.file_url.startsWith("/") ? "" : "/"}${ref.file_url}`
                                : "";

                            // Rescue URL from previous references if missing in current chunk
                            if (!mediaUrl) {
                              const rescued = activeMessages
                                .flatMap(m => m.file_references)
                                .find(r => r.file_name === ref.file_name && r.file_url)?.file_url;

                              if (rescued) {
                                mediaUrl = rescued.startsWith("http") || rescued.startsWith("blob:")
                                  ? rescued
                                  : `${import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_URL || "http://localhost:8000"}${rescued.startsWith("/") ? "" : "/"}${rescued}`;
                              }
                            }

                            if ((isVideo || isAudio) && !mediaUrl) return null;

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
                        id={message.role === "human" ? `human-message-${message.message_index}` : undefined}
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
                                p: ({ children }) => <p className="mb-3 last:mb-0 text-sm leading-relaxed text-neutral-300">{processMarkdownChildren(children, knownFileNames)}</p>,
                                ul: ({ children }) => <ul className="mb-3 last:mb-0 list-disc space-y-1.5 pl-5 text-sm text-neutral-300">{processMarkdownChildren(children, knownFileNames)}</ul>,
                                ol: ({ children }) => <ol className="mb-3 last:mb-0 list-decimal space-y-1.5 pl-5 text-sm text-neutral-300">{processMarkdownChildren(children, knownFileNames)}</ol>,
                                li: ({ children }) => <li className="leading-relaxed">{processMarkdownChildren(children, knownFileNames)}</li>,
                                strong: ({ children }) => <strong className="font-bold text-white">{processMarkdownChildren(children, knownFileNames)}</strong>,
                                em: ({ children }) => <em className="italic text-neutral-400">{processMarkdownChildren(children, knownFileNames)}</em>,
                                code: ({ className, children, ...props }) => {
                                  const match = /language-(\w+)/.exec(className || "");
                                  return match ? (
                                    <CodeBlock language={match[1]} value={String(children).replace(/\n$/, "")} />
                                  ) : (
                                    <code className="rounded-none border border-white/20 bg-neutral-900 px-1.5 py-0.5 font-mono text-[13px] font-bold text-white" {...props}>
                                      {children}
                                    </code>
                                  );
                                },
                                h1: ({ children }) => <h1 className="mb-4 mt-6 text-xl font-black uppercase tracking-tighter text-white">{children}</h1>,
                                h2: ({ children }) => <h2 className="mb-3 mt-5 text-lg font-black uppercase tracking-tight text-white">{children}</h2>,
                                h3: ({ children }) => <h3 className="mb-2 mt-4 text-base font-bold text-neutral-200">{children}</h3>,
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
                  </motion.div>
                ))}
              </AnimatePresence>

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

        <div className="shrink-0 border-t border-neutral-800 bg-neutral-950 p-4">
          <div className="mx-auto max-w-3xl">
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
              activeMessagesCount={activeMessages.length}
              topContent={
                attachedFiles.length > 0 && (
                  <div className="mb-2 flex w-full items-center gap-3 overflow-x-auto scrollbar-hide pb-1">
                    {attachedFiles.map((af, idx) => {
                      const { icon, label } = getFileInfo(af.file);
                      return (
                        <div
                          key={`${af.file.name}-${idx}`}
                          className={`group relative flex w-64 shrink-0 items-center gap-3 rounded-xl border p-2 transition-all duration-200 ${af.status === "error"
                            ? "border-red-900/50 bg-red-950/20"
                            : "border-white/10 bg-[#0a0a0a] hover:border-white/20"
                            }`}
                        >
                          {/* Icon Box */}
                          <div className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/5 text-white shadow-sm",
                            af.status === "uploading" ? "bg-neutral-900" : "bg-white/5"
                          )}>
                            {af.status === "uploading" ? (
                              <IconLoader2 className="h-5 w-5 animate-spin" />
                            ) : (
                              icon
                            )}
                          </div>

                          {/* File Details */}
                          <div className="flex flex-1 flex-col min-w-0">
                            <span className="truncate text-sm font-bold text-white tracking-tight">
                              {af.file.name}
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500">
                              {af.status === "error" ? "Upload Failed" : af.status === "uploading" ? "Uploading..." : label}
                            </span>
                          </div>

                          {/* Remove Button */}
                          <button
                            className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-neutral-900 text-white border border-white/10 transition-all hover:bg-neutral-800"
                            onClick={() => handleRemoveSingleFile(idx)}
                            type="button"
                            aria-label={`Remove ${af.file.name}`}
                          >
                            <IconX className="h-3 w-3" />
                          </button>
                        </div>
                      );
                    })}

                  </div>
                )
              }
            />
          </div>
        </div>
      </div>
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        isDanger={confirmModal.isDanger}
      />
    </section>
  );
}
