import { Transaction, Budget, ReceiptUpload, FinancialInsight, AppSettings } from "../types";

export const INITIAL_TRANSACTIONS: Transaction[] = [
  {
    id: "tx-1",
    date: "2026-05-28",
    description: "Nhận Lương tháng 5 (Công ty TechCorp)",
    category: "Lương",
    amount: 18500000,
    type: "income",
    status: "completed",
    note: "Lương cơ bản + thưởng chuyên cần"
  },
  {
    id: "tx-2",
    date: "2026-05-27",
    description: "Đi chợ Coopmart phục vụ cả tuần",
    category: "Mua sắm",
    amount: 852000,
    type: "expense",
    status: "completed",
    note: "Mua thịt cá dưa cà trái cây tươi"
  },
  {
    id: "tx-3",
    date: "2026-05-26",
    description: "Hóa đơn Điện lực lực TP.HCM",
    category: "Hóa đơn",
    amount: 1240000,
    type: "expense",
    status: "completed",
    note: "Thanh toán qua ví điện tử"
  },
  {
    id: "tx-4",
    date: "2026-05-26",
    description: "Ăn tối lẩu Hadilao cùng gia đình",
    category: "Ăn uống",
    amount: 1450000,
    type: "expense",
    status: "completed",
    note: "Gia đình sum họp sinh nhật em gái"
  },
  {
    id: "tx-5",
    date: "2026-05-25",
    description: "Cà phê Starbucks Landmark 81",
    category: "Ăn uống",
    amount: 185000,
    type: "expense",
    status: "completed",
    note: "Tiếp khách hàng đối tác"
  },
  {
    id: "tx-6",
    date: "2026-05-24",
    description: "Chuyến GrabCar khứ hồi Phú Mỹ Hưng",
    category: "Di chuyển",
    amount: 280000,
    type: "expense",
    status: "completed",
    note: "Đi tham gia hội chợ công nghệ"
  },
  {
    id: "tx-7",
    date: "2026-05-23",
    description: "Mua thuốc bổ sung vitamin Pharmacity",
    category: "Sức khỏe",
    amount: 320000,
    type: "expense",
    status: "completed",
    note: "Vitamin C và sủi bổ sung lực"
  },
  {
    id: "tx-8",
    date: "2026-05-22",
    description: "Thu nhập hoa hồng môi giới",
    category: "Khác",
    amount: 6000000,
    type: "income",
    status: "completed",
    note: "Nhận tiền mặt từ dự án giới thiệu khách"
  },
  {
    id: "tx-9",
    date: "2026-05-20",
    description: "Xem phim rạp CGV Cinema",
    category: "Giải trí",
    amount: 240000,
    type: "expense",
    status: "completed",
    note: "Vé xem phim bom tấn + bỏng ngô ngọt"
  },
  {
    id: "tx-10",
    date: "2026-05-18",
    description: "Cơm trưa văn phòng GrabFood",
    category: "Ăn uống",
    amount: 65000,
    type: "expense",
    status: "completed",
    note: "Cơm sườn bì chả"
  },
  {
    id: "tx-11",
    date: "2026-05-15",
    description: "Mua ốp lưng điện thoại Shopee",
    category: "Mua sắm",
    amount: 120000,
    type: "expense",
    status: "completed"
  },
  {
    id: "tx-12",
    date: "2026-05-14",
    description: "Thanh toán xăng xe máy",
    category: "Di chuyển",
    amount: 80000,
    type: "expense",
    status: "completed"
  },
  {
    id: "tx-13",
    date: "2026-05-10",
    description: "Đóng phí internet VNPT cáp quang",
    category: "Hóa đơn",
    amount: 220000,
    type: "expense",
    status: "completed"
  }
];

export const INITIAL_BUDGETS: Budget[] = [
  { id: "bg-1", category: "Ăn uống", limit: 4500000, spent: 1700000, color: "#f59e0b" }, // Warm Amber
  { id: "bg-2", category: "Mua sắm", limit: 3000000, spent: 972000, color: "#3b82f6" },  // Vibrant Blue
  { id: "bg-3", category: "Hóa đơn", limit: 2000000, spent: 1460000, color: "#ef4444" },  // Red Warning
  { id: "bg-4", category: "Di chuyển", limit: 1200000, spent: 360000, color: "#10b981" }, // Emerald Green
  { id: "bg-5", category: "Giải trí", limit: 1500000, spent: 240000, color: "#8b5cf6" }, // Purple
  { id: "bg-6", category: "Sức khỏe", limit: 1000000, spent: 320000, color: "#ec4899" }  // Pink
];

