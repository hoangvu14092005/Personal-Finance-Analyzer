"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Send, Sparkles, Trash2 } from "lucide-react";

import { getMe } from "@/lib/auth-api";
import {
  clearHistory,
  getHistory,
  sendMessage,
} from "@/lib/chat-api";
import { Button, CalloutBanner, PillTab } from "@/components/ui";

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
    return () => {
      cancelled = true;
    };
  }, [router]);

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
        // ignore
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authReady]);

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
        onToolCall: () => {},
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
      <div className="text-body-sm text-mute">
        Đang kiểm tra phiên đăng nhập…
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col space-y-4">
      <header className="rounded-xl border border-hairline-soft bg-white p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight text-ink">
              <Bot className="h-5 w-5 text-accent-green" aria-hidden />
              Trợ lý tài chính (AI)
            </h1>
            <p className="mt-0.5 text-sm text-ash">
              Hỏi về chi tiêu, ngân sách hoặc hóa đơn đã tải lên bằng tiếng Việt.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.slice(0, 2).map((q) => (
              <PillTab key={q} onClick={() => void handleSend(q)}>{q}</PillTab>
            ))}
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClear()}
            className="mt-4 text-caption-sm text-mute hover:text-accent-red"
          >
            <span className="inline-flex items-center gap-1.5"><Trash2 className="h-3.5 w-3.5" aria-hidden />Xóa lịch sử</span>
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-hairline-soft bg-white p-4 space-y-3">
        {loadingHistory && (
          <p className="text-body-sm text-mute text-center">
            Đang tải lịch sử…
          </p>
        )}

        {!loadingHistory && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-green-soft text-accent-green">
              <Sparkles className="h-5 w-5" aria-hidden />
            </div>
            <p className="text-body-md text-body text-center max-w-sm">
              Chào bạn! Hỏi tôi bất kỳ điều gì về chi tiêu của bạn.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <PillTab key={q} onClick={() => void handleSend(q)}>
                  {q}
                </PillTab>
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
        <div className="mb-3">
          <CalloutBanner severity="warning">{error}</CalloutBanner>
        </div>
      )}

      {/* Quick suggestions (when has messages) */}
      {messages.length > 0 && !streaming && (
        <div className="flex flex-wrap gap-1.5 pb-3">
          {SUGGESTED_QUESTIONS.slice(0, 3).map((q) => (
            <PillTab key={q} onClick={() => void handleSend(q)}>
              {q}
            </PillTab>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex items-end gap-2 rounded-2xl border border-hairline-soft bg-surface-card p-3">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi..."
          rows={1}
          disabled={streaming}
          className="flex-1 resize-none rounded-md border border-hairline bg-surface-doc px-3 py-2 text-body-md text-ink placeholder:text-ash focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 disabled:opacity-60"
        />
        <Button
          variant="primary"
          onClick={() => void handleSend()}
          disabled={streaming || !input.trim()}
        >
          {streaming ? "Đang gửi" : <><Send className="h-4 w-4" aria-hidden />Gửi</>}
        </Button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 text-body-md whitespace-pre-wrap ${
          isUser
            ? "bg-ink text-on-dark"
            : "bg-surface-card border border-hairline text-ink"
        }`}
      >
        {message.content || (message.streaming ? "Đang trả lời..." : "")}
        {message.streaming && message.content && (
          <span className="inline-block w-1.5 h-4 bg-mute animate-pulse ml-0.5 align-text-bottom" />
        )}
      </div>
    </div>
  );
}
