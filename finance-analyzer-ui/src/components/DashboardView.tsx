import { useState, useMemo } from "react";
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Wallet, 
  PiggyBank, 
  ChevronRight, 
  Plus,
  TrendingUp,
  TrendingDown,
  Clock
} from "lucide-react";
import { Transaction, Budget, AppSettings } from "../types";

interface DashboardViewProps {
  transactions: Transaction[];
  budgets: Budget[];
  settings: AppSettings;
  onAddTransactionClick: () => void;
  onNavigateToTab: (tab: string) => void;
}

export default function DashboardView({ 
  transactions, 
  budgets, 
  settings,
  onAddTransactionClick,
  onNavigateToTab
}: DashboardViewProps) {
  const [hoveredChartIndex, setHoveredChartIndex] = useState<number | null>(null);
  
  // Custom interactive dashboard view states
  const [activeLeftTab, setActiveLeftTab] = useState<'bar' | 'line'>('bar');
  const [activeRightTab, setActiveRightTab] = useState<'progress' | 'donut'>('progress');
  const [hoveredDonutIndex, setHoveredDonutIndex] = useState<number | null>(null);
  const [hoveredLineIndex, setHoveredLineIndex] = useState<number | null>(null);

  // Group completed expenses and incomes by date for the line/area trend graph
  const trendLineData = useMemo(() => {
    // Generate the last 10 active dates based on the transaction lists
    const dates = Array.from(new Set(transactions.map(t => t.date)))
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b))
      .slice(-10); // get last 10 days

    // Fallback if transaction data is scarce or sparse
    if (dates.length < 5) {
      const fallbackDates = [];
      for (let i = 9; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        fallbackDates.push(d.toISOString().split('T')[0]);
      }
      return fallbackDates.sort().map(dt => {
        const matching = transactions.filter(t => t.date === dt && t.status === 'completed');
        const income = matching.filter(t => t.type === 'income').reduce((acc, curr) => acc + curr.amount, 0);
        const expense = matching.filter(t => t.type === 'expense').reduce((acc, curr) => acc + curr.amount, 0);
        return {
          date: dt,
          displayDate: dt.substring(8) + "/" + dt.substring(5, 7),
          income,
          expense
        };
      });
    }

    return dates.map(dt => {
      const matching = transactions.filter(t => t.date === dt && t.status === 'completed');
      const income = matching.filter(t => t.type === 'income').reduce((acc, curr) => acc + curr.amount, 0);
      const expense = matching.filter(t => t.type === 'expense').reduce((acc, curr) => acc + curr.amount, 0);
      return {
        date: dt,
        displayDate: dt.substring(8) + "/" + dt.substring(5, 7),
        income,
        expense
      };
    });
  }, [transactions]);

  const lineMaxY = useMemo(() => {
    return Math.max(...trendLineData.flatMap(d => [d.expense, d.income]), 1000000);
  }, [trendLineData]);

  // Expenditure distribution structure for interactive Donut Chart
  const donutData = useMemo(() => {
    const summary: Record<string, { spent: number; color: string }> = {};
    const colorsMap: Record<string, string> = {
      "Ăn uống": "#f59e0b",
      "Mua sắm": "#3b82f6",
      "Hóa đơn": "#ef4444",
      "Di chuyển": "#10b981",
      "Sức khỏe": "#ec4899",
      "Giải trí": "#8b5cf6",
      "Khác": "#64748b"
    };

    budgets.forEach(b => {
      summary[b.category] = { spent: b.spent, color: b.color || colorsMap[b.category] || "#64748b" };
    });

    const items = Object.entries(summary)
      .map(([cat, val]) => ({
        category: cat,
        spent: val.spent,
        color: val.color
      }))
      .filter(item => item.spent > 0)
      .sort((a, b) => b.spent - a.spent);

    const totalSpent = items.reduce((s, c) => s + c.spent, 0);

    return items.map(it => ({
      ...it,
      percentage: totalSpent > 0 ? (it.spent / totalSpent) * 100 : 0
    }));
  }, [budgets]);

  const totalDonutSpent = useMemo(() => {
    return donutData.reduce((s, c) => s + c.spent, 0);
  }, [donutData]);

  // General statistics computations
  const stats = useMemo(() => {
    let totalIncome = 0;
    let totalExpense = 0;
    
    transactions.forEach(t => {
      if (t.status === 'completed') {
        if (t.type === 'income') totalIncome += t.amount;
        else totalExpense += t.amount;
      }
    });

    const netBalance = totalIncome - totalExpense;
    const totalBudgetLimit = budgets.reduce((acc, curr) => acc + curr.limit, 0);
    const totalBudgetSpent = budgets.reduce((acc, curr) => acc + curr.spent, 0);
    const savingsRatio = totalIncome > 0 ? (netBalance / totalIncome) * 100 : 0;

    return {
      totalIncome,
      totalExpense,
      netBalance,
      totalBudgetLimit,
      totalBudgetSpent,
      savingsRatio
    };
  }, [transactions, budgets]);

  // Format monetary quantities safely
  const formatVal = (num: number) => {
    return new Intl.NumberFormat(settings.currency === 'VND' ? "vi-VN" : "en-US", {
      style: "currency",
      currency: settings.currency,
      maximumFractionDigits: 0
    }).format(num);
  };

  // Custom high-fidelity graph data (Weekly structure)
  const chartData = [
    { name: "Khóa 1", thu: 4500000, chi: 1200000 },
    { name: "Khóa 2", thu: 5000000, chi: 1850000 },
    { name: "Khóa 3", thu: 3000000, chi: 3400000 },
    { name: "Khóa 4", thu: 6000000, chi: 1560000 },
    { name: "Khóa 5", thu: 6000000, chi: 3200000 }
  ];

  const maxVal = Math.max(...chartData.flatMap(d => [d.thu, d.chi]), 1);

  return (
    <div className="space-y-6">
      {/* Upper header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-850">
            Chào mừng trở lại, {settings.userName}!
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Xem báo cáo tổng thể, ngân sách và phân tích tài chính ngày hôm nay.
          </p>
        </div>
        <button
          onClick={onAddTransactionClick}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg transition-colors shadow-sm cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Ghi chép giao dịch</span>
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Thu Nhập Widget */}
        <div id="stat-income-card" className="p-5 bg-white border border-slate-100 rounded-xl flex items-center justify-between transition-all hover:shadow-sm">
          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tổng thu nhập</span>
            <div className="text-xl font-black text-slate-800 leading-none">
              {formatVal(stats.totalIncome)}
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>+14.2% so với tháng trước</span>
            </div>
          </div>
          <div className="w-11 h-11 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <ArrowUpRight className="w-6 h-6 stroke-[2.2]" />
          </div>
        </div>

        {/* Chi Tiêu Widget */}
        <div id="stat-expense-card" className="p-5 bg-white border border-slate-100 rounded-xl flex items-center justify-between transition-all hover:shadow-sm">
          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tổng chi tiêu</span>
            <div className="text-xl font-black text-[#f43f5e] leading-none">
              {formatVal(stats.totalExpense)}
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-rose-600">
              <TrendingDown className="w-3.5 h-3.5" />
              <span>+5.8% mức tiêu dùng thường nhật</span>
            </div>
          </div>
          <div className="w-11 h-11 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center shrink-0">
            <ArrowDownRight className="w-6 h-6 stroke-[2.2]" />
          </div>
        </div>

        {/* Số Dư Ví Widget */}
        <div id="stat-balance-card" className="p-5 bg-white border border-slate-100 rounded-xl flex items-center justify-between transition-all hover:shadow-sm">
          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Số dư hiện tại</span>
            <div className="text-xl font-black text-slate-800 leading-none">
              {formatVal(stats.netBalance)}
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-blue-600">
              <Wallet className="w-3.5 h-3.5" />
              <span>Ổn định, an toàn đầu tư</span>
            </div>
          </div>
          <div className="w-11 h-11 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <Wallet className="w-5.5 h-5.5" />
          </div>
        </div>

        {/* Tỷ Lệ Tích Lũy Widget */}
        <div id="stat-savings-card" className="p-5 bg-white border border-slate-100 rounded-xl flex items-center justify-between transition-all hover:shadow-sm">
          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Tỷ lệ tích lũy</span>
            <div className="text-xl font-black text-slate-800 leading-none">
              {stats.savingsRatio.toFixed(1)}%
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-500">
              <PiggyBank className="w-3.5 h-3.5 text-slate-400" />
              <span>Mục tiêu tích lũy lý tưởng: 20%</span>
            </div>
          </div>
          <div className="w-11 h-11 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <PiggyBank className="w-5.5 h-5.5" />
          </div>
        </div>
      </div>

      {/* Main Graph Area and Category Budget Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Interactive Comparison bar/line chart */}
        <div className="lg:col-span-8 p-5 bg-white border border-slate-100 rounded-xl flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-slate-50">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-bold text-slate-800">
                  Phân tích Dòng tiền
                </h3>
                {/* Switch Tabs */}
                <div className="inline-flex rounded-lg bg-slate-100/80 p-0.5 text-[11px] font-medium">
                  <button
                    onClick={() => setActiveLeftTab('bar')}
                    className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                      activeLeftTab === 'bar'
                        ? 'bg-white text-slate-850 font-bold shadow-xs'
                        : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    Cột mốc (Mới)
                  </button>
                  <button
                    onClick={() => setActiveLeftTab('line')}
                    className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                      activeLeftTab === 'line'
                        ? 'bg-white text-slate-850 font-bold shadow-xs'
                        : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    Xu hướng ngày
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {activeLeftTab === 'bar' 
                  ? 'Thống kê theo từng đợt dòng tiền phát sinh trong tháng này' 
                  : 'Xu hướng biến động thu chi qua 10 mốc giao dịch gần nhất'}
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs font-semibold">
              <div className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
                <span className="text-slate-500 text-[11px]">Thu</span>
              </div>
              <div className="flex items-center gap-1 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
                <span className="text-slate-500 text-[11px]">Chi</span>
              </div>
            </div>
          </div>

          {activeLeftTab === 'bar' ? (
            /* SVG Custom Interactive BAR Graph container */
            <div className="h-64 mt-4 relative flex items-end justify-between px-4 pb-2">
              {chartData.map((d, index) => {
                const heightThu = (d.thu / maxVal) * 160;
                const heightChi = (d.chi / maxVal) * 160;

                return (
                  <div 
                    key={index} 
                    className="flex flex-col items-center flex-1 group"
                    onMouseEnter={() => setHoveredChartIndex(index)}
                    onMouseLeave={() => setHoveredChartIndex(null)}
                  >
                    <div className="flex items-end gap-2.5 justify-center w-full" style={{ height: "180px" }}>
                      {/* Income Bar (Green) */}
                      <div 
                        className={`w-6 rounded-t-md transition-all duration-250 cursor-pointer ${
                          hoveredChartIndex === index 
                            ? "bg-emerald-600 shadow-md translate-y-[-2px]" 
                            : "bg-emerald-500/85 hover:bg-emerald-600"
                        }`}
                        style={{ height: `${Math.max(heightThu, 15)}px` }}
                      />
                      {/* Expense Bar (Rose) */}
                      <div 
                        className={`w-6 rounded-t-md transition-all duration-250 cursor-pointer ${
                          hoveredChartIndex === index 
                            ? "bg-rose-600 shadow-md translate-y-[-2px]" 
                            : "bg-rose-500/85 hover:bg-rose-600"
                        }`}
                        style={{ height: `${Math.max(heightChi, 15)}px` }}
                      />
                    </div>
                    {/* Label */}
                    <span className="text-[10px] font-mono font-bold text-slate-400 mt-2.5 uppercase tracking-wider">
                      {d.name}
                    </span>
                  </div>
                );
              })}

              {/* Dynamic Graph Tooltip */}
              {hoveredChartIndex !== null && (
                <div className="absolute top-2 left-1/2 transform -translate-x-1/2 bg-slate-900/95 text-white px-3.5 py-2.5 rounded-lg shadow-xl text-xs z-20 pointer-events-none transition-opacity flex flex-col gap-1 w-44">
                  <span className="font-bold text-slate-300 border-b border-slate-700/60 pb-1 mb-1 block">
                    Cột mốc {chartData[hoveredChartIndex].name}
                  </span>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-medium">Thu nhập:</span>
                    <span className="text-emerald-400 font-bold font-mono">{formatVal(chartData[hoveredChartIndex].thu)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-medium">Chi tiêu:</span>
                    <span className="text-rose-400 font-bold font-mono">{formatVal(chartData[hoveredChartIndex].chi)}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* BRAND NEW: Interactive Dual Area & Line chart using pure SVG gradients */
            <div className="h-64 mt-4 relative flex flex-col justify-end">
              <div className="w-full h-[180px] relative">
                {/* Background Grid Lines */}
                <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-50">
                  <div className="border-b border-dashed border-slate-100 w-full h-0"></div>
                  <div className="border-b border-dashed border-slate-100 w-full h-0"></div>
                  <div className="border-b border-dashed border-slate-100 w-full h-0"></div>
                  <div className="border-b border-dashed border-slate-100 w-full h-0"></div>
                </div>

                {/* SVG Graphics */}
                <svg className="w-full h-full overflow-visible" viewBox="0 0 500 150" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="income-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                    </linearGradient>
                    <linearGradient id="expense-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.18" />
                      <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Areas Under Lines */}
                  {(() => {
                    const incPoints = trendLineData.map((d, i) => ({
                      x: 25 + i * (450 / (trendLineData.length - 1)),
                      y: 135 - (d.income / lineMaxY) * 110
                    }));
                    const expPoints = trendLineData.map((d, i) => ({
                      x: 25 + i * (450 / (trendLineData.length - 1)),
                      y: 135 - (d.expense / lineMaxY) * 110
                    }));

                    const incPathD = incPoints.length > 0 
                      ? `M ${incPoints[0].x} ${incPoints[0].y} ` + incPoints.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ') 
                      : '';
                    const expPathD = expPoints.length > 0 
                      ? `M ${expPoints[0].x} ${expPoints[0].y} ` + expPoints.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ') 
                      : '';

                    const incAreaD = incPoints.length > 0
                      ? `${incPathD} L ${incPoints[incPoints.length - 1].x} 145 L ${incPoints[0].x} 145 Z`
                      : '';
                    const expAreaD = expPoints.length > 0
                      ? `${expPathD} L ${expPoints[expPoints.length - 1].x} 145 L ${expPoints[0].x} 145 Z`
                      : '';

                    return (
                      <>
                        {/* Area backgrounds */}
                        {incAreaD && <path d={incAreaD} fill="url(#income-grad)" />}
                        {expAreaD && <path d={expAreaD} fill="url(#expense-grad)" />}

                        {/* Line paths */}
                        {incPathD && <path d={incPathD} fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
                        {expPathD && <path d={expPathD} fill="none" stroke="#f43f5e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}

                        {/* Clickable Hover circles */}
                        {trendLineData.map((d, i) => {
                          const cx = 25 + i * (450 / (trendLineData.length - 1));
                          const cyExp = 135 - (d.expense / lineMaxY) * 110;
                          const cyInc = 135 - (d.income / lineMaxY) * 110;

                          return (
                            <g key={i} className="cursor-pointer">
                              {/* Income dot */}
                              <circle 
                                cx={cx} 
                                cy={cyInc} 
                                r={hoveredLineIndex === i ? "6" : "4"} 
                                fill="#ffffff" 
                                stroke="#10b981" 
                                strokeWidth="2" 
                                onMouseEnter={() => setHoveredLineIndex(i)}
                                onMouseLeave={() => setHoveredLineIndex(null)}
                                className="transition-all"
                              />
                              {/* Expense dot */}
                              <circle 
                                cx={cx} 
                                cy={cyExp} 
                                r={hoveredLineIndex === i ? "6" : "4"} 
                                fill="#ffffff" 
                                stroke="#f43f5e" 
                                strokeWidth="2" 
                                onMouseEnter={() => setHoveredLineIndex(i)}
                                onMouseLeave={() => setHoveredLineIndex(null)}
                                className="transition-all"
                              />
                            </g>
                          );
                        })}
                      </>
                    );
                  })()}
                </svg>
              </div>

              {/* Horizontal Axis Dates label */}
              <div className="flex justify-between px-2 mt-2 border-t border-slate-50 pt-1.5">
                {trendLineData.map((d, idx) => (
                  <span key={idx} className="text-[9px] font-mono font-bold text-slate-400">
                    {d.displayDate}
                  </span>
                ))}
              </div>

              {/* Hover line chart tooltip */}
              {hoveredLineIndex !== null && (
                <div className="absolute top-1 left-1/2 transform -translate-x-1/2 bg-slate-900/95 text-white px-3.5 py-2.5 rounded-lg shadow-xl text-xs z-20 pointer-events-none flex flex-col gap-1 w-44">
                  <span className="font-bold text-slate-300 border-b border-slate-700/60 pb-1 mb-1 block">
                    Ngày: {trendLineData[hoveredLineIndex].date}
                  </span>
                  <div className="flex justify-between">
                    <span className="text-emerald-400 font-semibold flex items-center gap-1">● Thu:</span>
                    <span className="font-mono font-bold text-emerald-400">{formatVal(trendLineData[hoveredLineIndex].income)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-rose-400 font-semibold flex items-center gap-1">● Chi:</span>
                    <span className="font-mono font-bold text-rose-400">{formatVal(trendLineData[hoveredLineIndex].expense)}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Real-time Category Budget meters and interactive donut breakdown */}
        <div className="lg:col-span-4 p-5 bg-white border border-slate-100 rounded-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-50">
              <h3 className="text-sm font-bold text-slate-800">Cơ cấu ngân sách</h3>
              
              {/* Toggle Pills */}
              <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-[10px] font-semibold">
                <button 
                  onClick={() => setActiveRightTab('progress')}
                  className={`px-2 py-1 rounded-md transition-all cursor-pointer ${
                    activeRightTab === 'progress' 
                      ? 'bg-white text-slate-800 shadow-xs font-bold' 
                      : 'text-slate-400 hover:text-slate-750'
                  }`}
                >
                  Hạn mức
                </button>
                <button 
                  onClick={() => setActiveRightTab('donut')}
                  className={`px-2 py-1 rounded-md transition-all cursor-pointer ${
                    activeRightTab === 'donut' 
                      ? 'bg-white text-slate-800 shadow-xs font-bold' 
                      : 'text-slate-400 hover:text-slate-750'
                  }`}
                >
                  Tỉ trọng (%)
                </button>
              </div>
            </div>

            {activeRightTab === 'progress' ? (
              /* Progress list */
              <div className="space-y-4 mt-4.5">
                {budgets.slice(0, 4).map((bg) => {
                  const ratio = Math.min((bg.spent / bg.limit) * 100, 100);
                  const isOverThreshold = ratio >= settings.budgetAlertThreshold;

                  return (
                    <div key={bg.id} className="space-y-1.5" id={`budget-widget-${bg.id}`}>
                      <div className="flex justify-between text-xs">
                        <span className="font-semibold text-slate-700">{bg.category}</span>
                        <span className="font-mono font-bold text-slate-500">
                          {formatVal(bg.spent)} / {formatVal(bg.limit)}
                        </span>
                      </div>
                      {/* Slider Progress Indicator */}
                      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden relative">
                        <div 
                          className="h-full rounded-full transition-all duration-300"
                          style={{ 
                            width: `${ratio}%`,
                            backgroundColor: ratio >= 90 ? "#ef4444" : isOverThreshold ? "#f59e0b" : bg.color 
                          }}
                        />
                      </div>
                      {/* Alert trigger caption */}
                      {ratio >= 90 ? (
                        <span className="text-[10px] text-red-500 font-bold flex items-center gap-1">
                          ⚠️ ĐÃ VƯỢT QUÁ HẠN MỨC CHO PHÉP!
                        </span>
                      ) : isOverThreshold ? (
                        <span className="text-[10px] text-amber-500 font-semibold flex items-center gap-1">
                          ⚠️ Đạt {ratio.toFixed(0)}% chuẩn cảnh báo ({settings.budgetAlertThreshold}%)
                        </span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              /* BRAND NEW: Interactive Custom SVG Donut Chart with a center interactive text label layout */
              <div className="mt-4.5 flex flex-col items-center">
                <div className="relative w-40 h-40">
                  <svg className="w-full h-full" viewBox="0 0 100 100">
                    {/* SVG Donut Slices */}
                    {(() => {
                      let cumulativePercentage = 0;
                      return donutData.map((it, idx) => {
                        const percentage = it.percentage;
                        const strokeDashoffset = 238.76 - (percentage / 100) * 238.76;
                        const activeRotation = -90 + (cumulativePercentage / 100) * 360;
                        cumulativePercentage += percentage;

                        return (
                          <circle
                            key={idx}
                            cx="50"
                            cy="50"
                            r="38"
                            fill="transparent"
                            stroke={it.color}
                            strokeWidth={hoveredDonutIndex === idx ? "11.5" : "9"}
                            strokeDasharray="238.76"
                            strokeDashoffset={strokeDashoffset}
                            transform={`rotate(${activeRotation} 50 50)`}
                            className="transition-all duration-250 cursor-pointer"
                            onMouseEnter={() => setHoveredDonutIndex(idx)}
                            onMouseLeave={() => setHoveredDonutIndex(null)}
                          />
                        );
                      });
                    })()}

                    {/* Rich text markers centered in the donut hole */}
                    <text x="50" y="44" textAnchor="middle" className="text-[7px] font-bold fill-slate-400 font-sans uppercase tracking-wider">
                      {hoveredDonutIndex !== null ? donutData[hoveredDonutIndex].category : "Tổng đã chi"}
                    </text>
                    <text x="50" y="55" textAnchor="middle" className="text-[9px] font-black fill-slate-800 font-mono leading-none">
                      {hoveredDonutIndex !== null ? formatVal(donutData[hoveredDonutIndex].spent) : formatVal(totalDonutSpent)}
                    </text>
                    <text x="50" y="64" textAnchor="middle" className="text-[6.5px] font-bold fill-emerald-600 font-sans">
                      {hoveredDonutIndex !== null ? `${donutData[hoveredDonutIndex].percentage.toFixed(1)}%` : "Bản đồ cơ cấu"}
                    </text>
                  </svg>
                </div>

                {/* Legend labels grid */}
                <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 w-full mt-4 text-[10px] border-t border-slate-50 pt-3">
                  {donutData.slice(0, 6).map((it, idx) => (
                    <div 
                      key={idx} 
                      className={`flex items-center gap-1.5 p-1 rounded transition-colors ${
                        hoveredDonutIndex === idx ? 'bg-slate-50' : ''
                      }`}
                      onMouseEnter={() => setHoveredDonutIndex(idx)}
                      onMouseLeave={() => setHoveredDonutIndex(null)}
                    >
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: it.color }} />
                      <span className="truncate text-slate-600 font-semibold">{it.category}</span>
                      <span className="font-mono text-slate-400 font-bold ml-auto">{it.percentage.toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="p-3 bg-emerald-50/45 rounded-lg border border-emerald-100/60 flex items-center gap-3 mt-4">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 font-bold text-sm">
              💡
            </div>
            <p className="text-[11px] font-medium leading-relaxed text-slate-600">
               Ngân sách hóa đơn ở ngưỡng đỏ. Hãy bớt đặt ăn ngoài để tối ưu lại hạn mức chi tiêu.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Activities Section */}
      <div className="p-5 bg-white border border-slate-100 rounded-xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-50">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Giao dịch phát sinh gần đây</h3>
            <p className="text-xs text-slate-400 mt-0.5">Liệt kê tất cả nguồn thu, nguồn chi thực tế trong tháng này</p>
          </div>
          <button
            onClick={() => onNavigateToTab("transactions")}
            className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 hover:underline inline-flex items-center gap-1 cursor-pointer"
          >
            <span>Nhật ký giao dịch</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Compact transaction list */}
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-50/60">
                <th className="py-3 px-3">Giao dịch</th>
                <th className="py-3 px-3">Phân loại</th>
                <th className="py-3 px-3">Thời gian</th>
                <th className="py-3 px-3 text-right">Số tiền</th>
                <th className="py-3 px-3 text-center">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 text-xs text-slate-700">
              {transactions.slice(0, 5).map((t) => (
                <tr key={t.id} className="hover:bg-slate-50/30 transition-colors group">
                  <td className="py-3 px-3 font-semibold text-slate-800">
                    <div className="flex flex-col">
                      <span>{t.description}</span>
                      {t.note && <span className="text-[10px] text-slate-400 font-normal mt-0.5 mt-0.5">{t.note}</span>}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 bg-slate-100/60 text-slate-500 rounded font-semibold text-[10px]">
                      {t.category}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-400 font-medium">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-300" />
                      <span>{t.date}</span>
                    </div>
                  </td>
                  <td className={`py-3 px-3 text-right font-bold font-mono text-sm ${t.type === 'income' ? 'text-emerald-600' : 'text-slate-800'}`}>
                    {t.type === 'income' ? '+' : '-'}{formatVal(t.amount)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={`inline-flex items-center justify-center px-2 py-0.5 text-[9px] font-bold rounded-full border ${
                      t.status === 'completed' 
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-100' 
                        : t.status === 'pending'
                        ? 'bg-amber-50 text-amber-700 border-amber-100'
                        : 'bg-rose-50 text-rose-700 border-rose-100'
                    }`}>
                      {t.status === 'completed' ? 'Thành công' : t.status === 'pending' ? 'Đang duyệt' : 'Hủy bỏ'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
