import Link from "next/link";

export function Footer() {
  return (
    <footer className="bg-canvas border-t border-hairline mt-auto">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-utility-xs text-body mb-3">Sản phẩm</h3>
            <ul className="space-y-2 text-body-xs">
              <li><Link href="/dashboard" className="text-body hover:text-ink">Dashboard</Link></li>
              <li><Link href="/transactions" className="text-body hover:text-ink">Giao dịch</Link></li>
              <li><Link href="/budgets" className="text-body hover:text-ink">Ngân sách</Link></li>
              <li><Link href="/chat" className="text-body hover:text-ink">Trợ lý AI</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="text-utility-xs text-body mb-3">Tài nguyên</h3>
            <ul className="space-y-2 text-body-xs">
              <li><Link href="/health" className="text-body hover:text-ink">System Status</Link></li>
              <li><a href="#" className="text-body hover:text-ink">Hướng dẫn</a></li>
              <li><a href="#" className="text-body hover:text-ink">FAQ</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-utility-xs text-body mb-3">Công ty</h3>
            <ul className="space-y-2 text-body-xs">
              <li><a href="#" className="text-body hover:text-ink">Về chúng tôi</a></li>
              <li><a href="#" className="text-body hover:text-ink">Liên hệ</a></li>
              <li><a href="#" className="text-body hover:text-ink">Bảo mật</a></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-4 border-t border-hairline-soft flex items-center justify-between">
          <div className="flex items-center gap-2 text-caption-xs text-mute">
            <span aria-hidden>💰</span>
            <span>© 2026 Personal Finance Analyzer</span>
          </div>
          <span className="text-caption-xs text-mute">Made with Next.js + FastAPI</span>
        </div>
      </div>
    </footer>
  );
}
