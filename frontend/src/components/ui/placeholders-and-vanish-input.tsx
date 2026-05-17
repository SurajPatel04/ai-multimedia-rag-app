"use client";

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export interface PlaceholdersAndVanishInputProps {
  placeholders: string[];
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void | Promise<void>;
  onStop?: () => void;
  leftSlot?: React.ReactNode;
  className?: string;
  disabled?: boolean;
  isStreaming?: boolean;
  topContent?: React.ReactNode;
  activeMessagesCount?: number;
}

export function PlaceholdersAndVanishInput({
  placeholders,
  onChange,
  onSubmit,
  onStop,
  leftSlot,
  className,
  disabled,
  isStreaming,
  topContent,
  activeMessagesCount,
}: PlaceholdersAndVanishInputProps) {
  const [currentPlaceholder, setCurrentPlaceholder] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startAnimation = () => {
    intervalRef.current = setInterval(() => {
      setCurrentPlaceholder((prev) => (prev + 1) % placeholders.length);
    }, 3000);
  };
  const handleVisibilityChange = () => {
    if (document.visibilityState !== "visible" && intervalRef.current) {
      clearInterval(intervalRef.current); // Clear the interval when the tab is not visible
      intervalRef.current = null;
    } else if (document.visibilityState === "visible") {
      startAnimation(); // Restart the interval when the tab becomes visible
    }
  };

  useEffect(() => {
    startAnimation();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [placeholders]);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [value, setValue] = useState("");
  const [isMultiline, setIsMultiline] = useState(false);

  // Flying bubble animation state
  const [flyingBubble, setFlyingBubble] = useState<{
    id: string;
    text: string;
    startRect: DOMRect;
    targetId: string;
  } | null>(null);
  const [animStep, setAnimStep] = useState<"start" | "flying" | "done">("start");
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (flyingBubble && animStep === "start") {
      const timer = setTimeout(() => {
        const targetEl = document.getElementById(flyingBubble.targetId);
        if (targetEl) {
          setTargetRect(targetEl.getBoundingClientRect());
          setAnimStep("flying");
        } else {
          setAnimStep("done");
        }
      }, 30);
      return () => clearTimeout(timer);
    }
  }, [flyingBubble, animStep]);

  const resizeTextarea = useCallback(() => {
    const textarea = inputRef.current;
    if (!textarea) return;

    const lineHeight = Number.parseFloat(getComputedStyle(textarea).lineHeight);
    const maxHeight = lineHeight * 6;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
    setIsMultiline(textarea.scrollHeight > lineHeight * 1.5);
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [value, resizeTextarea]);

  const formRef = useRef<HTMLFormElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !disabled && !isStreaming) {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!value || isStreaming || disabled) return;

    if (formRef.current) {
      const rect = formRef.current.getBoundingClientRect();
      setFlyingBubble({
        id: Date.now().toString(),
        text: value,
        startRect: rect,
        targetId: `human-message-${activeMessagesCount || 0}`,
      });
      setAnimStep("start");
    }

    setValue("");
    if (inputRef.current) {
      inputRef.current.value = "";
    }
    resizeTextarea();

    onSubmit && onSubmit(e);
  };

  return (
    <>
      <form
        ref={formRef}
        className={cn(
          "relative mx-auto flex w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-[0px_2px_3px_-1px_rgba(0,0,0,0.1),_0px_1px_0px_0px_rgba(25,28,33,0.02),_0px_0px_0px_1px_rgba(25,28,33,0.08)] transition duration-200 dark:bg-zinc-800",
          value && "bg-gray-50",
          className,
        )}
        onSubmit={handleSubmit}
      >
        {topContent && (
          <div className="w-full px-4 pt-3">
            {topContent}
          </div>
        )}
        <div className="relative flex min-h-12 w-full items-end">
          {leftSlot ? (
            <div
              className={cn(
                "relative z-50 flex h-12 shrink-0 pl-2 transition-all",
                isMultiline ? "items-end pb-1" : "items-center",
              )}
            >
              {leftSlot}
            </div>
          ) : null}
          <textarea
            onChange={(e) => {
              setValue(e.target.value);
              onChange && onChange(e);
            }}
            onKeyDown={handleKeyDown}
            ref={inputRef}
            value={value}
            rows={1}
            className="relative z-50 my-1 max-h-[10rem] min-h-10 flex-1 resize-none border-none bg-transparent px-3 py-2 pr-16 text-sm leading-6 text-black focus:outline-none focus:ring-0 dark:text-white sm:text-base"
          />

          <div className="pointer-events-none absolute inset-0 flex h-12 items-center">
            <AnimatePresence mode="wait">
              {!value && (
                <motion.p
                  initial={{
                    y: 5,
                    opacity: 0,
                  }}
                  key={`current-placeholder-${currentPlaceholder}`}
                  animate={{
                    y: 0,
                    opacity: 1,
                  }}
                  exit={{
                    y: -15,
                    opacity: 0,
                  }}
                  transition={{
                    duration: 0.3,
                    ease: "linear",
                  }}
                  className={cn(
                    "w-[calc(100%-5rem)] truncate text-left text-sm font-normal text-neutral-500 dark:text-zinc-500 sm:text-base",
                    leftSlot ? "pl-14" : "pl-4 sm:pl-12",
                  )}
                >
                  {placeholders[currentPlaceholder]}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          <div className="pointer-events-none absolute bottom-0 right-0 top-0 z-40 w-14 bg-inherit" />
          <button
            disabled={(!value && !isStreaming) || (disabled && !isStreaming)}
            type={isStreaming ? "button" : "submit"}
            onClick={isStreaming ? onStop : undefined}
            className={cn(
              "absolute right-3 z-50 flex h-8 w-8 items-center justify-center rounded-full bg-black transition duration-200 disabled:bg-gray-100 dark:bg-zinc-900 dark:disabled:bg-zinc-800",
              isMultiline ? "bottom-2" : "top-1/2 -translate-y-1/2",
              (disabled && !isStreaming) && "opacity-30 cursor-not-allowed"
            )}
          >
            {isStreaming ? (
              <div className="h-2.5 w-2.5 bg-white rounded-[1px]" />
            ) : (
              <motion.svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-gray-300 h-4 w-4"
              >
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <motion.path
                  d="M5 12l14 0"
                  initial={{
                    strokeDasharray: "50%",
                    strokeDashoffset: "50%",
                  }}
                  animate={{
                    strokeDashoffset: value ? 0 : "50%",
                  }}
                  transition={{
                    duration: 0.3,
                    ease: "linear",
                  }}
                />
                <path d="M13 18l6 -6" />
                <path d="M13 6l6 6" />
              </motion.svg>
            )}
          </button>
        </div>
      </form>

      <AnimatePresence>
        {flyingBubble && (
          <motion.div
            initial={{
              position: "fixed",
              left: flyingBubble.startRect.left,
              top: flyingBubble.startRect.top,
              width: flyingBubble.startRect.width,
              height: flyingBubble.startRect.height,
              backgroundColor: "#000000",
              borderColor: "#262626",
              borderWidth: "1px",
              borderStyle: "solid",
              borderRadius: "16px",
              opacity: 1,
              color: "#ffffff",
              paddingLeft: leftSlot ? "48px" : "12px",
              paddingTop: "8px",
              paddingRight: "48px",
              paddingBottom: "8px",
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              zIndex: 99999,
              pointerEvents: "none",
              boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
            }}
            animate={
              animStep === "flying" && targetRect
                ? {
                    left: targetRect.left,
                    top: targetRect.top,
                    width: targetRect.width,
                    height: targetRect.height,
                    backgroundColor: "#262626",
                    borderColor: "#262626",
                    borderRadius: "16px 2px 16px 16px",
                    opacity: [1, 1, 0],
                    paddingLeft: "16px",
                    paddingTop: "10px",
                    paddingRight: "16px",
                    paddingBottom: "10px",
                  }
                : animStep === "done"
                ? { opacity: 0 }
                : {}
            }
            transition={{
              duration: 0.35,
              ease: [0.25, 1, 0.5, 1],
            }}
            onAnimationComplete={() => {
              if (animStep === "flying" || animStep === "done") {
                setFlyingBubble(null);
                setAnimStep("start");
              }
            }}
          >
            <span className="truncate w-full text-left text-sm leading-6 sm:text-base">{flyingBubble.text}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