export const INITIAL_UPLOADS: ReceiptUpload[] = [
  {
    id: "up-101",
    fileName: "starbucks_may25.png",
    fileSize: "1.2 MB",
    uploadDate: "2026-05-25",
    status: "synced",
    recognizedData: {
      merchant: "Starbucks Coffee Vietnam",
      date: "2026-05-25",
      total: 185000,
      category: "Ăn uống",
      items: [
        { id: "up-item-1", name: "Caramel Macchiato Grand", qty: 1, price: 95000 },
        { id: "up-item-2", name: "Croissant hạnh nhân", qty: 1, price: 55000 },
        { id: "up-item-3", name: "Espresso Solo", qty: 1, price: 35000 }
      ]
    }
  },
  {
    id: "up-102",
    fileName: "receipt_coopmart.jpg",
    fileSize: "2.4 MB",
    uploadDate: "2026-05-27",
    status: "success",
    recognizedData: {
      merchant: "Siêu thị Co.opmart Nguyễn Đình Chiểu",
      date: "2026-05-27",
      total: 852000,
      category: "Mua sắm",
      items: [
        { id: "up-item-4", name: "Sữa tươi sạch TH True Milk 1L", qty: 4, price: 36000 },
        { id: "up-item-5", name: "Gạo lài thơm túi 5kg", qty: 1, price: 145000 },
        { id: "up-item-6", name: "Thịt ba rọi heo CP 1kg", qty: 1, price: 185000 },
        { id: "up-item-7", name: "Rau cải xanh & nấm rơm", qty: 1, price: 46000 },
        { id: "up-item-8", name: "Bóng đèn Compact Rạng Đông 15W", qty: 2, price: 40000 }
      ]
    }
  }
];

export const INITIAL_INSIGHTS: FinancialInsight[] = [
  {
    id: "ins-1",
    type: "warning",
    title: "Ngân sách 'Ăn uống' chạm mốc 58%",
    description: "Bạn đã chi 2,615,000 VND trong hạn mức 4,500,000 VND đề gia hạn danh mục Ăn uống. Tần suất ăn lẩu và cà phê đối ngoại của bạn trong 2 tuần qua tăng 18%.",
    impactValue: "Còn lại 1,885,000đ",
    date: "Hôm nay",
    category: "Ăn uống"
  },
  {
    id: "ins-2",
    type: "opportunity",
    title: "Tiết kiệm phí thanh toán Hóa đơn",
    description: "Sử dụng tính năng chiết khấu 2% khi liên kết thẻ tín dụng TechBank thanh toán tiền điện tháng này để tiết kiệm tiền.",
    impactValue: "Giảm trực tiếp ~25,000đ",
    date: "Tháng này",
    category: "Hóa đơn"
  },
  {
    id: "ins-3",
    type: "success",
    title: "Thặng dư tài chính đạt trạng thái xuất sắc",
    description: "Số dư ròng trong ví của bạn hiện tại dương 13,290,000 VND. Tỷ lệ tiết kiệm thực tế đạt 54% tổng thu nhập nhờ kiểm soát tốt mua sắm thời trang xả láng.",
    impactValue: "Tích lũy 54% thu nhập",
    date: "Tuần này",
    category: "Tất cả"
  }
];

export const INITIAL_SETTINGS: AppSettings = {
  userName: "Nguyễn Minh Quân",
  currency: "VND",
  budgetAlertThreshold: 80,
  ocrEngine: "gemini",
  notificationEmail: true,
  theme: "white"
};

export const CHOOSE_CATEGORIES = [
  "Ăn uống",
  "Mua sắm",
  "Hóa đơn",
  "Di chuyển",
  "Giải trí",
  "Sức khỏe",
  "Lương",
  "Khác"
];
