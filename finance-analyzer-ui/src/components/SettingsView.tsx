import React, { useState } from "react";
import { 
  User, 
  Coins, 
  Sliders, 
  Mail, 
  Cpu, 
  ShieldAlert, 
  ExternalLink,
  CheckCircle,
  HelpCircle
} from "lucide-react";
import { AppSettings } from "../types";

interface SettingsViewProps {
  settings: AppSettings;
  onUpdateSettings: (newSettings: AppSettings) => void;
}

export default function SettingsView({ settings, onUpdateSettings }: SettingsViewProps) {
  const [userName, setUserName] = useState(settings.userName);
  const [currency, setCurrency] = useState(settings.currency);
  const [budgetAlertThreshold, setBudgetAlertThreshold] = useState(settings.budgetAlertThreshold);
  const [ocrEngine, setOcrEngine] = useState(settings.ocrEngine);
  const [notificationEmail, setNotificationEmail] = useState(settings.notificationEmail);
  const [isSaved, setIsSaved] = useState(false);

  // Check if process env simulation shows key is active
  // Since we are client side we can pass flag or read from a state, let's make a beautiful visual guide
  const isKeyActive = ocrEngine === 'gemini';

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateSettings({
      userName,
      currency,
      budgetAlertThreshold,
      ocrEngine,
      notificationEmail,
      theme: "white"
    });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-850">
            Cài Đặt Hệ Thống
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Cá nhân hóa tài khoản, điều chỉnh ngưỡng cảnh báo ngân sách và cấu hình công nghệ OCR.
          </p>
        </div>

        {/* Saved Toast notice */}
        {isSaved && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.8 text-xs font-bold bg-emerald-50 text-emerald-700 rounded-lg animate-fade-in border border-emerald-150">
            <CheckCircle className="w-4.5 h-4.5" />
            <span>Đã cập nhật thay đổi thành công!</span>
          </span>
        )}
      </div>

      {/* Main Form Fields Bento Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Core fields (Profile, Currency) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Section 1: Cá nhân và Tiền tệ */}
          <div className="p-5 bg-white border border-slate-100 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 pb-3.5 border-b border-slate-50">
              <User className="w-4.5 h-4.5 text-slate-400" />
              <span>Cá nhân hóa tài khoản</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* User Name */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tên chủ sở hữu ví</label>
                <input
                  type="text"
                  required
                  placeholder="Nhập họ và tên..."
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-150 rounded-lg outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                />
              </div>

              {/* Currency type */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Đơn vị tệ hiển thị</label>
                <div className="flex gap-2.5">
                  <button
                    type="button"
                    onClick={() => setCurrency('VND')}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg border transition-all cursor-pointer ${currency === 'VND' ? 'bg-slate-900 border-slate-900 text-white' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                  >
                    Việt Nam Đồng (VND)
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrency('USD')}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg border transition-all cursor-pointer ${currency === 'USD' ? 'bg-slate-900 border-slate-900 text-white' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                  >
                    Đô-la Mỹ (USD)
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Ngưỡng canh báo */}
          <div className="p-5 bg-white border border-slate-100 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 pb-3.5 border-b border-slate-50">
              <Sliders className="w-4.5 h-4.5 text-slate-400" />
              <span>Định mức & Ngưỡng kiểm soát</span>
            </h3>

            <div className="space-y-4">
              {/* Alert range slider */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-700">Ngưỡng tự động kích hoạt canh báo đỏ:</span>
                  <span className="font-mono font-bold text-red-550 text-sm text-red-650">{budgetAlertThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="100"
                  step="5"
                  value={budgetAlertThreshold}
                  onChange={(e) => setBudgetAlertThreshold(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <p className="text-[10px] text-slate-400">Hệ thống sẽ bật báo động cam/đỏ trên trang Tổng quan và Ngân sách khi danh mục của bạn chạm ngưỡng này.</p>
              </div>

              {/* Notification toggle */}
              <div className="flex items-start gap-3.5 pt-2">
                <input
                  type="checkbox"
                  id="notif_email"
                  checked={notificationEmail}
                  onChange={(e) => setNotificationEmail(e.target.checked)}
                  className="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500 mt-0.5 cursor-pointer"
                />
                <div className="space-y-0.5 select-none">
                  <label htmlFor="notif_email" className="text-xs font-bold text-slate-700 cursor-pointer">Báo cáo bọc tài chính qua Email mỗi tháng</label>
                  <p className="text-[10px] text-slate-400">Gửi tổng kết bảng lương, định mức đã chi tiêu và insights tư duy tự động vào hòm thư cá nhân.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right side options: AI config (OCR, credentials guide) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Section 3: Trí tuệ Nhân tạo OCR và Setup secrets */}
          <div className="p-5 bg-white border border-slate-100 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 pb-3.5 border-b border-slate-50">
              <Cpu className="w-4.5 h-4.5 text-slate-400" />
              <span>Cấu hình Trí tuệ Nhân tạo OCR</span>
            </h3>

            <div className="space-y-4">
              {/* OCR Engine Selection options */}
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Bộ máy phân tích bóc tách</label>
                <div className="space-y-2">
                  <label className="flex items-start gap-2.5 p-2.5 border rounded-lg hover:bg-slate-50/50 cursor-pointer text-xs">
                    <input
                      type="radio"
                      name="ocr_engine_select"
                      value="gemini"
                      checked={ocrEngine === 'gemini'}
                      onChange={() => setOcrEngine('gemini')}
                      className="w-4 h-4 text-emerald-600 focus:ring-emerald-500 mt-0.5 cursor-pointer"
                    />
                    <div>
                      <strong className="text-slate-750 block font-bold leading-normal">Gemini Multimodal Vision AI</strong>
                      <span className="text-[10px] text-slate-400 leading-normal block mt-0.5">Yêu cầu GEMINI_API_KEY. Bóc tách chính xác mọi dòng sản phẩm, ngày tháng thực tế từ hình ảnh tải lên.</span>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-2.5 border rounded-lg hover:bg-slate-50/50 cursor-pointer text-xs">
                    <input
                      type="radio"
                      name="ocr_engine_select"
                      value="mock-high-speed"
                      checked={ocrEngine === 'mock-high-speed'}
                      onChange={() => setOcrEngine('mock-high-speed')}
                      className="w-4 h-4 text-emerald-600 focus:ring-emerald-500 mt-0.5 cursor-pointer"
                    />
                    <div>
                      <strong className="text-slate-750 block font-bold leading-normal">Simulated High-Speed (Ngoại tuyến)</strong>
                      <span className="text-[10px] text-slate-400 leading-normal block mt-0.5">Không cần API key. Sử dụng mô phỏng logic tiếng Việt cao cấp để kiểm chứng giao diện hoạt động tức thời.</span>
                    </div>
                  </label>
                </div>
              </div>

              {/* API Secrets tutorial box */}
              <div className="p-3.5 rounded-lg border border-slate-100 bg-[#f8fafc] space-y-2 text-xs">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
                  <span>Cách truyền Secrets ở AI Studio</span>
                </span>
                <p className="text-[11px] leading-relaxed text-slate-500">
                  Ứng dụng này sử dụng server-side proxy bảo mật để bảo vệ thông tin API của bạn. Để cài đặt khóa:
                </p>
                <ol className="list-decimal pl-4.5 text-[10.5px] text-slate-600 space-y-1 font-medium leading-relaxed">
                  <li>Tìm bảng điều khiển <strong className="text-slate-800">Secrets / Cài đặt</strong> ở AI Studio UI.</li>
                  <li>Thêm một biến có nhãn định danh: <code className="bg-slate-200/50 px-1 py-0.5 rounded font-mono font-bold text-slate-800">GEMINI_API_KEY</code></li>
                  <li>Dán khóa API của Google GenAI vào giá trị và lưu lại.</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Form Submission buttons */}
      <div className="flex justify-end pt-4.5 border-t border-slate-100">
        <button
          type="submit"
          className="px-6 py-2.8 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-md tracking-wider transition-all cursor-pointer border-0"
        >
          Lưu tất cả cấu hình cài đặt
        </button>
      </div>
    </form>
  );
}
