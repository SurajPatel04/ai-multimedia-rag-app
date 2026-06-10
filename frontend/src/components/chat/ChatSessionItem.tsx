import React, { useState, useEffect, useRef } from "react";
import { IconDots, IconPencil, IconTrash } from "@tabler/icons-react";
import type { ChatSession } from "@/services/chatService";

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

export const ChatSessionItem = ({
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
