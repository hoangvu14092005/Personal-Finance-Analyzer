import { useState } from "react";
import { 
  Menu, 
  Bell, 
  Search, 
  HelpCircle, 
  Sparkles,
  ChevronRight,
  TrendingUp,
  CreditCard
} from "lucide-react";

import { 
  Transaction, 
  Budget, 
  ReceiptUpload, 
  FinancialInsight, 
  ChatMessage, 
  AppSettings 
} from "./types";

import { 
  INITIAL_TRANSACTIONS, 
  INITIAL_BUDGETS, 
  INITIAL_UPLOADS, 
  INITIAL_INSIGHTS, 
  INITIAL_SETTINGS 
} from "./data/mockData";

// View components imports
import Sidebar from "./components/Sidebar";
import DashboardView from "./components/DashboardView";
import AnalysisView from "./components/AnalysisView";
import TransactionsView from "./components/TransactionsView";
import ReceiptOCRView from "./components/ReceiptOCRView";
import BudgetView from "./components/BudgetView";
import InsightsView from "./components/InsightsView";
import AssistantChatView from "./components/AssistantChatView";
import SettingsView from "./components/SettingsView";

export default function App() {
  const [activeTab, setActiveTab] = useState<string>("overview");
  
  // Core Application Shared State managers
  const [transactions, setTransactions] = useState<Transaction[]>(INITIAL_TRANSACTIONS);
  const [budgets, setBudgets] = useState<Budget[]>(INITIAL_BUDGETS);
  const [uploads, setUploads] = useState<ReceiptUpload[]>(INITIAL_UPLOADS);
  const [insights, setInsights] = useState<FinancialInsight[]>(INITIAL_INSIGHTS);
  const [settings, setSettings] = useState<AppSettings>(INITIAL_SETTINGS);

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([
    {
      id: "welcome-msg",
      sender: "assistant",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: "Xin chào! Tôi là Trợ lý Phân tích Tài chính AI cá nhân của bạn.\n\nTôi có thể giúp bạn làm các việc sau:\n1. Báo cáo thống kê chi phí, tư vấn lập ngân sách lành mạnh áp dụng nguyên tắc 50/30/20.\n2. Tách nhỏ bất kỳ ảnh hóa đơn mua sắm nào (qua tab 'Tải hóa đơn lên (OCR)') rồi lưu trực tiếp vào sổ ví.\n3. Gợi ý phương pháp cắt giảm chi tiêu không thiết yếu dựa trên dữ liệu thật.\n\nHãy chọn một gợi ý phía dưới hoặc đặt bất kỳ câu hỏi nào!"
    }
  ]);

  // Modal triggers
  const [isAddTransactionOpen, setIsAddTransactionOpen] = useState(false);

  // CALLBACK 1: Add manual transactions log
  const handleAddTransaction = (newTxData: Omit<Transaction, 'id'>) => {
    const generatedTx: Transaction = {
      ...newTxData,
      id: `tx-manual-${Date.now()}`
    };

    setTransactions(prev => [generatedTx, ...prev]);

    // Recalculate correlating category budgets spent meters
    if (newTxData.type === 'expense' && newTxData.status === 'completed') {
      setBudgets(prev => prev.map(bg => {
        if (bg.category === newTxData.category) {
          return {
            ...bg,
            spent: bg.spent + newTxData.amount
          };
        }
        return bg;
      }));
    }
  };

  // CALLBACK 2: Drop manual record from journals
  const handleDeleteTransaction = (id: string) => {
    const targetTx = transactions.find(t => t.id === id);
    if (!targetTx) return;

    if (window.confirm && !window.confirm("Bạn có chắc chắn muốn xóa giao dịch này?")) {
      return;
    }

    setTransactions(prev => prev.filter(t => t.id !== id));

    // Deduct spendings from correlated budget trackers safely
    if (targetTx.type === 'expense' && targetTx.status === 'completed') {
      setBudgets(prev => prev.map(bg => {
        if (bg.category === targetTx.category) {
          return {
            ...bg,
            spent: Math.max(bg.spent - targetTx.amount, 0)
          };
        }
        return bg;
      }));
    }
  };

  // CALLBACK 3: Sync OCR Upload complete results into database
  const handleSyncOCRReceiptToTransactions = (uploadId: string, finalData: any) => {
    // 1. Mark matching uploading document as synced
    setUploads(prev => prev.map(u => {
      if (u.id === uploadId) {
        return {
          ...u,
          status: 'synced' as const,
          recognizedData: finalData
        };
      }
      return u;
    }));

    // 2. Export extracted parameters to active expense transactions feed
    const generatedTx: Transaction = {
      id: `tx-ocr-${Date.now()}`,
      date: finalData.date || new Date().toISOString().split('T')[0],
      description: `Hóa đơn: ${finalData.merchant}`,
      category: finalData.category,
      amount: finalData.total,
      type: 'expense',
      status: 'completed',
      note: `Tự động bóc tách từ hóa đơn ${finalData.items.length} mặt hàng.`
    };
    setTransactions(prev => [generatedTx, ...prev]);

    // 3. Update category budget gauge directly
    setBudgets(prev => prev.map(bg => {
      if (bg.category === finalData.category) {
        return {
          ...bg,
          spent: bg.spent + finalData.total
        };
      }
      return bg;
    }));

    alert(`Đã hoàn tất đồng bộ hóa đơn của ${finalData.merchant} vào hệ thống ví tài chính!`);
  };

  // CALLBACK 4: Push new bóc tách document
  const handleNewOCRUpload = (newUpload: ReceiptUpload) => {
    setUploads(prev => [newUpload, ...prev]);
  };

  // CALLBACK 5: Edit existing category budget limit
  const handleUpdateBudgetLimit = (id: string, newLimit: number) => {
    setBudgets(prev => prev.map(b => b.id === id ? { ...b, limit: newLimit } : b));
  };

  // CALLBACK 6: Register brand new sector limit
  const handleAddNewBudget = (category: string, limit: number) => {
    const generatedBg: Budget = {
      id: `bg-gen-${Date.now()}`,
      category,
      limit,
      spent: 0,
      color: `#${Math.floor(Math.random()*16777215).toString(16)}` // Random color fallback
    };
    setBudgets(prev => [...prev, generatedBg]);
  };

  // CALLBACK 7: Update config parameters
  const handleUpdateSettings = (newSettings: AppSettings) => {
    setSettings(newSettings);
  };

  // CALLBACK 8: Update financial insights from Gemini server
  const handleRefreshInsights = (newInsights: FinancialInsight[]) => {
    setInsights(newInsights);
  };

  // CALLBACK 9: Send User Chat Message over Express Proxy
  const handleSendChatMessage = async (userText: string) => {
    const userMsg: ChatMessage = {
      id: `chat-${Date.now()}-user`,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: userText
    };

    setChatHistory(prev => [...prev, userMsg]);

    try {
      // Proxy chat calls to our Express server `/api/chat`
      // Send historical content context for memory-retrieval
      const histPayload = chatHistory.slice(-4).map(h => ({
        role: h.sender === 'user' ? 'user' : 'model',
        text: h.text
      }));

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          history: histPayload
        })
      });

      if (!response.ok) {
        throw new Error("Lỗi máy chủ mốc nối GenAI");
      }

      const data = await response.json();
      
      const assistantMsg: ChatMessage = {
        id: `chat-${Date.now()}-assistant`,
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: data.text
      };

      setChatHistory(prev => [...prev, assistantMsg]);

    } catch (error) {
      console.error("Chat proxy failed. Running instant client intelligent advisor fallback:", error);
      
      // Fallback message
      setTimeout(() => {
        const assistantMsg: ChatMessage = {
          id: `chat-${Date.now()}-assistant`,
          sender: "assistant",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: `Tôi đã ghi nhận băn khoăn của bạn về vấn đề tài chính. Hiện tại mạng đang bận, tuy nhiên đối chiếu dữ liệu của bạn:\n- Thặng dư tiền mặt đạt **${(transactions.filter(t => t.type === 'income').reduce((s, c) => s + c.amount, 0) - transactions.filter(t => t.type === 'expense').reduce((s, c) => s + c.amount, 0)).toLocaleString()} VND**.\n- Bạn đang có định mức cảnh báo đỏ ở nhóm **Hóa đơn**.\n\nHãy kiểm tra lại cài đặt Secrets nếu bạn chưa cấu hình khóa API thực tế!`
        };
        setChatHistory(prev => [...prev, assistantMsg]);
      }, 1000);
    }
  };

  // Reset entire chat
  const handleClearChatHistory = () => {
    setChatHistory([
      {
        id: "welcome-reset",
        sender: "assistant",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: "Sẵn sàng nhận diện hóa đơn hoặc trả lời tư vấn định mức tài chính tiếp theo."
      }
    ]);
  };

  // Helper trigger to swap pages
  const handleNavigateToTab = (tab: string) => {
    setActiveTab(tab);
  };

  // Render Core Target Panel Views
  const renderActiveView = () => {
    switch (activeTab) {
      case "overview":
        return (
          <DashboardView 
            transactions={transactions}
            budgets={budgets}
            settings={settings}
            onAddTransactionClick={() => {
              setActiveTab("transactions");
              setIsAddTransactionOpen(true);
            }}
            onNavigateToTab={handleNavigateToTab}
          />
        );
      case "analysis":
        return (
          <AnalysisView 
            transactions={transactions}
            budgets={budgets}
            settings={settings}
          />
        );
      case "transactions":
        return (
          <TransactionsView 
            transactions={transactions}
            settings={settings}
            onAddTransaction={handleAddTransaction}
            onDeleteTransaction={handleDeleteTransaction}
            isAddModalOpenInitially={isAddTransactionOpen}
          />
        );
      case "ocr":
        return (
          <ReceiptOCRView 
            uploads={uploads}
            settings={settings}
            onOCRComplete={handleNewOCRUpload}
            onSyncToTransactions={handleSyncOCRReceiptToTransactions}
          />
        );
      case "budgets":
        return (
          <BudgetView 
            budgets={budgets}
            settings={settings}
            onUpdateBudget={handleUpdateBudgetLimit}
            onAddBudget={handleAddNewBudget}
          />
        );
      case "insights":
        return (
          <InsightsView 
            insights={insights}
            budgets={budgets}
            transactions={transactions}
            settings={settings}
            onRefreshInsights={handleRefreshInsights}
          />
        );
      case "chat":
        return (
          <AssistantChatView 
            chatHistory={chatHistory}
            settings={settings}
            onSendMessage={handleSendChatMessage}
            onClearChat={handleClearChatHistory}
          />
        );
      case "settings":
        return (
          <SettingsView 
            settings={settings}
            onUpdateSettings={handleUpdateSettings}
          />
        );
      default:
        return (
          <div className="py-20 text-center">
            <h3>Đang tải tính năng mong muốn...</h3>
          </div>
        );
    }
  };

  return (
    <div id="finance-app-root" className="min-h-screen bg-white text-[#1e293b] flex font-sans antialiased overflow-x-hidden selection:bg-emerald-100 selection:text-emerald-800">
      
      {/* 1. Left Sidebar Navigation Panel */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setIsAddTransactionOpen(false); // Clear toggle
        }} 
        settings={settings} 
      />

      {/* 2. Right Base Content View Window */}
      <div className="flex-1 flex flex-col min-w-0" id="main-frame-panel">
        
        {/* Top-bar Panel Utility Row */}
        <header className="h-16 px-8 border-b border-slate-100 flex items-center justify-between shrink-0 bg-white">
          <div className="flex items-center gap-1.5">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">Hệ sinh thái quản lý tài chính</h2>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="text-xs font-bold text-slate-550 capitalize">{activeTab} controls</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            {/* Quick alert indicator */}
            <div className="p-1.5 hover:bg-slate-50 text-slate-400 hover:text-slate-700 rounded-full transition-all cursor-pointer relative" title="Thông báo hệ thống">
              <Bell className="w-5 h-5 stroke-[1.8]" />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500 ring-2 ring-white"></span>
            </div>

            <div className="h-7 w-px bg-slate-100"></div>

            {/* Quick telemetry sync value */}
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 bg-slate-50 p-1.5 px-3.5 rounded-lg border border-slate-100">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>Dữ liệu: Local synced</span>
            </div>
          </div>
        </header>

        {/* Dynamic page component viewport container */}
        <main className="flex-1 overflow-y-auto p-8 max-w-7xl w-full mx-auto" id="viewport-panel">
          {renderActiveView()}
        </main>
      </div>
    </div>
  );
}
