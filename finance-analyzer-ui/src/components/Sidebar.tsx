import { 
  LayoutDashboard, 
  PieChart, 
  ReceiptText, 
  UploadCloud, 
  Target, 
  Sparkles, 
  Bot, 
  Settings,
  CreditCard
} from "lucide-react";
import { AppSettings } from "../types";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  settings: AppSettings;
}

export default function Sidebar({ activeTab, setActiveTab, settings }: SidebarProps) {
  const menuItems = [
    { id: "overview", label: "Tổng quan", icon: LayoutDashboard },
    { id: "analysis", label: "Phân tích chi tiêu", icon: PieChart },
    { id: "transactions", label: "Danh sách giao dịch", icon: ReceiptText },
    { id: "ocr", label: "Tải hóa đơn lên (OCR)", icon: UploadCloud },
    { id: "budgets", label: "Quản lý ngân sách", icon: Target },
    { id: "insights", label: "Thông tin Insights", icon: Sparkles },
    { id: "chat", label: "Trợ lý tài chính (AI)", icon: Bot },
    { id: "settings", label: "Cài đặt hệ thống", icon: Settings },
  ];

  return (
    <aside id="app-sidebar" className="w-64 border-r border-slate-100 bg-white flex flex-col h-screen sticky top-0 shrink-0 z-10 transition-all duration-300">
      {/* Brand Logo and Title */}
      <div className="p-6 border-b border-slate-50 flex items-center gap-3">
        <div className="p-2.5 bg-emerald-50 rounded-xl text-emerald-600 flex items-center justify-center">
          <CreditCard className="w-5 h-5 stroke-[2.2]" id="sidebar-logo-icon" />
        </div>
        <div>
          <h1 className="font-sans font-bold tracking-tight text-[#1e293b] text-base leading-tight">
            Ví Thông Minh
          </h1>
          <p className="font-mono text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-0.5">
            Finance Analyzer
          </p>
        </div>
      </div>

      {/* User Information Summary */}
      <div className="p-5 border-b border-slate-50/60 bg-gradient-to-b from-[#f8fafc]/50 to-white">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-full border border-emerald-100 bg-emerald-50/60 flex items-center justify-center font-bold text-emerald-700 text-sm">
            {settings.userName.split(" ").pop()?.substring(0, 2).toUpperCase() || "AI"}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 leading-snug">
              {settings.userName}
            </h4>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 mt-1">
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse"></span>
              Đơn vị: {settings.currency}
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              id={`nav-tab-${item.id}`}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-150 relative ${
                isActive
                  ? "bg-emerald-50/70 text-emerald-700 font-semibold border-l-4 border-emerald-600 rounded-l-none pl-3"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon className={`w-4.5 h-4.5 stroke-[1.8] ${isActive ? "text-emerald-600" : "text-slate-400 group-hover:text-slate-600"}`} />
              <span>{item.label}</span>
              {isActive && (
                <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/30">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-medium">Chế độ: {settings.ocrEngine === "gemini" ? "Real AI (Gemini)" : "Simulator"}</span>
          <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-[10px] font-bold text-slate-500">v2.1</span>
        </div>
      </div>
    </aside>
  );
}
