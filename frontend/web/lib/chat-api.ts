/**
 * Chat API client (Phase 6.8).
 * SSE streaming + history + clear.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export interface ChatMessageItem {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string | null;
  tool_calls: unknown[] | null;
  tool_name: string | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  items: ChatMessageItem[];
  has_more: boolean;
  next_before_id: number | null;
}

export interface StreamHandlers {
  onToken: (text: string) => void;
  onToolCall: (name: string) => void;
  onDone: () => void;
  onError: (msg: string) => void;
}

/**
 * Send message via SSE stream.
 * Parses SSE events: token, tool_call, done, error.
 */
export async function sendMessage(
  content: string,
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  });

  if (!response.ok || !response.body) {
    handlers.onError(`HTTP ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Split on double newline (SSE block separator)
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      if (!block.trim()) continue;
      const lines = block.split("\n");
      let eventType = "";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7);
        } else if (line.startsWith("data: ")) {
          data = line.slice(6);
        }
      }

      if (!eventType || !data) continue;

      try {
        const parsed = JSON.parse(data);
        switch (eventType) {
          case "token":
            handlers.onToken(parsed.content || "");
            break;
          case "tool_call":
            handlers.onToolCall(parsed.name || "");
            break;
          case "done":
            handlers.onDone();
            break;
          case "error":
            handlers.onError(parsed.message || "Unknown error");
            break;
        }
      } catch {
        // Skip malformed JSON
      }
    }
  }

  // If stream ended without done event
  handlers.onDone();
}

/**
 * Get chat history (cursor pagination).
 */
export async function getHistory(
  beforeId?: number,
  limit = 50,
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (beforeId !== undefined) {
    params.set("before_id", String(beforeId));
  }

  const response = await fetch(
    `${API_BASE}/api/v1/chat/history?${params.toString()}`,
    { credentials: "include" },
  );

  if (!response.ok) {
    throw Object.assign(new Error("Failed to load history"), {
      status: response.status,
    });
  }

  return response.json();
}

/**
 * Clear all chat history.
 */
export async function clearHistory(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/chat/history`, {
    method: "DELETE",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Failed to clear history: ${response.status}`);
  }
}
