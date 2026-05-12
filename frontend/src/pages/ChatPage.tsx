import { useState } from "react";
import {
  IconArrowLeft,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconMessage,
  IconPaperclip,
  IconPlus,
  IconSearch,
  IconSettings,
} from "@tabler/icons-react";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { authService } from "@/services/authService";

const chatLinks = [
  "Auth API setup",
  "Pan assignment notes",
  "Frontend polish",
  "Route protection",
];

const messages = [
  {
    role: "assistant",
    content: "Hi Suraj. What should we build or debug next?",
  },
  {
    role: "user",
    content: "Create a chat page with a sidebar.",
  },
  {
    role: "assistant",
    content: "Done. The protected app now opens into this chat workspace.",
  },
];

const placeholders = [
  "Ask anything about this assignment",
  "Upload a PDF, audio, or video file",
  "Summarize this file",
  "What should we build next?",
];

export default function ChatPage() {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } finally {
      window.location.href = "/login";
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files?.[0] ?? null);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  };

  return (
    <section className="flex h-screen w-full overflow-hidden bg-black">
      <Sidebar autoOpen={false} open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-6 border-r border-neutral-800 bg-black">
          <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
            <div className="group/sidebar-toggle relative z-20 flex h-9 items-center gap-2 py-1">
              <a
                aria-label="AI Chat"
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-black"
                href="/dashboard"
              >
                <IconMessage className="h-4 w-4" />
              </a>
              {open ? (
                <span className="text-sm font-medium text-white">AI Chat</span>
              ) : null}
              <button
                aria-label={open ? "Collapse sidebar" : "Open sidebar"}
                className={
                  open
                    ? "ml-auto flex h-8 w-8 items-center justify-center rounded-md text-neutral-300 transition hover:bg-neutral-900 hover:text-white"
                    : "absolute left-0 top-1 flex h-8 w-8 items-center justify-center rounded-md bg-white text-black opacity-0 transition group-hover/sidebar-toggle:opacity-100"
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

            <div className="mt-8 flex flex-col gap-2">
              <SidebarLink
                link={{
                  label: "New chat",
                  href: "/dashboard",
                  icon: <IconPlus className="h-5 w-5 shrink-0 text-neutral-200" />,
                }}
              />
              <SidebarLink
                link={{
                  label: "Search chats",
                  href: "/dashboard",
                  icon: <IconSearch className="h-5 w-5 shrink-0 text-neutral-200" />,
                }}
              />
            </div>

            <div className="mt-8 border-t border-neutral-800 pt-4">
              <p className="mb-2 px-1 text-xs font-medium uppercase tracking-wide text-neutral-500">
                Recent
              </p>
              <div className="flex flex-col gap-1">
                {chatLinks.map((label) => (
                  <SidebarLink
                    key={label}
                    link={{
                      label,
                      href: "/dashboard",
                      icon: <IconMessage className="h-5 w-5 shrink-0 text-neutral-300" />,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <SidebarLink
              link={{
                label: "Settings",
                href: "/dashboard",
                icon: <IconSettings className="h-5 w-5 shrink-0 text-neutral-200" />,
              }}
            />
            <button
              className="flex items-center justify-start gap-2 py-2 text-sm text-neutral-200 transition hover:text-white"
              onClick={handleLogout}
              type="button"
            >
              <IconArrowLeft className="h-5 w-5 shrink-0" />
              {open ? <span>Logout</span> : null}
            </button>
          </div>
        </SidebarBody>
      </Sidebar>

      <div className="flex min-w-0 flex-1 flex-col bg-neutral-950">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-800 px-4 md:px-6">
          <div>
            <h1 className="text-sm font-semibold text-white">Chat</h1>
            <p className="text-xs text-neutral-400">Protected workspace</p>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((message, index) => (
              <div
                className={
                  message.role === "user"
                    ? "ml-auto max-w-[82%] rounded-lg bg-white px-4 py-3 text-sm text-neutral-950"
                    : "mr-auto max-w-[82%] rounded-lg border border-neutral-800 bg-black px-4 py-3 text-sm text-neutral-100"
                }
                key={`${message.role}-${index}`}
              >
                {message.content}
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-neutral-800 p-4">
          <div className="mx-auto max-w-3xl">
            {selectedFile ? (
              <div className="mb-2 flex items-center justify-between gap-3 rounded-lg border border-neutral-800 bg-black px-3 py-2 text-xs text-neutral-300">
                <span className="truncate">{selectedFile.name}</span>
                <button
                  className="shrink-0 text-neutral-500 transition hover:text-white"
                  onClick={() => setSelectedFile(null)}
                  type="button"
                >
                  Remove
                </button>
              </div>
            ) : null}

            <PlaceholdersAndVanishInput
              className="max-w-none border border-neutral-800 bg-black shadow-none dark:bg-black"
              leftSlot={
                <label className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl text-neutral-300 transition hover:bg-neutral-900 hover:text-white">
                  <IconPaperclip className="h-5 w-5" />
                  <input
                    accept="application/pdf,video/*,audio/*"
                    className="sr-only"
                    onChange={handleFileChange}
                    type="file"
                  />
                </label>
              }
              onChange={() => {}}
              onSubmit={handleSubmit}
              placeholders={placeholders}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
