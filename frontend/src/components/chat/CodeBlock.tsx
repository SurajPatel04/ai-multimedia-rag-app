import React, { useState } from "react";
import { Copy, Check } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export const CodeBlock = ({ language, value }: { language: string; value: string }) => {
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
        style={vscDarkPlus as any}
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
