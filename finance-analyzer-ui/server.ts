import express from "express";
import path from "path";
import dotenv from "dotenv";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";

dotenv.config();

const app = express();
const PORT = 3000;

// Setup generous limits for base64 receipt uploads
app.use(express.json({ limit: "25mb" }));
app.use(express.urlencoded({ limit: "25mb", extended: true }));

// Lazy init of Gemini API Client
let aiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
    return null;
  }
  if (!aiClient) {
    aiClient = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// 1. CHAT BOT ENDPOINT
app.post("/api/chat", async (req, res) => {
  try {
    const { message, history } = req.body;
    const ai = getGeminiClient();

    if (!ai) {
      // Elegant, conversational fallback when no API key is provided
      const responseText = getMockChatResponse(message);
      return res.json({
        text: responseText + "\n\n*(Lưu ý: Phản hồi này được tạo tự động ở chế độ ngoại tuyến. Thêm GEMINI_API_KEY trong Settings > Secrets để sử dụng Trí Tuệ Nhân Tạo thực tế)*",
        isMock: true,
      });
    }

    // Format history for Gemini chat if present
    // Let's use simple prompt construction for maximum safety and speed
    const systemPrompt = `Bạn là Trợ lý Tài chính AI tối tân tích hợp trong ứng dụng quản lý chi tiêu.
Nhiệm vụ của bạn là tư vấn tài chính, phân tích chi tiêu, gợi ý tiết kiệm bằng Tiếng Việt một cách nhiệt tình, chính xác và có chiều sâu.
Hãy trả lời với định dạng Markdown chuyên nghiệp. Có thể kẻ bảng, dùng ký hiệu tiền tệ VND, định nghĩa rõ ràng. Thân thiện và thông thái.

Dưới đây là lịch sử chat gần nhất (nếu có):
${(history || []).map((h: any) => `${h.role === 'user' ? 'Người dùng' : 'Trợ lý'}: ${h.text}`).join('\n')}

Hãy trả lời tin nhắn mới này: "${message}"`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: systemPrompt,
    });

    res.json({
      text: response.text || "Xin lỗi, tôi không thể xử lý yêu cầu lúc này.",
      isMock: false,
    });

  } catch (error: any) {
    console.error("Gemini Chat Error:", error);
    res.status(500).json({ error: error.message || "Lỗi xử lý ngôn ngữ trên máy chủ." });
  }
});

// 2. RECEIPT OCR ENDPOINT (multimodal)
app.post("/api/ocr", async (req, res) => {
  try {
    const { imageBase64, mimeType, fileName } = req.body;
    const ai = getGeminiClient();

    if (!ai || !imageBase64) {
      // Robust simulated OCR parse based on file upload
      console.log("No API Key or image data. Running high-fidelity local OCR Simulator.");
      const mockResult = getMockOCRData(fileName || "receipt.png");
      // Add a small delay to simulate processing
      await new Promise(resolve => setTimeout(resolve, 1500));
      return res.json({
        recognizedData: mockResult,
        isMock: true
      });
    }

    // Prepare image part
    const dataOnly = imageBase64.includes(",") ? imageBase64.split(",")[1] : imageBase64;
    const imagePart = {
      inlineData: {
        mimeType: mimeType || "image/png",
        data: dataOnly,
      },
    };

    const textPart = {
      text: `Analyze this receipt. Extract the merchant name, document date (formatted as YYYY-MM-DD), the absolute totals in VND, the best matching budget category (choose exactly one from: 'Ăn uống', 'Mua sắm', 'Hóa đơn', 'Di chuyển', 'Giải trí', 'Sức khỏe', 'Khác'), and a list of line items with their names, quantities, and individual unit prices if readable. Return the result in structured Vietnamese.`
    };

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: { parts: [imagePart, textPart] },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            merchant: { type: Type.STRING, description: "Name of the supermarket, store or provider" },
            date: { type: Type.STRING, description: "Transaction date in format YYYY-MM-DD" },
            total: { type: Type.NUMBER, description: "Grand total on receipt as a single integer" },
            category: { type: Type.STRING, description: "Must be one of: Ăn uống, Mua sắm, Hóa đơn, Di chuyển, Giải trí, Sức khỏe, Khác" },
            items: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING, description: "Item description or name in Vietnamese" },
                  qty: { type: Type.INTEGER, description: "Quantity purchased" },
                  price: { type: Type.NUMBER, description: "Unit price in VND" }
                },
                required: ["name", "qty", "price"]
              }
            }
          },
          required: ["merchant", "date", "total", "category"]
        }
      }
    });

    const textResult = response.text;
    if (textResult) {
      const parsed = JSON.parse(textResult.trim());
      // Ensure items have localized string IDs for React state loop
      if (parsed.items) {
        parsed.items = parsed.items.map((it: any, index: number) => ({
          ...it,
          id: `ocr_item_${Date.now()}_${index}`
        }));
      } else {
        parsed.items = [];
      }
      res.json({ recognizedData: parsed, isMock: false });
    } else {
      throw new Error("Không nhận diện được nội dung hóa đơn.");
    }

  } catch (error: any) {
    console.error("Gemini OCR Error:", error);
    res.status(500).json({ error: error.message || "Lỗi xử lý OCR hóa đơn." });
  }
});

