import React, { useState, useRef } from "react";
import { 
  Upload, 
  FileText, 
  Check, 
  RefreshCw, 
  Sparkles, 
  ArrowRight, 
  Trash2, 
  Plus, 
  AlertTriangle,
  ZoomIn
} from "lucide-react";
import { ReceiptUpload, RecognizedReceipt, AppSettings } from "../types";
import { CHOOSE_CATEGORIES } from "../data/mockData";

interface ReceiptOCRViewProps {
  uploads: ReceiptUpload[];
  settings: AppSettings;
  onOCRComplete: (receipt: ReceiptUpload) => void;
  onSyncToTransactions: (uploadId: string, finalData: RecognizedReceipt) => void;
}

export default function ReceiptOCRView({ 
  uploads, 
  settings, 
  onOCRComplete,
  onSyncToTransactions 
}: ReceiptOCRViewProps) {
  const [selectedUploadId, setSelectedUploadId] = useState<string | null>(uploads[0]?.id || null);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errMessage, setErrMessage] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Editable recognized receipt state
  const [editingReceipt, setEditingReceipt] = useState<RecognizedReceipt | null>(() => {
    const initial = uploads.find(u => u.id === selectedUploadId);
    return initial?.recognizedData ? JSON.parse(JSON.stringify(initial.recognizedData)) : null;
  });

  const selectedUpload = uploads.find(u => u.id === selectedUploadId);

  // Currency Formatter
  const formatVal = (num: number) => {
    return new Intl.NumberFormat(settings.currency === 'VND' ? "vi-VN" : "en-US", {
      style: "currency",
      currency: settings.currency,
      maximumFractionDigits: 0
    }).format(num);
  };

  // Change currently selected upload
  const handleSelectUpload = (id: string) => {
    setSelectedUploadId(id);
    const curr = uploads.find(u => u.id === id);
    if (curr?.recognizedData) {
      setEditingReceipt(JSON.parse(JSON.stringify(curr.recognizedData)));
    } else {
      setEditingReceipt(null);
    }
    setErrMessage(null);
  };

  // File drag & drop triggers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.value && e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  // Core File -> Base64 -> API POST flow
  const processFile = (file: File) => {
    setIsProcessing(true);
    setErrMessage(null);
    
    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64String = event.target?.result as string;
      const uploadId = `up-gen-${Date.now()}`;
      
      try {
        const response = await fetch("/api/ocr", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            imageBase64: base64String,
            mimeType: file.type || "image/png",
            fileName: file.name
          })
        });

        if (!response.ok) {
          throw new Error("Mã lỗi máy chủ OCR: " + response.status);
        }

        const data = await response.json();
        const outputUpload: ReceiptUpload = {
          id: uploadId,
          fileName: file.name,
          fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
          uploadDate: new Date().toISOString().split("T")[0],
          status: "success",
          recognizedData: data.recognizedData
        };

        onOCRComplete(outputUpload);
        setSelectedUploadId(uploadId);
        setEditingReceipt(data.recognizedData);

      } catch (err: any) {
        console.error("OCR Processing failed:", err);
        setErrMessage("Không hỗ trợ giải mã tệp này hoặc lỗi kết nối. Đang sử dụng Mock OCR cục bộ...");
        
        // Instant graceful mock fallback
        const mockData = getLocalFallbackData(file.name);
        const fallbackUpload: ReceiptUpload = {
          id: uploadId,
          fileName: file.name,
          fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
          uploadDate: new Date().toISOString().split("T")[0],
          status: "success",
          recognizedData: mockData
        };
        onOCRComplete(fallbackUpload);
        setSelectedUploadId(uploadId);
        setEditingReceipt(mockData);
      } finally {
        setIsProcessing(false);
      }
    };

    reader.readAsDataURL(file);
  };

  // Quick preset loader buttons
  const loadPresetReceipt = (presetName: string) => {
    setIsProcessing(true);
    setErrMessage(null);

    // Simulated network processing latency
    setTimeout(() => {
      const mockResult = getLocalFallbackData(presetName);
      const newUpload: ReceiptUpload = {
        id: `up-preset-${Date.now()}`,
        fileName: presetName,
        fileSize: "1.5 MB",
        uploadDate: new Date().toISOString().split("T")[0],
        status: "success",
        recognizedData: mockResult
      };

      onOCRComplete(newUpload);
      setSelectedUploadId(newUpload.id);
      setEditingReceipt(mockResult);
      setIsProcessing(false);
    }, 1200);
  };

  // Sync edited results back to transaction logs
  const handleSyncClick = () => {
    if (!selectedUploadId || !editingReceipt) return;
    
    // Sum total before syncing
    const itemsTotal = editingReceipt.items.reduce((s, it) => s + (it.price * it.qty), 0);
    const finalData = {
      ...editingReceipt,
      total: itemsTotal > 0 ? itemsTotal : editingReceipt.total
    };

    onSyncToTransactions(selectedUploadId, finalData);
    
    // Update active row status directly
    const updatedUploadsList = uploads.map(u => u.id === selectedUploadId ? { ...u, status: 'synced' as const, recognizedData: finalData } : u);
    setEditingReceipt(null);
  };

  // Form manipulation actions
  const handleItemValueChange = (itemId: string, field: 'name' | 'qty' | 'price', val: any) => {
    if (!editingReceipt) return;
    const updatedItems = editingReceipt.items.map(it => {
      if (it.id === itemId) {
        return {
          ...it,
          [field]: field === 'name' ? val : Number(val)
        };
      }
      return it;
    });

    // Recompute total sum
    const newSum = updatedItems.reduce((acc, curr) => acc + (curr.price * curr.qty), 0);
    setEditingReceipt({
      ...editingReceipt,
      items: updatedItems,
      total: newSum
    });
  };

  const handleAddField = () => {
    if (!editingReceipt) return;
    const newItem = {
      id: `field-gen-${Date.now()}`,
      name: "Sản phẩm mới",
      qty: 1,
      price: 15000
    };
    const updated = [...editingReceipt.items, newItem];
    setEditingReceipt({
      ...editingReceipt,
      items: updated,
      total: updated.reduce((acc, curr) => acc + (curr.price * curr.qty), 0)
    });
  };

  const handleRemoveField = (id: string) => {
    if (!editingReceipt) return;
    const updated = editingReceipt.items.filter(it => it.id !== id);
    setEditingReceipt({
      ...editingReceipt,
      items: updated,
      total: updated.reduce((acc, curr) => acc + (curr.price * curr.qty), 0)
    });
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-850">
          Tự Động Trích Xuất Hóa Đơn (OCR Scan)
        </h2>
        <p className="text-sm text-slate-400 mt-0.5">
          Tải ảnh hóa đơn lên để AI bóc tách chi tiết từng sản phẩm, ngày mua và tự động ghi sổ tài chính nhanh chóng.
        </p>
      </div>

      {/* Upload Drag Card vs Presets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Upload Drop Zone Area */}
        <div id="ocr-uploaddrop-card" className="md:col-span-2">
          <div 
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`h-48 border-2 border-dashed rounded-xl flex flex-col items-center justify-center p-6 text-center transition-all duration-200 cursor-pointer ${
              dragActive 
                ? "border-emerald-500 bg-emerald-50/20" 
                : "border-slate-200 bg-white hover:border-emerald-500 hover:bg-slate-50/40"
            }`}
          >
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFileInput}
              accept="image/*"
              className="hidden" 
            />
            {isProcessing ? (
              <div className="flex flex-col items-center gap-3">
                <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin" />
                <p className="text-sm font-bold text-slate-700">AI đang phân tích & bóc tách hóa đơn...</p>
                <p className="text-xs text-slate-400">Có thể mất từ 1-3 giây để nhận diện tự động</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2.5">
                <div className="p-3 bg-emerald-50 text-emerald-600 rounded-full">
                  <Upload className="w-6 h-6 stroke-[2]" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-850">Kéo thả hóa đơn vào đây hoặc click để tải lên</h4>
                  <p className="text-xs text-slate-400 mt-1">Hỗ trợ định dạng ảnh JPG, PNG, WEBP tối đa 15MB</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Rapid preset loaders card */}
        <div className="p-4 bg-white border border-slate-100 rounded-xl flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Chạy Thử Nghiệm Nhanh</span>
            <h3 className="text-sm font-bold text-slate-800 mt-1.5">Ảnh hóa đơn mẫu có sẵn</h3>
            <p className="text-xs text-slate-400 mt-1 leading-normal">Bất kỳ người dùng nào cũng có thể nhấn để kiểm chứng bóc tách hóa đơn ảo:</p>
            
            <div className="space-y-2 mt-4">
              <button
                disabled={isProcessing}
                onClick={() => loadPresetReceipt("coopmart_sieuthi_hoadon.png")}
                className="w-full text-left py-2 px-3 hover:bg-slate-50 border border-slate-100/80 rounded-lg text-xs font-semibold text-slate-650 flex items-center justify-between cursor-pointer"
              >
                <span>Siêu thị Co.opmart Nguyễn Đình Chiểu</span>
                <span className="text-[9px] font-mono text-slate-400 font-bold">~852,000đ</span>
              </button>
              <button
                disabled={isProcessing}
                onClick={() => loadPresetReceipt("starbucks_coffee_bill.png")}
                className="w-full text-left py-2 px-3 hover:bg-slate-50 border border-slate-100/80 rounded-lg text-xs font-semibold text-slate-650 flex items-center justify-between cursor-pointer"
              >
                <span>Cửa hàng Starbucks Landmark 81</span>
                <span className="text-[9px] font-mono text-slate-400 font-bold">~185,000đ</span>
              </button>
              <button
                disabled={isProcessing}
                onClick={() => loadPresetReceipt("grab_taxi_invoice.png")}
                className="w-full text-left py-2 px-3 hover:bg-slate-50 border border-slate-100/80 rounded-lg text-xs font-semibold text-slate-650 flex items-center justify-between cursor-pointer"
              >
                <span>GrabCar Công nghệ di chuyển</span>
                <span className="text-[9px] font-mono text-slate-400 font-bold">~124,000đ</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {errMessage && (
        <div className="p-3 bg-amber-50 text-amber-800 border-l-4 border-amber-600 rounded text-xs flex items-center gap-2">
          <AlertTriangle className="w-4.5 h-4.5 shrink-0 text-amber-600" />
          <span>{errMessage}</span>
        </div>
      )}

      {/* Main split-screen panel */}
      {selectedUpload && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left panel: Receipt preview */}
          <div className="lg:col-span-5 p-5 bg-white border border-slate-100 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center pb-3.5 border-b border-slate-50">
                <h3 className="text-sm font-bold text-slate-800">Mô phỏng tệp Hóa đơn</h3>
                <span className="text-[10px] font-mono font-medium text-slate-400">{selectedUpload.fileName} ({selectedUpload.fileSize})</span>
              </div>

              {/* Simulated visual layout */}
              <div className="p-5 border border-slate-100 rounded-xl bg-[#fafafa]/80 my-4 font-mono select-none relative shadow-inner">
                {/* Visual bounding watermark tag */}
                <div className="absolute top-2 right-2 border-2 border-dashed border-emerald-500/80 text-emerald-600 text-[9px] px-1 bg-emerald-50 font-sans font-bold uppercase tracking-widest rounded animate-pulse">
                  AI OCR active
                </div>

                <div className="text-center pb-4 border-b border-dashed border-slate-200">
                  <h4 className="text-xs uppercase font-extrabold tracking-wider">{editingReceipt?.merchant || selectedUpload.recognizedData?.merchant || "QUÁN ĂN"}</h4>
                  <p className="text-[9px] text-slate-400 text-slate-400">Đơn vị thanh toán hóa đơn giá trị gia tăng</p>
                  <p className="text-[10px] text-slate-500 font-bold mt-1">Ngày mua: {editingReceipt?.date || selectedUpload.recognizedData?.date || "—"}</p>
                </div>

                {/* Items container */}
                <div className="py-4 space-y-2 border-b border-dashed border-slate-200 text-[11px] leading-relaxed">
                  {(editingReceipt?.items || selectedUpload.recognizedData?.items || []).map((it, idx) => (
                    <div key={idx} className="flex justify-between">
                      <div className="flex flex-col max-w-[200px]">
                        <span className="font-bold text-slate-700 uppercase tracking-tight">{it.name}</span>
                        <span className="text-[10px] text-slate-450 font-semibold italic">SL: {it.qty} x {it.price.toLocaleString()}đ</span>
                      </div>
                      <span className="font-bold text-slate-800 leading-none">{(it.qty * it.price).toLocaleString()}đ</span>
                    </div>
                  ))}
                </div>

                {/* Summaries layout */}
                <div className="pt-4 text-xs font-black flex justify-between uppercase">
                  <span>Tổng tiền thanh toán (VND):</span>
                  <span className="text-[#f43f5e] font-black text-sm">
                    {((editingReceipt?.items || []).reduce((acc, curr) => acc + (curr.price * curr.qty), 0) || selectedUpload.recognizedData?.total || 0).toLocaleString()}đ
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 p-2.5 bg-slate-50 text-[11px] text-slate-500 rounded border border-slate-100">
              <ZoomIn className="w-4.5 h-4.5 text-slate-400 shrink-0" />
              <span>Sử dụng chuột và bàn phím ở khung bên phải để sửa đổi các trường bóc tách sai trước khi lưu.</span>
            </div>
          </div>

          {/* Right panel: OCR structured correction fields */}
          <div className="lg:col-span-7 p-5 bg-white border border-slate-100 rounded-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3.5 border-b border-slate-50">
                <div className="flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-bold text-slate-800">Kết quả quét thông tin</h3>
                </div>
                <span className={`px-2 py-0.5 rounded font-bold text-[10px] leading-relaxed uppercase tracking-wider ${
                  selectedUpload.status === 'synced' 
                    ? 'bg-blue-50 text-blue-700' 
                    : 'bg-emerald-50 text-emerald-700 animate-pulse'
                }`}>
                  {selectedUpload.status === 'synced' ? 'Đã liên kết ví' : 'Sẵn sàng ghi sổ'}
                </span>
              </div>

              {editingReceipt ? (
                <div className="mt-4.5 space-y-4">
                  {/* Store Name & Date row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Đơn vị cung cấp</label>
                      <input
                        type="text"
                        value={editingReceipt.merchant}
                        onChange={(e) => setEditingReceipt({ ...editingReceipt, merchant: e.target.value })}
                        className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-150 rounded outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 font-bold"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Ngày hóa đơn</label>
                      <input
                        type="date"
                        value={editingReceipt.date}
                        onChange={(e) => setEditingReceipt({ ...editingReceipt, date: e.target.value })}
                        className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-150 rounded outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 font-mono font-bold"
                      />
                    </div>
                  </div>

                  {/* Category select & Total block */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Nhóm ngân sách</label>
                      <select
                        value={editingReceipt.category}
                        onChange={(e) => setEditingReceipt({ ...editingReceipt, category: e.target.value })}
                        className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-150 rounded outline-none focus:ring-2 focus:ring-emerald-500 text-slate-850 font-semibold"
                      >
                        {CHOOSE_CATEGORIES.map(cat => (
                          <option key={cat} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tổng hóa đơn thực tế</label>
                      <div className="px-3 py-1.5 text-xs bg-[#fff5f5] text-red-650 font-black font-mono border border-red-100 rounded">
                        {formatVal(editingReceipt.total)}
                      </div>
                    </div>
                  </div>

                  {/* Line items checklist table */}
                  <div className="space-y-2 mt-2">
                    <div className="flex justify-between items-center">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Kê khai danh mục chi tiết</label>
                      <button
                        type="button"
                        onClick={handleAddField}
                        className="inline-flex items-center gap-0.5 text-[10px] font-extrabold text-emerald-600 hover:text-emerald-700 cursor-pointer"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Thêm dòng mới</span>
                      </button>
                    </div>

                    <div className="max-h-56 overflow-y-auto space-y-2.5 border border-slate-50/60 p-2 rounded bg-slate-50/20">
                      {editingReceipt.items.map((it) => (
                        <div key={it.id} className="flex items-center gap-2" id={`ocr-edit-row-${it.id}`}>
                          {/* Name */}
                          <input
                            type="text"
                            value={it.name}
                            onChange={(e) => handleItemValueChange(it.id, 'name', e.target.value)}
                            placeholder="Mô tả sản phẩm"
                            className="flex-1 px-2.5 py-1 bg-white border border-slate-150 text-xs rounded text-slate-800"
                          />
                          {/* Quantity */}
                          <input
                            type="number"
                            min="1"
                            value={it.qty}
                            onChange={(e) => handleItemValueChange(it.id, 'qty', e.target.value)}
                            className="w-12 px-2 py-1 bg-white border border-slate-150 text-xs rounded text-slate-800 font-mono text-center"
                          />
                          {/* Price */}
                          <input
                            type="number"
                            min="1"
                            value={it.price}
                            onChange={(e) => handleItemValueChange(it.id, 'price', e.target.value)}
                            className="w-24 px-2 py-1 bg-white border border-slate-150 text-xs rounded text-slate-800 font-mono text-right"
                          />
                          {/* Delete Action */}
                          <button
                            type="button"
                            onClick={() => handleRemoveField(it.id)}
                            className="p-1 hover:text-red-500 rounded bg-transparent transition-all cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4 text-slate-400 hover:text-red-500" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-slate-400 text-xs text-center">
                  <p>Hóa đơn mẫu này đã được liên kết đồng bộ thành công vào ví tài chính giao dịch của bạn.</p>
                  <p className="mt-1">Chọn hóa đơn khác hoặc tải thêm ảnh mới để thực hiện trích xuất dữ liệu.</p>
                </div>
              )}
            </div>

            {/* Editing actions buttons */}
            {editingReceipt && (
              <div className="flex items-center justify-end gap-3.5 border-t border-slate-100 pt-4 mt-6">
                <span className="text-[11px] font-medium text-slate-400 mr-auto">Cơ chế: {settings.ocrEngine === "gemini" ? "Real AI (Gemini)" : "Simulator"}</span>
                <button
                  type="button"
                  onClick={handleSyncClick}
                  className="inline-flex items-center gap-1.5 px-4.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded shadow-sm tracking-wide cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>Xác nhận & Đồng bộ vào Sổ ví</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Uploaded History List Table */}
      <div className="p-5 bg-white border border-slate-100 rounded-xl">
        <h3 className="text-sm font-bold text-slate-800 pb-3 border-b border-slate-50">Nhật ký danh sách hóa đơn tải lên</h3>
        <div className="overflow-x-auto mt-2.5">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-50/60">
                <th className="py-2.5 px-3">Tên hóa đơn</th>
                <th className="py-2.5 px-3">Thời điểm tải</th>
                <th className="py-2.5 px-3">Hạn mức tiền bóc tách</th>
                <th className="py-2.5 px-3">Danh mục băm</th>
                <th className="py-2.5 px-3 text-center">Trạng thái đồng bộ</th>
                <th className="py-2.5 px-3 text-center">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 text-slate-700">
              {uploads.map((up) => (
                <tr 
                  key={up.id} 
                  className={`hover:bg-slate-50/20 transition-colors cursor-pointer ${selectedUploadId === up.id ? 'bg-slate-50/70 border-l-4 border-emerald-500' : ''}`}
                  onClick={() => handleSelectUpload(up.id)}
                >
                  <td className="py-3 px-3 font-semibold text-slate-850">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4.5 h-4.5 text-slate-400 shrink-0" />
                      <span>{up.fileName}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-400 font-semibold">{up.uploadDate}</td>
                  <td className="py-3 px-3 font-bold font-mono text-slate-800">
                    {up.recognizedData ? formatVal(up.recognizedData.total) : "—"}
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded font-semibold text-[9px]">
                      {up.recognizedData?.category || "Chưa tách"}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[9px] font-bold rounded-full ${
                      up.status === 'synced' 
                        ? 'bg-blue-50 text-blue-800 border border-blue-100' 
                        : 'bg-emerald-55 bg-emerald-50 text-emerald-800 border border-emerald-100'
                    }`}>
                      {up.status === 'synced' ? 'Đã duyệt ghi sổ' : 'Bán thảo (Chưa đồng bộ)'}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleSelectUpload(up.id)}
                      className="text-[10px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-0.5 mx-auto hover:underline cursor-pointer"
                    >
                      <span>Xem chi tiết</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
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


// MOCK FALLBACK DATA GENERATOR
function getLocalFallbackData(name: string): RecognizedReceipt {
  const lower = name.toLowerCase();
  if (lower.includes("starbucks") || lower.includes("cafe")) {
    return {
      merchant: "Starbucks Coffee Vietnam",
      date: new Date().toISOString().split("T")[0],
      total: 185000,
      category: "Ăn uống",
      items: [
        { id: "gen_1", name: "Caramel Macchiato Grand", qty: 1, price: 95000 },
        { id: "gen_2", name: "Croissant hạnh nhân", qty: 2, price: 45000 }
      ]
    };
  }
  if (lower.includes("coopmart") || lower.includes("sieuthi") || lower.includes("grocery")) {
    return {
      merchant: "Siêu thị Co.opmart Nguyễn Đình Chiểu",
      date: new Date().toISOString().split("T")[0],
      total: 852000,
      category: "Mua sắm",
      items: [
        { id: "gen_3", name: "Sữa tươi sạch TH True Milk 1L", qty: 4, price: 36000 },
        { id: "gen_4", name: "Gạo lài thơm túi 5kg", qty: 1, price: 145000 },
        { id: "gen_5", name: "Thịt ba rọi heo CP 1kg", qty: 1, price: 185050 },
        { id: "gen_6", name: "Rau cải xanh & nấm rơm", qty: 1, price: 46000 },
        { id: "gen_7", name: "Bóng đèn Compact Rạng Đông 15W", qty: 2, price: 165000 }
      ]
    };
  }
  if (lower.includes("grab") || lower.includes("taxi")) {
    return {
      merchant: "Công ty Cổ phần GrabCar Việt Nam",
      date: new Date().toISOString().split("T")[0],
      total: 124000,
      category: "Di chuyển",
      items: [
        { id: "gen_8", name: "Chuyến đi GrabCar từ Quận 1 đến Quận 7", qty: 1, price: 124000 }
      ]
    };
  }
  return {
    merchant: "Cửa Hàng Tiện Lợi Circle K",
    date: new Date().toISOString().split("T")[0],
    total: 82000,
    category: "Ăn uống",
    items: [
      { id: "gen_9", name: "Mì trộn trứng ốp la Circle K", qty: 2, price: 25000 },
      { id: "gen_10", name: "Nước tăng lực Redbull lon", qty: 1, price: 18000 },
      { id: "gen_11", name: "Kẹo cao su Doublemint", qty: 1, price: 14000 }
    ]
  };
}
