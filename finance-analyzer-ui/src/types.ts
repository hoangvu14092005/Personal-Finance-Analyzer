export interface Transaction {
  id: string;
  date: string;
  description: string;
  category: string;
  amount: number;
  type: 'income' | 'expense';
  status: 'completed' | 'pending' | 'failed';
  note?: string;
}

export interface Budget {
  id: string;
  category: string;
  limit: number;
  spent: number;
  color: string;
}

export interface ReceiptItem {
  id: string;
  name: string;
  qty: number;
  price: number;
}

export interface RecognizedReceipt {
  merchant: string;
  date: string;
  total: number;
  category: string;
  items: ReceiptItem[];
}

export interface ReceiptUpload {
  id: string;
  fileName: string;
  fileSize: string;
  uploadDate: string;
  imageUrl?: string;
  status: 'processing' | 'success' | 'failed' | 'synced';
  recognizedData?: RecognizedReceipt;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  chartData?: { name: string; value: number }[];
  tableData?: any[];
}

export interface FinancialInsight {
  id: string;
  type: 'warning' | 'success' | 'info' | 'opportunity';
  title: string;
  description: string;
  impactValue?: string;
  date: string;
  category?: string;
}

export interface AppSettings {
  userName: string;
  currency: 'VND' | 'USD';
  budgetAlertThreshold: number; // e.g. 80%
  ocrEngine: 'gemini' | 'mock-high-speed';
  notificationEmail: boolean;
  theme: 'white';  // Mandated white background theme
}
