import React from "react";

type Block =
  | { type: "h1" | "h2" | "h3"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "p"; text: string }
  | { type: "empty" };

function parseInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-neutral-800 px-1 py-0.5 font-mono text-xs text-emerald-400"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Headings
    if (line.startsWith("### ")) {
      blocks.push({ type: "h3", text: line.slice(4) });
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push({ type: "h2", text: line.slice(3) });
      i++;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push({ type: "h1", text: line.slice(2) });
      i++;
      continue;
    }

    // Unordered list — * item, - item, • item
    if (/^(\*|-|•)\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^(\*|-|•)\s/.test(lines[i])) {
        items.push(lines[i].replace(/^(\*|-|•)\s/, ""));
        i++;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    // Ordered list — "1. item"
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ""));
        i++;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      blocks.push({ type: "empty" });
      i++;
      continue;
    }

    // Paragraph
    blocks.push({ type: "p", text: line });
    i++;
  }

  return blocks;
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const blocks = parseBlocks(content);

  return (
    <div className={`space-y-2 leading-relaxed ${className}`}>
      {blocks.map((block, idx) => {
        switch (block.type) {
          case "h1":
            return (
              <h1 key={idx} className="text-lg font-bold text-white">
                {parseInline(block.text)}
              </h1>
            );
          case "h2":
            return (
              <h2 key={idx} className="text-base font-semibold text-white">
                {parseInline(block.text)}
              </h2>
            );
          case "h3":
            return (
              <h3 key={idx} className="text-sm font-semibold text-neutral-200">
                {parseInline(block.text)}
              </h3>
            );
          case "ul":
            return (
              <ul key={idx} className="list-disc space-y-1 pl-5 text-sm">
                {block.items.map((item, ii) => (
                  <li key={ii}>{parseInline(item)}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={idx} className="list-decimal space-y-1 pl-5 text-sm">
                {block.items.map((item, ii) => (
                  <li key={ii}>{parseInline(item)}</li>
                ))}
              </ol>
            );
          case "empty":
            return <div key={idx} className="h-1" />;
          case "p":
          default:
            return (
              <p key={idx} className="text-sm">
                {parseInline(block.text)}
              </p>
            );
        }
      })}
    </div>
  );
}
