import React, { useState } from "react";
import { 
  Plus, 
  Trash2, 
  Edit2, 
  Check, 
  X, 
  Target, 
  AlertTriangle,
  Smile,
  Info
} from "lucide-react";
import { Budget, AppSettings } from "../types";
import { CHOOSE_CATEGORIES } from "../data/mockData";

interface BudgetViewProps {
  budgets: Budget[];
  settings: AppSettings;
  onUpdateBudget: (id: string, newLimit: number) => void;
  onAddBudget: (category: string, limit: number) => void;
}

export default function BudgetView({ 
  budgets, 
  settings,
  onUpdateBudget,
  onAddBudget
}: BudgetViewProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingVal, setEditingVal] = useState("");
  
  // New budget form states
  const [isAdding, setIsAdding] = useState(false);
  const [newCat, setNewCat] = useState("Ăn uống");
  const [newLimit, setNewLimit] = useState("");

  // Currency Converter
  const formatVal = (num: number) => {
    return new Intl.NumberFormat(settings.currency === 'VND' ? "vi-VN" : "en-US", {
      style: "currency",
      currency: settings.currency,
      maximumFractionDigits: 0
    }).format(num);
  };

  const handleEditClick = (bg: Budget) => {
    setEditingId(bg.id);
    setEditingVal(bg.limit.toString());
  };

  const handleSaveClick = (id: string) => {
    if (!editingVal || isNaN(Number(editingVal))) {
      alert("Hạn mức nhập vào không hợp lệ!");
      return;
    }
    onUpdateBudget(id, Math.abs(Number(editingVal)));
    setEditingId(null);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLimit || isNaN(Number(newLimit))) {
      alert("Vui lòng nhập định mức hợp lệ!");
      return;
    }

    // Check if category already has a budget
    const exists = budgets.find(b => b.category === newCat);
    if (exists) {
      alert(`Định mức cho danh mục '${newCat}' đã tồn tại! Hãy chỉnh sửa trực tiếp.`);
      return;
    }

    onAddBudget(newCat, Math.abs(Number(newLimit)));
    setNewLimit("");
    setIsAdding(false);
  };

  // Compute aggregated totals
  const totalLimit = budgets.reduce((acc, curr) => acc + curr.limit, 0);
  const totalSpent = budgets.reduce((acc, curr) => acc + curr.spent, 0);
  const totalRatio = totalLimit > 0 ? (totalSpent / totalLimit) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Upper header block */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-850">
            Quản Lý Định Mức Ngân Sách
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Kiểm soát chi tiêu bằng cách áp hạn mức riêng cho từng nhóm nhu cầu cuộc sống.
          </p>
        </div>

        <button
          onClick={() => setIsAdding(!isAdding)}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg transition-colors shadow-sm cursor-pointer border-0"
        >
          <Plus className="w-4 h-4" />
          <span>Thiết lập ngân sách mới</span>
        </button>
      </div>

      {/* Cumulative global threshold meter */}
      <div className="p-5 bg-white border border-slate-100 rounded-xl space-y-3.5">
        <div className="flex justify-between items-center">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Định mức chi tiêu chung</span>
            <h3 className="text-base font-bold text-slate-850 mt-1">
              {formatVal(totalSpent)} tiêu dùng trong tổng số {formatVal(totalLimit)} quỹ
            </h3>
          </div>
          <span className="font-mono font-black text-slate-800 text-base">{totalRatio.toFixed(0)}%</span>
        </div>

        {/* Big cumulative bar */}
        <div className="h-3 w-full bg-slate-150 bg-slate-100 rounded-full overflow-hidden relative">
          <div 
            className="h-full rounded-full transition-all duration-300"
            style={{ 
              width: `${Math.min(totalRatio, 100)}%`,
              backgroundColor: totalRatio >= 90 ? "#ef4444" : totalRatio >= settings.budgetAlertThreshold ? "#f59e0b" : "#10b981"
            }}
          />
        </div>

        <div className="flex justify-between text-[11px] text-slate-400 font-medium">
          <span>0 (Gốc tuần)</span>
          <span className="text-slate-550 font-semibold font-sans flex items-center gap-1">
            <Info className="w-3.5 h-3.5" />
            Vạch ngưỡng đỏ tự động: Đạt {settings.budgetAlertThreshold}% hạn mức
          </span>
          <span>Hạn mức đầy</span>
        </div>
      </div>

      {/* Add new budget panel (expands inline) */}
      {isAdding && (
        <form onSubmit={handleFormSubmit} className="p-4.5 bg-emerald-50/20 border border-emerald-100/50 rounded-xl grid grid-cols-1 sm:grid-cols-3 gap-4 animate-in slide-in-from-top-4 duration-150">
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Danh mục cần tạo</label>
            <select
              value={newCat}
              onChange={(e) => setNewCat(e.target.value)}
              className="w-full px-3 py-1.8 bg-white border border-slate-150 rounded-lg text-xs font-semibold text-slate-700 outline-none"
            >
              {CHOOSE_CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider font-sans">Hạn mức giới hạn (VND)</label>
            <input
              type="number"
              required
              min="1"
              placeholder="Nhập giới hạn ví..."
              value={newLimit}
              onChange={(e) => setNewLimit(e.target.value)}
              className="w-full px-3 py-1.8 bg-white border border-slate-150 rounded-lg text-xs outline-none font-mono font-bold"
            />
          </div>
          <div className="flex items-end gap-2.5">
            <button
              type="submit"
              className="flex-1 py-1.8 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer border-0"
            >
              Kích hoạt ngay
            </button>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="py-1.8 px-3 hover:bg-slate-100 text-slate-500 rounded-lg text-xs font-semibold cursor-pointer border-0"
            >
              Hủy bỏ
            </button>
          </div>
        </form>
      )}

      {/* Category Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {budgets.map((bg) => {
          const ratio = Math.min((bg.spent / bg.limit) * 100, 100);
          const isOverThreshold = ratio >= settings.budgetAlertThreshold;
          const isEditing = editingId === bg.id;

          return (
            <div 
              key={bg.id} 
              id={`budget-card-${bg.id}`}
              className="p-5 bg-white border border-slate-100 rounded-xl flex flex-col justify-between transition-all hover:shadow-sm"
            >
              <div className="space-y-3.5">
                {/* Card Title & Icon Row */}
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2.5">
                    <div 
                      className="w-8.5 h-8.5 rounded-lg flex items-center justify-center text-white"
                      style={{ backgroundColor: bg.color }}
                    >
                      <Target className="w-4.5 h-4.5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-800">{bg.category}</h4>
                      <span className="text-[10px] text-slate-400 font-bold font-mono">ID: {bg.id.toUpperCase()}</span>
                    </div>
                  </div>

                  {/* Edit limit buttons */}
                  {!isEditing ? (
                    <button
                      onClick={() => handleEditClick(bg)}
                      className="p-1 text-slate-400 hover:text-emerald-600 hover:bg-slate-50 rounded transition-all cursor-pointer"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleSaveClick(bg.id)}
                        className="p-1 text-emerald-600 hover:bg-emerald-50 rounded transition-all cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1 text-slate-400 hover:bg-slate-50 rounded transition-all cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {/* numerical indicator values */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-slate-450 font-medium">
                    <span>Đã chi tiêu:</span>
                    <span>Định mức:</span>
                  </div>
                  <div className="flex justify-between items-baseline">
                    <span className="text-base font-extrabold text-slate-800 font-mono">
                      {formatVal(bg.spent)}
                    </span>
                    
                    {/* Editable / Numerical view limit */}
                    {isEditing ? (
                      <input
                        type="number"
                        value={editingVal}
                        onChange={(e) => setEditingVal(e.target.value)}
                        className="w-24 px-1.5 py-0.5 text-xs bg-slate-50 border border-slate-350 outline-none text-right font-mono font-bold text-slate-800"
                        autoFocus
                      />
                    ) : (
                      <span className="text-xs font-bold text-slate-400 font-mono">
                        {formatVal(bg.limit)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Progress bar and label alerts */}
                <div className="space-y-1.5">
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full rounded-full transition-all duration-300"
                      style={{ 
                        width: `${ratio}%`,
                        backgroundColor: ratio >= 100 ? "#ef4444" : isOverThreshold ? "#f59e0b" : bg.color
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-semibold text-slate-400 font-mono">
                    <span>{ratio.toFixed(0)}% SỬ DỤNG</span>
                    <span>CÒN LẠI {formatVal(Math.max(bg.limit - bg.spent, 0))}</span>
                  </div>
                </div>
              </div>

              {/* Threshold Warnings */}
              <div className="mt-4 pt-3.5 border-t border-slate-50 flex items-center gap-2">
                {ratio >= 100 ? (
                  <span className="text-[10.5px] text-red-600 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                    <span>Hạn mức đã vỡ quá giới hạn quy định!</span>
                  </span>
                ) : isOverThreshold ? (
                  <span className="text-[10.5px] text-amber-600 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    <span>Đã quá hạn canh báo ({settings.budgetAlertThreshold}%)</span>
                  </span>
                ) : (
                  <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                    <Smile className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span>Chi phí vẫn đang nằm trong vùng an toàn</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
