"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { getMe } from "@/lib/auth-api";
import {
  clearHistory,
  getHistory,
  sendMessage,
  type ChatMessageItem,
} from "@/lib/chat-api";

const SUGGESTED_QUESTIONS = [
  "Tổng chi tháng này",
  "So với tháng trước thì sao?",
  "Top merchant tuần này",
  "Budget còn bao nhiêu?",
];

interface DisplayMessage {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export default function ChatClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auth gate
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        router.replace("/login?next=/chat");
      }
    })();
    return () => { cancelled = true; };
  }, [router]);

  // Load history
  useEffect(() => {
    if (!authReady) return;
    let cancelled = false;
    void (async () => {
      try {
        const data = await getHistory();
        if (cancelled) return;
        const display: DisplayMessage[] = data.items
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content || "",
          }));
        setMessages(display);
      } catch {
        // Ignore history load errors
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    })();
    return () => { cancelled = true; };
  }, [authReady]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(
    async (text?: string) => {
      const content = (text || input).trim();
      if (!content || streaming) return;

      setInput("");
      setError(null);
      setStreaming(true);

      // Add user message
      const userMsg: DisplayMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
      };
      const assistantMsg: DisplayMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      await sendMessage(content, {
        onToken: (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
              };
            }
            return updated;
          });
        },
        onToolCall: () => {
          // Could show "đang tìm kiếm..." indicator
        },
        onDone: () => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = { ...last, streaming: false };
            }
            return updated;
          });
          setStreaming(false);
        },
        onError: (msg) => {
          setError(msg);
          setStreaming(false);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant" && !last.content) {
              // Remove empty assistant message on error
              return updated.slice(0, -1);
            }
            return updated;
          });
        },
      });
    },
    [input, streaming],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Xóa toàn bộ lịch sử chat?")) return;
    try {
      await clearHistory();
      setMessages([]);
    } catch {
      setError("Không thể xóa lịch sử");
    }
  };

  if (!authReady) {
    return (
      <div className="text-sm text-slate-500">
        Đang kiểm tra phiên đăng nhập…
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-12rem)] max-w-2xl flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            💬 Trợ lý chi tiêu
          </h1>
          <p className="text-xs text-slate-500">
            Hỏi bất kỳ điều gì về chi tiêu của bạn
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClear()}
            className="text-xs text-slate-500 hover:text-rose-600"
          >
            Xóa lịch sử
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-3">
        {loadingHistory && (
          <p className="text-sm text-slate-400 text-center">
            Đang tải lịch sử…
          </p>
        )}

        {!loadingHistory && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <p className="text-sm text-slate-500">
              Chào bạn! Hỏi tôi bất kỳ điều gì về chi tiêu của bạn.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void handleSend(q)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 hover:border-slate-300 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 mb-2">
          {error}
        </div>
      )}

      {/* Suggested questions (when has messages) */}
      {messages.length > 0 && !streaming && (
        <div className="flex flex-wrap gap-1.5 pb-2">
          {SUGGESTED_QUESTIONS.slice(0, 3).map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => void handleSend(q)}
              className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100 transition"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex items-end gap-2 border-t border-slate-200 pt-3">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi..."
          rows={1}
          disabled={streaming}
          className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-slate-500 focus:outline-none disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={streaming || !input.trim()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 transition"
        >
          {streaming ? "..." : "Gửi"}
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-slate-900 text-white"
            : "bg-white border border-slate-200 text-slate-900"
        }`}
      >
        {message.content || (message.streaming ? "⏳" : "")}
        {message.streaming && message.content && (
          <span className="inline-block w-1.5 h-4 bg-slate-400 animate-pulse ml-0.5 align-text-bottom" />
        )}
      </div>
    </div>
  );
}
