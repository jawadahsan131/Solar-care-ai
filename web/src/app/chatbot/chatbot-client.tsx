"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

type Language = "en" | "roman_urdu";

type ChatResponse = {
  answer: string;
  sources: string[];
  source_details: string[];
  used_chunks: number;
};

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  sources: string[];
  noMatch: boolean;
};

export default function ChatbotClient() {
  const [language, setLanguage] = useState<Language>("en");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!text || sending) return;

    setMessages((current) => [
      ...current,
      { role: "user", text, sources: [], noMatch: false },
    ]);
    setMessage("");
    setErrorMessage("");
    setSending(true);

    try {
      const response = await apiFetch<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, language }),
      });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: response.answer,
          sources: response.source_details.length
            ? response.source_details
            : response.sources,
          noMatch: response.used_chunks === 0,
        },
      ]);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The assistant could not answer right now. Please try again.",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="mx-auto grid w-full max-w-4xl gap-5 pt-4 text-[var(--ink)]">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--green)]">
            SOLAR CARE AI
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
            Help / Ask
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Ask about solar planning or inverter reference documents. Answers use the
            available references and show their sources.
          </p>
        </div>
        <Link className="button button-quiet" href="/dashboard">
          Back to homes
        </Link>
      </header>

      <div
        aria-live="polite"
        aria-relevant="additions text"
        className="flex max-h-[58vh] min-h-72 flex-col gap-3 overflow-y-auto rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm sm:p-6"
        role="log"
      >
        {messages.length === 0 && (
          <p className="m-auto max-w-md text-center text-sm leading-6 text-[var(--muted)]">
            Ask a question to search the project reference documents. If they do not
            cover it, the assistant will say so.
          </p>
        )}
        {messages.map((item, index) => (
          <article
            className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 sm:max-w-[80%] ${
              item.role === "user"
                ? "ml-auto bg-[var(--green)] text-white"
                : "mr-auto border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)]"
            }`}
            key={`${item.role}-${index}`}
          >
            <p className={item.noMatch ? "italic text-[var(--muted)]" : "whitespace-pre-wrap"}>
              {item.text}
            </p>
            {item.role === "assistant" && item.sources.length > 0 && (
              <p className="mt-2 break-words text-xs leading-5 text-[var(--muted)]">
                Sources: {item.sources.join(", ")}
              </p>
            )}
          </article>
        ))}
        {sending && (
          <p className="mr-auto rounded-2xl border border-[var(--line)] bg-[var(--paper)] px-4 py-3 text-sm text-[var(--muted)]">
            Assistant is searching and typing…
          </p>
        )}
        <div ref={messagesEndRef} />
      </div>

      {errorMessage && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {errorMessage}
        </p>
      )}

      <form className="grid gap-3 rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm sm:p-5" onSubmit={sendMessage}>
        <label className="grid max-w-xs gap-1 text-sm font-semibold" htmlFor="chat-language">
          Response language
          <select
            className="min-h-11 rounded-lg border border-[var(--line)] bg-white px-3 text-sm font-normal"
            id="chat-language"
            onChange={(event) => setLanguage(event.target.value as Language)}
            value={language}
          >
            <option value="en">English</option>
            <option value="roman_urdu">Roman Urdu</option>
          </select>
        </label>
        <div className="flex gap-2">
          <input
            autoComplete="off"
            className="min-h-12 min-w-0 flex-1 rounded-xl border border-[var(--line)] px-4 text-sm outline-none focus:border-[var(--green)] focus:ring-2 focus:ring-[var(--green)]/15"
            maxLength={1000}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={language === "en" ? "Ask a question…" : "Apna sawal likhein…"}
            value={message}
          />
          <button
            className="button button-primary min-h-12"
            disabled={sending || !message.trim()}
            type="submit"
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
        <p className="text-xs text-[var(--muted)]">
          Press Enter to send. Verify safety and financial decisions with your manual or a qualified installer.
        </p>
      </form>
    </section>
  );
}
