import React, { useState, useRef, useEffect } from "react";
import { 
  Send, 
  Sparkles, 
  Trash2, 
  Bot, 
  HelpCircle,
  Clock,
  ArrowRight,
  User,
  Coffee,
  PiggyBank,
  Check
} from "lucide-react";
import { ChatMessage, AppSettings } from "../types";

interface AssistantChatViewProps {
  chatHistory: ChatMessage[];
  settings: AppSettings;
  onSendMessage: (text: string) => Promise<void>;
  onClearChat: () => void;
}

export default function AssistantChatView({ 
  chatHistory, 
  settings, 
  onSendMessage,
  onClearChat
}: AssistantChatViewProps) {
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to latest bubble
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isSending]);

  const handleSend = async (text: string) => {
    if (!text.trim() || isSending) return;
    setIsSending(true);
    setInputText("");
    
    try {
      await onSendMessage(text);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSending(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(inputText);
  };

  const suggestionChips = [
    { text: "Thống kê chi tiêu ăn uống của tôi?", icon: Coffee },
    { text: "Làm sao để tiết kiệm 30% thu nhập dồi dào?", icon: PiggyBank },
    { text: "Dự phóng tài chính cá nhân tháng tới?", icon: Sparkles },
    { text: "Phân tích ngân sách Hóa đơn đang ở mức đỏ?", icon: HelpCircle }
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-white border border-slate-100 rounded-xl overflow-hidden relative">
      {/* View Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/20 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center font-bold">
            <Bot className="w-5 h-5 stroke-[2]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
              <span>Trợ lý Tài chính AI</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Gemini 3.5-flash tư vấn, lập biểu và đề xuất giải pháp tiết kiệm thực tế</p>
          </div>
        </div>

        {chatHistory.length > 2 && (
          <button
            onClick={onClearChat}
            className="p-1 px-2 hover:bg-rose-50 hover:text-rose-600 border border-slate-100 hover:border-rose-100 text-xs text-slate-400 font-semibold rounded-lg transition-all flex items-center gap-1 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Xóa lịch sử</span>
          </button>
        )}
      </div>

      {/* Messages Feed Area */}
      <div className="flex-1 overflow-y-auto p-4.5 space-y-4 bg-slate-50/10">
        {chatHistory.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div 
              key={msg.id} 
              id={`chat-bubble-${msg.id}`}
              className={`flex items-start gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
            >
              {/* Profile marker bubble icon */}
              <div className={`w-8.5 h-8.5 rounded-full flex items-center justify-center shrink-0 ${
                isUser 
                  ? 'bg-slate-900 border border-slate-800 text-white font-extrabold text-xs' 
                  : 'bg-emerald-50 text-emerald-700 font-bold border border-emerald-100'
              }`}>
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4.5 h-4.5" />}
              </div>

              {/* Core bubble dialog body */}
              <div className="space-y-1">
                <div className={`p-3.5 rounded-xl border leading-relaxed text-xs shadow-sm ${
                  isUser 
                    ? 'bg-slate-900 border-slate-900 text-white rounded-tr-none' 
                    : 'bg-white border-slate-100 text-slate-700 rounded-tl-none font-medium'
                }`}>
                  {/* Clean Markdown rendering simulator */}
                  <div className="whitespace-pre-line select-text" id={`msg-body-${msg.id}`}>
                    {msg.text}
                  </div>
                </div>
                {/* Timestamp */}
                <div className={`text-[9px] text-slate-400 font-medium px-1 flex items-center gap-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <Clock className="w-3 h-3 text-slate-300" />
                  <span>{msg.timestamp}</span>
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing indicator bubble */}
        {isSending && (
          <div className="flex items-start gap-3 mr-auto max-w-[85%]">
            <div className="w-8.5 h-8.5 rounded-full flex items-center justify-center bg-emerald-50 text-emerald-700 border border-emerald-100 shrink-0">
              <Bot className="w-4.5 h-4.5 animate-bounce" />
            </div>
            <div className="space-y-1">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-400 rounded-tl-none font-semibold flex items-center gap-2">
                <span className="inline-flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce duration-300"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce duration-300 delay-100"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce duration-300 delay-200"></span>
                </span>
                <span>Trợ lý tài chính đang suy nghĩ...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips Box */}
      {chatHistory.length <= 2 && !isSending && (
        <div className="p-4 border-t border-slate-50 bg-white shrink-0 scrollbar-none overflow-x-auto">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2 px-1">Gợi ý chủ đề nhanh</span>
          <div className="flex gap-2.5">
            {suggestionChips.map((chip, idx) => {
              const ChipIcon = chip.icon;
              return (
                <button
                  key={idx}
                  onClick={() => handleSend(chip.text)}
                  className="px-3.5 py-2.5 bg-slate-50 border border-slate-100/60 hover:border-emerald-500 hover:bg-emerald-50/10 text-slate-650 hover:text-emerald-700 font-semibold text-[11px] rounded-lg text-left inline-flex items-center gap-2 whitespace-nowrap transition-all duration-155 cursor-pointer"
                >
                  <ChipIcon className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500" />
                  <span>{chip.text}</span>
                  <ArrowRight className="w-3 h-3 text-slate-300 ml-1 shrink-0" />
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Input keyboard actions card */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/20 shrink-0">
        <form onSubmit={handleFormSubmit} className="flex gap-2">
          <input
            type="text"
            required
            disabled={isSending}
            placeholder="Trao đổi thêm về chi tiêu, hướng dẫn tiết kiệm..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="flex-1 px-4 py-2.5 bg-white text-slate-850 placeholder-slate-400 text-xs border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isSending}
            className="p-3 bg-emerald-500/90 hover:bg-emerald-600 text-white rounded-lg transition-colors flex items-center justify-center shrink-0 disabled:opacity-50 border-0 cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
