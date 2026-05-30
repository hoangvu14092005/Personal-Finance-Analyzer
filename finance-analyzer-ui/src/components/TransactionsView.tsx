import React, { useState, useMemo } from "react";
import { 
  Search, 
  Trash2, 
  Edit3, 
  CheckCircle, 
  AlertCircle, 
  X,
  CreditCard,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  Filter
} from "lucide-react";
import { Transaction, AppSettings } from "../types";
import { CHOOSE_CATEGORIES } from "../data/mockData";

interface TransactionsViewProps {
  transactions: Transaction[];
  settings: AppSettings;
  onAddTransaction: (t: Omit<Transaction, 'id'>) => void;
  onDeleteTransaction: (id: string) => void;
  isAddModalOpenInitially?: boolean;
}

export default function TransactionsView({ 
  transactions, 
  settings, 
  onAddTransaction,
  onDeleteTransaction,
  isAddModalOpenInitially = false
}: TransactionsViewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<'all' | 'income' | 'expense'>('all');
  const [filterCat, setFilterCat] = useState<string>("all");
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(isAddModalOpenInitially);
  
  // Form input states
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Ăn uống");
  const [type, setType] = useState<'income' | 'expense'>('expense');
  const [date, setDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<'completed' | 'pending'>('completed');

  // Filter transactions dynamically
  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      // Search matches
      const matchSearch = t.description.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          (t.note && t.note.toLowerCase().includes(searchTerm.toLowerCase()));
      // Type matching
      const matchType = filterType === 'all' || t.type === filterType;
      // Category matching
      const matchCat = filterCat === "all" || t.category === filterCat;
      
      return matchSearch && matchType && matchCat;
    });
  }, [transactions, searchTerm, filterType, filterCat]);

  const stats = useMemo(() => {
    let thu = 0;
    let chi = 0;
    filteredTransactions.forEach(t => {
      if (t.status === 'completed') {
        if (t.type === 'income') thu += t.amount;
        else chi += t.amount;
      }
    });
    return { thu, chi, ròng: thu - chi };
  }, [filteredTransactions]);

  // Format currency
  const formatVal = (num: number) => {
    return new Intl.NumberFormat(settings.currency === 'VND' ? "vi-VN" : "en-US", {
      style: "currency",
      currency: settings.currency,
      maximumFractionDigits: 0
    }).format(num);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!desc || !amount || isNaN(Number(amount))) {
      alert("Vui lòng nhập mô tả và số tiền hợp lệ!");
      return;
    }

    onAddTransaction({
      description: desc,
      amount: Math.abs(Number(amount)),
      category,
      type,
      date,
      status: status as any,
      note: note || undefined
    });

    // Reset fields
    setDesc("");
    setAmount("");
    setCategory("Ăn uống");
    setType("expense");
    setNote("");
    setStatus("completed");
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Upper overview stats header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-850">
            Sổ Nhật Ký Giao Dịch
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Tìm kiếm, thêm mới hoặc đối chiếu các giao dịch phát sinh.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg transition-colors shadow-sm cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm giao dịch mới</span>
        </button>
      </div>

      {/* Mini Grid counters matching filter parameters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-emerald-50/15 border border-emerald-100/60 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Thu nhập (Đã lọc)</span>
          <div className="text-lg font-black text-emerald-600 mt-1">{formatVal(stats.thu)}</div>
        </div>
        <div className="p-4 bg-rose-50/15 border border-rose-100/60 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Chi tiêu (Đã lọc)</span>
          <div className="text-lg font-black text-rose-500 mt-1">{formatVal(stats.chi)}</div>
        </div>
        <div className={`p-4 border rounded-xl ${stats.ròng >= 0 ? 'bg-slate-50 border-slate-100' : 'bg-rose-50/30 border-rose-100/40'}`}>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Dòng tiền ròng</span>
          <div className={`text-lg font-black mt-1 ${stats.ròng >= 0 ? 'text-slate-800' : 'text-rose-600'}`}>
            {stats.ròng >= 0 ? '+' : ''}{formatVal(stats.ròng)}
          </div>
        </div>
      </div>

      {/* Search & Filter Options layout bar */}
      <div className="p-4.5 bg-white border border-slate-100 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4.5 h-4.5 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm theo mô tả hoặc ghi chú..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 text-slate-800 placeholder-slate-400 text-sm border-0 focus:ring-2 focus:ring-emerald-500 rounded-lg outline-none"
          />
        </div>

        {/* Filters and selectors */}
        <div className="flex flex-wrap items-center gap-3.5">
          {/* Section filter */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold text-slate-500">
            <button
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 rounded-md cursor-pointer ${filterType === 'all' ? 'bg-white text-slate-800 shadow-sm' : 'hover:text-slate-900'}`}
            >
              Tất cả
            </button>
            <button
              onClick={() => setFilterType('income')}
              className={`px-3 py-1.5 rounded-md cursor-pointer ${filterType === 'income' ? 'bg-white text-emerald-700 shadow-sm' : 'hover:text-slate-900'}`}
            >
              Thu nhập
            </button>
            <button
              onClick={() => setFilterType('expense')}
              className={`px-3 py-1.5 rounded-md cursor-pointer ${filterType === 'expense' ? 'bg-white text-rose-600 shadow-sm' : 'hover:text-slate-900'}`}
            >
              Chi tiêu
            </button>
          </div>

          {/* Category SELECT filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterCat}
              onChange={(e) => setFilterCat(e.target.value)}
              className="px-3.5 py-1.5 bg-slate-50 border border-slate-150 rounded-lg text-xs font-semibold text-slate-650 outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="all">Mọi danh mục</option>
              {CHOOSE_CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Core Log Grid */}
      <div className="p-5 bg-white border border-slate-100 rounded-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-50/60">
                <th className="py-3 px-3">Giao dịch</th>
                <th className="py-3 px-3">Phân loại</th>
                <th className="py-3 px-3">Ghi chú</th>
                <th className="py-3 px-3">Thời gian</th>
                <th className="py-3 px-3 text-right">Số tiền</th>
                <th className="py-3 px-3 text-center">Trạng thái</th>
                <th className="py-3 px-3 text-center">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 text-xs text-slate-700">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-slate-400">
                    Không tìm thấy giao dịch nào khớp với tiêu chí tìm kiếm.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/20 transition-colors group">
                    <td className="py-3.5 px-3 font-semibold text-slate-800">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg shrink-0 ${t.type === 'income' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-50 text-slate-500'}`}>
                          <CreditCard className="w-4 h-4" />
                        </div>
                        <span className="font-bold">{t.description}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="px-2.5 py-0.5 bg-slate-100 text-slate-500 rounded font-semibold text-[10px]">
                        {t.category}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="text-slate-450 italic font-medium">{t.note || "—"}</span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-400 font-bold font-mono">
                      {t.date}
                    </td>
                    <td className={`py-3.5 px-3 text-right font-black font-mono text-sm ${t.type === 'income' ? 'text-emerald-600' : 'text-slate-800'}`}>
                      {t.type === 'income' ? '+' : '-'}{formatVal(t.amount)}
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-bold rounded-full ${
                        t.status === 'completed' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : 'bg-amber-50 text-amber-700 border border-amber-100'
                      }`}>
                        {t.status === 'completed' ? (
                          <>
                            <CheckCircle className="w-2.5 h-2.5" />
                            <span>Đã hoàn thành</span>
                          </>
                        ) : (
                          <>
                            <AlertCircle className="w-2.5 h-2.5" />
                            <span>Đang chờ duyệt</span>
                          </>
                        )}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          title="Xóa giao dịch"
                          onClick={() => onDeleteTransaction(t.id)}
                          className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-all cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual record dialog MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-100 max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-slate-50 flex justify-between items-center bg-slate-55">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                  ✍️
                </div>
                <h3 className="text-sm font-bold text-slate-800">Ghi chép giao dịch thủ công</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 hover:bg-slate-100 rounded-full transition-all text-slate-400 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleFormSubmit} className="p-5 space-y-4">
              {/* Type Select buttons */}
              <div className="grid grid-cols-2 gap-3.5 p-1 bg-slate-100 rounded-lg">
                <button
                  type="button"
                  onClick={() => setType('expense')}
                  className={`py-2 text-xs font-bold rounded-md transition-all cursor-pointer ${type === 'expense' ? 'bg-white text-rose-600 shadow-sm' : 'text-slate-550 hover:text-slate-800'}`}
                >
                  <div className="flex items-center justify-center gap-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-rose-500" />
                    <span>Chi Tiêu (Chi phí)</span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setType('income')}
                  className={`py-2 text-xs font-bold rounded-md transition-all cursor-pointer ${type === 'income' ? 'bg-white text-emerald-700 shadow-sm' : 'text-slate-550 hover:text-slate-800'}`}
                >
                  <div className="flex items-center justify-center gap-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Thu Nhập (Thu hoạch)</span>
                  </div>
                </button>
              </div>

              {/* Grid Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Description input */}
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Mô tả giao dịch *</label>
                  <input
                    type="text"
                    required
                    placeholder="Ví dụ: Cơm trưa rạp xiếc, Đi taxi bến xe..."
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  />
                </div>

                {/* Amount input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Số tiền (VND) *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    placeholder="Số tiền thực tế..."
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 font-mono font-bold"
                  />
                </div>

                {/* Category select */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Danh mục ngân sách</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 font-semibold"
                  >
                    {CHOOSE_CATEGORIES.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                {/* Date Input */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Ngày giao dịch</label>
                  <input
                    type="date"
                    required
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 font-mono font-bold"
                  />
                </div>

                {/* Status selector */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Trạng thái duyệt</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as any)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  >
                    <option value="completed">Đã hoàn thành</option>
                    <option value="pending">Từ từ thanh toán (Bút toán treo)</option>
                  </select>
                </div>

                {/* Notes Input */}
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Ghi chú thêm (Không bắt buộc)</label>
                  <textarea
                    rows={2}
                    placeholder="Nhập thông tin chi tiết (nếu có)..."
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 resize-none"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-3.5 border-t border-slate-100 pt-4.5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4.5 py-2 text-xs font-semibold hover:bg-slate-100 rounded-lg text-slate-500 cursor-pointer"
                >
                  Đóng lại
                </button>
                <button
                  type="submit"
                  className="px-4.5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg cursor-pointer"
                >
                  Ghi sổ ngay
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
