import { useState, useEffect } from "react";
import { 
  Sparkles, 
  RefreshCw, 
  AlertTriangle, 
  TrendingUp, 
  CheckCircle, 
  Info,
  ChevronRight,
  Lightbulb,
  Cpu
} from "lucide-react";
import { FinancialInsight, Budget, Transaction, AppSettings } from "../types";

interface InsightsViewProps {
  insights: FinancialInsight[];
  budgets: Budget[];
  transactions: Transaction[];
  settings: AppSettings;
  onRefreshInsights: (newInsights: FinancialInsight[]) => void;
}

export default function InsightsView({ 
  insights, 
  budgets, 
  transactions, 
  settings,
  onRefreshInsights 
}: InsightsViewProps) {
  const [filterType, setFilterType] = useState<'all' | 'warning' | 'opportunity' | 'success' | 'info'>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isUsingMock, setIsUsingMock] = useState(false);

  // Filter insights
  const filteredInsights = insights.filter(ins => {
    return filterType === 'all' || ins.type === filterType;
  });

  // Call Express API to generate real or mock dynamic insights
  const handleRegenerateInsights = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch("/api/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentBudgets: budgets,
          recentTransactions: transactions
        })
      });

      if (!response.ok) {
        throw new Error("Không thể kết nối máy chủ phân tích.");
      }

      const data = await response.json();
      onRefreshInsights(data.insights);
      setIsUsingMock(!!data.isMock);

    } catch (error) {
      console.error("Failed to generate dynamic insights:", error);
      alert("Lỗi máy chủ phân tích. Đang tự động nạp kết quả mẫu cục bộ...");
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* View Header with AI Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-850 flex items-center gap-2">
            <span>Trung Tâm Phân Tích Thực Tế (AI Insights)</span>
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Các phát hiện thông minh, cảnh báo rủi ro chi tiêu và phương pháp tiết kiệm được tự động tổng hợp bởi AI.
          </p>
        </div>

        <button
          onClick={handleRegenerateInsights}
          disabled={isRefreshing}
          className="inline-flex items-center gap-2 px-4.5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-sm rounded-lg shadow-sm transition-all focus:ring-2 focus:ring-emerald-500 cursor-pointer border-0 disabled:opacity-50"
        >
          {isRefreshing ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Cpu className="w-4 h-4" />
          )}
          <span>Phân tích lại bằng AI</span>
        </button>
      </div>

      {/* AI Header Billboard */}
      <div className="p-5 bg-gradient-to-r from-slate-900 via-slate-850 to-slate-800 text-white rounded-xl relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 z-10">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
            <Sparkles className="w-4.5 h-4.5 animate-pulse" />
            <span>AI ENGINE TRUY VẤN</span>
          </div>
          <h3 className="text-base font-extrabold font-sans">
            Mạng nơ-ron phân tích dữ liệu mua sắm tháng 5
          </h3>
          <p className="text-xs text-slate-350 leading-relaxed max-w-xl">
            Sử dụng thông lực Gemini {settings.ocrEngine === "gemini" ? "Real-time" : "Simulator"} để quét toàn bộ giao dịch, hóa đơn bóc tách và đối lưu với hạn mức. Cảnh báo các cụm điểm tăng giá đột xuất.
          </p>
        </div>

        <div className="flex items-center gap-4 shrink-0 bg-white/5 p-4 rounded-xl border border-white/10 z-10">
          <div className="text-center">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">Tỷ lệ chính xác</span>
            <div className="text-lg font-black text-emerald-400 font-mono">98.4%</div>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="text-center">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">Trạng thái</span>
            <div className="text-xs font-bold text-slate-200 mt-0.5">ONLINE</div>
          </div>
        </div>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap gap-2 text-xs font-semibold">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3.5 py-1.8 rounded-full border transition-all cursor-pointer ${filterType === 'all' ? 'bg-slate-900 border-slate-900 text-white' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
        >
          Tất cả ({insights.length})
        </button>
        <button
          onClick={() => setFilterType('warning')}
          className={`px-3.5 py-1.8 rounded-full border transition-all cursor-pointer ${filterType === 'warning' ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
        >
          Cảnh báo ({insights.filter(i => i.type === 'warning').length})
        </button>
        <button
          onClick={() => setFilterType('opportunity')}
          className={`px-3.5 py-1.8 rounded-full border transition-all cursor-pointer ${filterType === 'opportunity' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
        >
          Cơ hội tiết kiệm ({insights.filter(i => i.type === 'opportunity').length})
        </button>
        <button
          onClick={() => setFilterType('success')}
          className={`px-3.5 py-1.8 rounded-full border transition-all cursor-pointer ${filterType === 'success' ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
        >
          Điểm tích cực ({insights.filter(i => i.type === 'success').length})
        </button>
        <button
          onClick={() => setFilterType('info')}
          className={`px-3.5 py-1.8 rounded-full border transition-all cursor-pointer ${filterType === 'info' ? 'bg-slate-100 border-slate-300 text-slate-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
        >
          Sự thật tài chính ({insights.filter(i => i.type === 'info').length})
        </button>
      </div>

      {/* Insights listing */}
      <div className="space-y-4">
        {filteredInsights.length === 0 ? (
          <div className="p-12 text-center bg-white border border-slate-100 rounded-xl text-slate-400 text-xs">
             Không có phân tích nào khớp với bộ lọc bạn chọn.
          </div>
        ) : (
          filteredInsights.map((ins) => {
            // Find icons and border colors
            let iconElement = <Info className="w-5 h-5 text-slate-500" />;
            let borderClass = "border-l-4 border-l-slate-450 border-slate-100";
            let bgClass = "bg-white";

            if (ins.type === 'warning') {
              iconElement = <AlertTriangle className="w-5 h-5 text-rose-500" />;
              borderClass = "border-l-4 border-l-rose-500 border-slate-100";
            } else if (ins.type === 'opportunity') {
              iconElement = <Lightbulb className="w-5 h-5 text-yellow-600" />;
              borderClass = "border-l-4 border-l-amber-500 border-slate-100";
              bgClass = "bg-amber-50/10";
            } else if (ins.type === 'success') {
              iconElement = <CheckCircle className="w-5 h-5 text-emerald-600" />;
              borderClass = "border-l-4 border-l-emerald-600 border-slate-100";
            } else if (ins.type === 'info') {
              iconElement = <TrendingUp className="w-5 h-5 text-blue-600" />;
              borderClass = "border-l-4 border-l-blue-500 border-slate-100";
            }

            return (
              <div 
                key={ins.id} 
                id={`insight-card-${ins.id}`}
                className={`p-5 rounded-xl border ${borderClass} ${bgClass} flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all hover:shadow-sm`}
              >
                <div className="flex items-start gap-4">
                  <div className="p-2 bg-slate-100 rounded-lg shrink-0 mt-0.5">
                    {iconElement}
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-widest">{ins.category || "TẤT CẢ"}</span>
                      <span className="text-[10px] text-slate-350">•</span>
                      <span className="text-[10px] font-sans text-slate-400 font-medium">{ins.date}</span>
                    </div>
                    <h4 className="text-sm font-bold text-slate-800 leading-normal">{ins.title}</h4>
                    <p className="text-xs text-slate-500 leading-relaxed max-w-2xl">{ins.description}</p>
                  </div>
                </div>

                {/* Impact value widget */}
                {ins.impactValue && (
                  <div className="shrink-0 bg-slate-900 text-white font-mono px-3.5 py-1.8 rounded text-xs font-black text-center shadow">
                    <span className="text-[9px] text-slate-400 font-sans font-semibold tracking-wider uppercase block pb-0.5 mb-0.5 border-b border-slate-700/60 leading-none">Ước tính dòng</span>
                    <span className="text-emerald-400 tracking-tight text-sm font-extrabold">{ins.impactValue}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
