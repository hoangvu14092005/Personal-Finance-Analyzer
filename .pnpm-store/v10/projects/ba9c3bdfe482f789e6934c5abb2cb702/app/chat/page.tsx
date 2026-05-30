import { Suspense } from "react";
import ChatClient from "./chat-client";

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="text-sm text-slate-500">Đang tải...</div>
      }
    >
      <ChatClient />
    </Suspense>
  );
}
