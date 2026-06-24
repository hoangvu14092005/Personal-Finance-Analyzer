// Bảng màu chart cho 15 danh mục chuẩn (khớp màu seed trong DB).
// Dùng nhất quán giữa donut, bar, legend, badge. Ưu tiên `color` từ API; nếu
// thiếu thì map theo tên; cuối cùng fallback theo index.

export const CATEGORY_COLORS: Record<string, string> = {
  "Ăn uống": "#f59e0b",
  "Cà phê & đồ uống": "#d97706",
  "Thực phẩm & siêu thị": "#22c55e",
  "Mua sắm": "#3b82f6",
  "Di chuyển": "#10b981",
  "Du lịch": "#14b8a6",
  "Giáo dục": "#0ea5e9",
  "Giải trí": "#8b5cf6",
  "Sức khỏe & y tế": "#ec4899",
  "Hóa đơn & tiện ích": "#ef4444",
  "Nhà ở": "#6366f1",
  "Làm đẹp & chăm sóc cá nhân": "#f472b6",
  "Chuyển khoản & rút tiền": "#64748b",
  "Quà tặng & quyên góp": "#a855f7",
  Khác: "#a3a3a3",
};

// Palette dự phòng cho merchant/sản phẩm (không có màu cố định).
export const FALLBACK_PALETTE = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#ef4444",
  "#0ea5e9",
  "#6366f1",
  "#64748b",
];

/** Màu cho 1 danh mục: ưu tiên color từ API, rồi map theo tên, rồi fallback. */
export function categoryColor(
  name: string,
  apiColor?: string | null,
  index = 0,
): string {
  if (apiColor) return apiColor;
  return CATEGORY_COLORS[name] ?? FALLBACK_PALETTE[index % FALLBACK_PALETTE.length];
}

/** Format số tiền VND ngắn gọn (không số lẻ). */
export function formatVnd(value: number): string {
  if (!Number.isFinite(value)) return "0 VND";
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} VND`;
}

/** Format gọn cho trục biểu đồ: 1.2tr, 350k. */
export function formatVndShort(value: number): string {
  if (!Number.isFinite(value)) return "0";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}tr`;
  if (abs >= 1_000) return `${Math.round(value / 1_000)}k`;
  return String(Math.round(value));
}
