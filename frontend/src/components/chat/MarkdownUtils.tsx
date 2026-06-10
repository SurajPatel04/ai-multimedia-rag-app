import React, { Fragment } from "react";
import { IconFileText } from "@tabler/icons-react";

// Global Media Player
let activeTimeUpdateRef: { element: HTMLMediaElement; listener: () => void } | null = null;

export const handlePlayMedia = (startSeconds: number, endSeconds: number, event?: React.MouseEvent) => {
  let mediaElement: HTMLMediaElement | null = null;

  if (event) {
    const button = event.currentTarget as HTMLElement;
    const container = button.closest(".chat-message-group");
    if (container) {
      mediaElement = container.querySelector("video, audio") as HTMLMediaElement;
    }

    if (!mediaElement) {
      const allPlayers = Array.from(document.querySelectorAll("video, audio")) as HTMLMediaElement[];
      const previousPlayers = allPlayers.filter(p =>
        p.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING
      );
      if (previousPlayers.length > 0) {
        mediaElement = previousPlayers[previousPlayers.length - 1]; // Pick the closest one above
      }
    }
  }

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

export const renderTextWithEnhancements = (text: string, fileNames: string[] = [], onPdfClick?: (name: string, page: number, query?: string) => void) => {
  // Matches timestamps: [00:00 - 00:00] or 00:00 - 00:00
  const timestampRegex = /(?:\[(?:.*?\|\s*)?)?\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-–]\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b(?:\])?/g;

  // Document Page Match: [filename.pdf | Page 2] or [filename.docx | Page 2 | "quote"]
  const pdfPageRegex = /\[([^\|\]]+\.(?:pdf|docx|doc|xlsx|xls|csv))\s*\|\s*Page\s*(\d+)(?:\s*\|\s*["']?(.*?)["']?)?\]/gi;

  // Matches known filenames exactly, fallback to common regex
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

  // Find PDF Pages
  let pMatch;
  while ((pMatch = pdfPageRegex.exec(text)) !== null) {
    if (matches.some(m => pMatch!.index >= m.index && pMatch!.index < m.index + m.length)) continue;

    const fileName = pMatch[1].trim();
    const pageNum = parseInt(pMatch[2], 10);
    const exactQuote = pMatch[3]?.trim();

    // Extract preceding text as search query fallback
    const snippetBefore = text.substring(Math.max(0, pMatch.index - 150), pMatch.index);
    let fallbackQuery = snippetBefore
      .split(/(?:\n|\.\s|\?\s|\!\s)/) // split by newlines or sentence endings
      .pop()?.trim()
      .replace(/^["'\s]+|["'\s]+$/g, '') // Remove trailing/leading quotes
      .replace(/[*_~`]/g, "") || undefined;

    // If fallback is too long, trim to last 8 words
    if (fallbackQuery && fallbackQuery.split(' ').length > 8) {
      fallbackQuery = fallbackQuery.split(' ').slice(-8).join(' ');
    }

    const searchQuery = exactQuote || fallbackQuery;

    matches.push({
      index: pMatch.index,
      length: pMatch[0].length,
      content: (
        <button
          key={`pdf-${pMatch.index}`}
          type="button"
          className="mx-1 inline-flex items-center rounded border border-white/20 bg-white/10 px-1.5 py-0.5 text-[11px] font-bold text-white transition-colors hover:bg-white/20"
          onClick={() => onPdfClick && onPdfClick(fileName, pageNum, searchQuery)}
        >
          <IconFileText className="mr-1 h-3 w-3" /> {fileName} | Page {pageNum}
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

export const processMarkdownChildren = (children: React.ReactNode, fileNames: string[] = [], onPdfClick?: (name: string, page: number, query?: string) => void): React.ReactNode => {
  if (typeof children === "string") {
    return renderTextWithEnhancements(children, fileNames, onPdfClick);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => <Fragment key={i}>{processMarkdownChildren(child, fileNames, onPdfClick)}</Fragment>);
  }
  return children;
};