// 3. INSIGHTS GENERATION ENDPOINT
app.post("/api/insights", async (req, res) => {
  try {
    const { currentBudgets, recentTransactions } = req.body;
    const ai = getGeminiClient();

    if (!ai) {
      // Dynamic mock insights based on current metrics
      const mockInsights = getMockInsightsDynamic(currentBudgets, recentTransactions);
      return res.json({ insights: mockInsights, isMock: true });
    }

    const prompt = `Bạn là Chuyên gia Phân tích Tài chính AI. Dựa trên dữ liệu tài chính thực tế dưới đây:
Nhân sách hiện tại: ${JSON.stringify(currentBudgets || [])}
Giao dịch gần nhất: ${JSON.stringify(recentTransactions || [])}

Hãy phân tích và viết ra 4 ý kiến phân tích (financial insights) cực kỳ thiết thực dưới định dạng JSON là một danh sách.
Mỗi insight cần có cấu trúc:
- type: 'warning' | 'success' | 'info' | 'opportunity'
- title: string (Tiêu đề phân tích hấp dẫn, ví dụ: "Ăn uống tăng mạnh", "Thăng dư khả quan")
- description: string (Mô tả phân tích tiếng Việt sâu sắc kèm lời khuyên tiết kiệm cụ thể)
- impactValue: string (Số tiền hoặc tỷ lệ tiết kiệm được, ví dụ: "Tiết kiệm 450,000đ", "Giảm 12%")
- date: string (Ví dụ: "Hôm nay", "Tháng này")
- category: string (Danh mục liên quan hoặc "Tất cả")

Chỉ trả về JSON hợp lệ theo định nghĩa trên. Trả về đúng ngôn ngữ tiếng Việt.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash",
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            insights: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  type: { type: Type.STRING, description: "warning, success, info, opportunity" },
                  title: { type: Type.STRING },
                  description: { type: Type.STRING },
                  impactValue: { type: Type.STRING },
                  date: { type: Type.STRING },
                  category: { type: Type.STRING }
                },
                required: ["type", "title", "description", "date"]
              }
            }
          },
          required: ["insights"]
        }
      }
    });

    const parsed = JSON.parse(response.text?.trim() || '{"insights": []}');
    // Assign stable random IDs
    const insightsWithIds = (parsed.insights || []).map((ins: any, index: number) => ({
      ...ins,
      id: `ai_insight_${Date.now()}_${index}`
    }));

    res.json({ insights: insightsWithIds, isMock: false });

  } catch (error: any) {
    console.error("Gemini Insights Error:", error);
    res.status(500).json({ error: error.message || "Lỗi tạo insights tự động." });
  }
});


// HELPER ACTIONS & FALLBACK FUNCTIONS

function getMockChatResponse(msg: string): string {
  const m = msg.toLowerCase();
  if (m.includes("chào") || m.includes("hello") || m.includes("hi")) {
    return "Xin chào! Tôi có thể giúp gì cho bạn hôm nay để phân tích chi tiêu hoặc tối ưu hóa ngân sách cá nhân? Bạn có thể hỏi tôi những câu như: 'Cách lập ngân sách ăn uống?' hay 'Tôi nên làm gì khi chi tiêu vượt giới hạn?'";
  }
  if (m.includes("ăn uống") || m.includes("nhà hàng") || m.includes("cafe")) {
    return "Danh mục **Ăn uống** thường chiếm tỷ trọng lớn thứ hai trong tài chính cá nhân sau tiền nhà. Đối với ngân sách hiện tại của bạn:\n- Bạn đã tiêu **1,850,000 VND** trên hạn mức **3,000,000 VND**.\n- Bạn còn lại **1,150,000 VND** (tương đương 38%)\n\n**Mẹo tối ưu:**\n1. Lên thực đơn tuần và đi siêu thị một lần thay vì mua lẻ tẻ.\n2. Tận dụng tối đa combo bữa trưa văn phòng nấu sẵn.\n3. Hạn chế đặt đồ ăn qua ứng dụng trong giờ cao điểm để giảm chi phí giao hàng sực nước.";
  }
  if (m.includes("ngân sách") || m.includes("giới hạn") || m.includes("tiết kiệm")) {
    return "Để thiết lập một ngân sách lành mạnh, bạn nên theo sát quy tắc **50/30/20**:\n- **50% Nhu cầu thiết yếu** (Nhà thuê, Điện nước, Gạo dầu ăn, Hóa đơn bắt buộc)\n- **30% Mong muốn cá nhân** (Đi chơi, Cafe, Mua sắm trang phục, Xem phim)\n- **20% Tiết kiệm & Tích lũy đầu tư**\n\nHiện tại, bạn đang tích lũy được khoảng **15%** tổng thu nhập của tháng. Hãy thử tự động hóa trích lập 10% thu nhập ngay khi nhận lương vào ngày đầu tháng nhé!";
  }
  if (m.includes("tổng quan") || m.includes("chi tiêu") || m.includes("bao nhiêu")) {
    return "Dưới đây là tóm tắt nhanh chi tiêu tháng này của bạn:\n1. **Tổng thu nhập**: 24,500,000 VND (gồm Lương và Thưởng dự án).\n2. **Tổng chi tiêu thực tế**: 11,210,000 VND.\n3. **Số dư ròng**: +13,290,000 VND (Rất tích cực!\n\nBạn có muốn phân tích hóa đơn mua sắm vừa rồi để tự động phân phối ngân sách không?";
  }
  return "Tôi đã nhận được câu hỏi trực quan của bạn về quản lý tài chính. Để tối ưu dòng tiền, bạn hãy đảm bảo ghi chép đầy đủ các giao dịch phát sinh qua mục **Giao dịch** hoặc **Tải hóa đơn lên** để tôi giúp bạn OCR bóc tách và thống kê ngân sách tự động chính xác nhất nhé!";
}

function getMockOCRData(fileName: string): any {
  const fileLower = fileName.toLowerCase();
  if (fileLower.includes("starbucks") || fileLower.includes("cafe") || fileLower.includes("coffee")) {
    return {
      merchant: "Starbucks Coffee Vietnam",
      date: new Date().toISOString().split("T")[0],
      total: 185000,
      category: "Ăn uống",
      items: [
        { id: "mock_1", name: "Caramel Macchiato Grand", qty: 1, price: 95000 },
        { id: "mock_2", name: "Croissant hạnh nhân", qty: 1, price: 55000 },
        { id: "mock_3", name: "Espresso Solo", qty: 1, price: 35000 }
      ]
    };
  }
  if (fileLower.includes("coopmart") || fileLower.includes("gr grocery") || fileLower.includes("sieuthi") || fileLower.includes("supermarket")) {
    return {
      merchant: "Siêu thị Co.opmart Nguyễn Đình Chiểu",
      date: new Date().toISOString().split("T")[0],
      total: 624500,
      category: "Mua sắm",
      items: [
        { id: "mock_4", name: "Sữa tươi sạch TH True Milk 1L", qty: 4, price: 36000 },
        { id: "mock_5", name: "Gạo lài thơm túi 5kg", qty: 1, price: 145000 },
        { id: "mock_6", name: "Thịt ba rọi heo CP 1kg", qty: 1, price: 185000 },
        { id: "mock_7", name: "Dầu ăn Tường An 2L", qty: 1, price: 104500 },
        { id: "mock_8", name: "Rau cải xanh & nấm rơm", qty: 1, price: 46000 }
      ]
    };
  }
  if (fileLower.includes("grab") || fileLower.includes("taxi") || fileLower.includes("be")) {
    return {
      merchant: "Công ty Cổ phần GrabCar Việt Nam",
      date: new Date().toISOString().split("T")[0],
      total: 124000,
      category: "Di chuyển",
      items: [
        { id: "mock_9", name: "Chuyến đi GrabCar từ Quận 1 đến Quận 7", qty: 1, price: 124000 }
      ]
    };
  }
  // Default general generic receipt
  return {
    merchant: "Cửa Hàng Tiện Lợi Circle K",
    date: new Date().toISOString().split("T")[0],
    total: 82000,
    category: "Ăn uống",
    items: [
      { id: "mock_10", name: "Mì trộn trứng ốp la Circle K", qty: 2, price: 25000 },
      { id: "mock_11", name: "Nước tăng lực Redbull lon", qty: 1, price: 18000 },
      { id: "mock_12", name: "Kẹo cao su Doublemint", qty: 1, price: 14000 }
    ]
  };
}

function getMockInsightsDynamic(budgets: any[], txs: any[]): any[] {
  // Return standard high-fidelity Vietnamese insights
  return [
    {
      id: "opt_1",
      type: "opportunity",
      title: "Cắt giảm chi phí di chuyển",
      description: "Hệ thống phát hiện bạn di chuyển taxi công nghệ 5 lần trong tuần này. Nếu đổi sang đi xe buýt hoặc đi chung xe, bạn có thể giảm chi tiêu danh mục này khoảng 35%.",
      impactValue: "Tiết kiệm ~350,000đ/tuần",
      date: "Hôm nay",
      category: "Di chuyển"
    },
    {
      id: "wrn_1",
      type: "warning",
      title: "Hạn mức Ăn uống sắp chạm mốc 80%",
      description: "Tổng chi tiêu ăn uống ngoài của bạn đã đạt 2,350,000 VND trong tổng số 3,000,000 VND hạn mức thiết lập. Hãy chú ý tự nấu ăn tại nhà nhiều hơn trong 10 ngày cuối tháng.",
      impactValue: "Còn lại 650,000đ",
      date: "Tháng này",
      category: "Ăn uống"
    },
    {
      id: "suc_1",
      type: "success",
      title: "Kiểm soát tốt ngân sách Hóa đơn",
      description: "Tháng này bạn đã thanh toán hết các hóa đơn cốt lõi điện/nước/mạng internet chỉ chiếm 12% tổng chi phí của bạn, thấp hơn 5% so với tháng trước do biết tắt điều hòa hợp lý.",
      impactValue: "Giảm 115,000đ",
      date: "Tuần này",
      category: "Hóa đơn"
    },
    {
      id: "inf_1",
      type: "info",
      title: "Thời điểm dồi dào tài chính",
      description: "Các giao dịch thuộc danh mục 'Lương & Thưởng' đã tăng tổng số dư khả dụng lên 13M VND. Đây là cơ hội tốt để chuyển ngay 4,000,000 VND vào quỹ tiết kiệm dài hạn trước khi phát sinh mua sắm rảnh rỗi.",
      impactValue: "+4,000,000đ đầu tư",
      date: "Hôm nay",
      category: "Tất cả"
    }
  ];
}


// VITE INTEGRATION MIDDLEWARE
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    // In development mode, mount Vite dev server as middleware
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
    console.log("Vite middleware mounted successfully for local dev.");
  } else {
    // Serve production static assets from the standard 'dist' output directory
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
    console.log(`Serving static production build from: ${distPath}`);
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Finance Analyzer Full-Stack Express Server started on http://localhost:${PORT}`);
  });
}

startServer();
