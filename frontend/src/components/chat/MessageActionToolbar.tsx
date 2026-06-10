import React, { useState } from "react";
import { Copy, Check } from "lucide-react";

export const MessageActionToolbar = ({ text, isHuman }: { text: string; isHuman?: boolean }) => {
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
