import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { IconArrowRight, IconBrandGithub, IconMail, IconCloudUpload, IconDatabase, IconMessage2 } from "@tabler/icons-react";
import ragIcon from "@/assets/rag.png";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-white/20 overflow-x-hidden">
      <nav className="fixed top-0 z-50 w-full border-b border-white/5 bg-black/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <img src={ragIcon} alt="Logo" className="h-8 w-8 object-contain" />
            <span className="text-xl font-bold tracking-tight">AI Chat</span>
          </div>
          <div className="flex items-center gap-6">
            <Link to="/signup" className="rounded-full bg-white px-6 py-2.5 text-sm font-bold text-black hover:bg-neutral-200 transition-all active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)]">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative pt-40 pb-20 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.03)_0%,transparent_50%)]">

        <div className="mx-auto max-w-7xl px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[9px] md:text-[10px] font-bold uppercase tracking-[0.15em] md:tracking-[0.3em] text-neutral-400 mb-6 md:mb-10 backdrop-blur-md whitespace-nowrap overflow-hidden">
              The new standard for data conversations
            </span>
            <h1 className="bg-gradient-to-br from-white via-white to-neutral-500 bg-clip-text text-4xl sm:text-6xl md:text-[90px] font-extrabold tracking-tighter text-transparent mb-8 md:mb-10 leading-[1.1] md:leading-[0.95]">
              Intelligent insights <br className="hidden sm:block" />
              <span className="text-neutral-400 font-serif italic">at the speed of thought.</span>
            </h1>
            <p className="mx-auto max-w-2xl text-base md:text-xl text-neutral-400 leading-relaxed mb-10 md:mb-14 font-medium px-4 md:px-0">
              The only platform that seamlessly bridges the gap between your raw data and actionable intelligence. PDFs, Videos, and Audio now fully conversational.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 px-6">
              <Link to="/signup" className="group relative flex w-full sm:w-auto items-center justify-center gap-3 rounded-full bg-white px-8 py-4 md:px-10 md:py-5 text-lg md:text-xl font-bold text-black shadow-[0_0_40px_rgba(255,255,255,0.1)] hover:bg-neutral-200 transition-all active:scale-95">
                Begin Your Analysis
                <IconArrowRight className="h-5 w-5 md:h-6 md:w-6 transition-transform group-hover:translate-x-1.5" />
              </Link>
            </div>
          </motion.div>

          <div className="mt-48 py-20">
            <div className="text-center mb-20">
              <h2 className="text-3xl md:text-5xl font-bold mb-6">Simple, yet powerful workflow</h2>
              <p className="text-neutral-500 max-w-xl mx-auto">Three steps to transform your static documents into interactive knowledge bases.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
              <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-neutral-800 to-transparent -z-10 hidden md:block" />
              {[
                { step: "01", icon: <IconCloudUpload className="h-8 w-8 text-white" />, title: "Upload Data", desc: "Drop your PDFs, video recordings, or audio files into the platform." },
                { step: "02", icon: <IconDatabase className="h-8 w-8 text-white" />, title: "AI Indexing", desc: "Our RAG pipeline extracts context and builds a vector-based memory." },
                { step: "03", icon: <IconMessage2 className="h-8 w-8 text-white" />, title: "Interact", desc: "Ask questions, generate summaries, and extract citations instantly." }
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.2 * i }}
                  className="flex flex-col items-center"
                >
                  <div className="h-16 w-16 rounded-2xl bg-neutral-900 border border-neutral-800 flex items-center justify-center mb-8 shadow-2xl group-hover:bg-white group-hover:text-black transition-all duration-500">
                    {item.icon}
                  </div>
                  <h3 className="text-2xl font-bold mb-4">{item.title}</h3>
                  <p className="text-neutral-500 text-center max-w-[250px]">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Detailed Features Section */}
          <div className="mt-48 grid grid-cols-1 md:grid-cols-2 gap-20 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="text-left"
            >
              <h2 className="text-4xl md:text-6xl font-bold mb-8 leading-tight">Beyond just simple chat.</h2>
              <p className="text-lg text-neutral-400 mb-10">We've built a suite of tools designed for serious research and document analysis.</p>

              <ul className="space-y-6">
                {[
                  "Multi-modal RAG (PDF, Video, Audio)",
                  "Real-time SSE Streaming",
                  "Persistent long-term session memory",
                  "Smart Timestamps & Source Citations"
                ].map((text, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.1 * i + 0.3 }}
                    className="flex items-center gap-4 text-white font-semibold"
                  >
                    <div className="h-6 w-6 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-white" />
                    </div>
                    {text}
                  </motion.li>
                ))}
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="relative aspect-square rounded-[32px] border border-neutral-800 bg-neutral-900/50 p-4 overflow-hidden group shadow-2xl"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />

              <div className="relative h-full w-full rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden flex shadow-2xl">
                <div className="w-16 md:w-24 border-r border-neutral-800 bg-neutral-900/50 p-2 hidden sm:flex flex-col gap-2">
                  <div className="h-2 w-8 bg-neutral-800 rounded-full mb-2" />
                  {[1, 2, 3, 4].map(i => (
                    <div key={i} className={`h-1.5 w-full bg-neutral-800/50 rounded-full ${i === 1 ? 'bg-white/20' : ''}`} />
                  ))}
                </div>

                <div className="flex-1 flex flex-col p-4">
                  <div className="space-y-4 flex-1">
                    <div className="flex justify-end">
                      <div className="bg-white/10 border border-white/20 rounded-lg p-2 max-w-[80%]">
                        <div className="h-1 w-16 bg-white/50 rounded-full" />
                      </div>
                    </div>

                    <div className="flex justify-start gap-2">
                      <div className="h-5 w-5 rounded-md bg-neutral-800 flex-shrink-0" />
                      <div className="space-y-1.5 flex-1">
                        <div className="h-1.5 w-full bg-neutral-700 rounded-full" />
                        <div className="h-1.5 w-3/4 bg-neutral-700 rounded-full" />
                        <div className="h-1.5 w-1/2 bg-neutral-700 rounded-full" />
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <div className="bg-white/10 border border-white/20 rounded-lg p-2 max-w-[80%]">
                        <div className="h-1 w-20 bg-white/50 rounded-full" />
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-2 items-center">
                    <div className="flex-1 h-7 rounded-lg bg-neutral-900 border border-neutral-800 px-2 flex items-center">
                      <div className="h-1 w-24 bg-neutral-700 rounded-full" />
                    </div>
                    <div className="h-7 w-7 rounded-lg bg-white" />
                  </div>
                </div>
              </div>
            </motion.div>
          </div>


        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-16 mt-20">
        <div className="mx-auto max-w-7xl px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-10 text-neutral-500 text-sm"
          >
            <div className="flex items-center gap-3">
              <img src={ragIcon} alt="Logo" className="h-8 w-8 opacity-40 grayscale" />
              <p className="font-medium">© 2026 AI Chat Platform.</p>
            </div>

            <div className="h-4 w-px bg-neutral-800 hidden md:block" />

            <a
              href="https://github.com/SurajPatel04"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
            >
              <IconBrandGithub className="h-4 w-4" />
              <span>Built by Suraj Patel</span>
            </a>

            <div className="h-4 w-px bg-neutral-800 hidden md:block" />

            <a
              href="mailto:surajpatel9390@gmail.com"
              className="flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
            >
              <IconMail className="h-4 w-4" />
              <span>surajpatel9390@gmail.com</span>
            </a>
          </motion.div>
        </div>
      </footer>
    </div>

  );
}
