"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bot,
  CreditCard,
  LayoutDashboard,
  PieChart,
  ReceiptText,
  Settings,
  Sparkles,
  Target,
  UploadCloud,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";

const NAV_GROUPS = [
  {
    label: "Quản lý",
    items: [
      { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
      { href: "/analytics", label: "Phân tích chi tiêu", icon: PieChart },
      { href: "/transactions", label: "Danh sách giao dịch", icon: ReceiptText },
    ],
  },
  {
    label: "Chứng từ",
    items: [
      { href: "/receipts/upload", label: "Tải hóa đơn lên (OCR)", icon: UploadCloud },
      { href: "/receipts", label: "Danh sách hóa đơn", icon: ReceiptText },
      { href: "/budgets", label: "Quản lý ngân sách", icon: Target },
    ],
  },
  {
    label: "AI & hệ thống",
    items: [
      { href: "/insights", label: "Thông tin Insights", icon: Sparkles },
      { href: "/chat", label: "Trợ lý tài chính (AI)", icon: Bot },
      { href: "/settings", label: "Cài đặt hệ thống", icon: Settings },
    ],
  },
];

const ALL_NAV_HREFS = NAV_GROUPS.flatMap((group) => group.items.map((item) => item.href));

function hrefMatches(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/" || pathname.startsWith("/dashboard");
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Trả về href cụ thể nhất (dài nhất) khớp với pathname hiện tại, để mỗi route
 * chỉ làm sáng đúng một mục. Tránh trường hợp `/receipts/upload` làm sáng cả
 * `/receipts` (vì `/receipts` là tiền tố của `/receipts/upload`).
 */
function resolveActiveHref(pathname: string | null): string | null {
  if (!pathname) return null;
  let best: string | null = null;
  for (const href of ALL_NAV_HREFS) {
    if (hrefMatches(pathname, href) && (best === null || href.length > best.length)) {
      best = href;
    }
  }
  return best;
}

function NavGroups({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const activeHref = resolveActiveHref(pathname);
  return (
    <nav className="space-y-6" aria-label="Primary navigation">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="space-y-2">
          <p className="px-3 text-caption-xs font-bold uppercase tracking-wide text-ash">
            {group.label}
          </p>
          <div className="space-y-1">
            {group.items.map((item) => {
              const active = item.href === activeHref;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-body-sm font-semibold transition-colors ${
                    active
                      ? "bg-accent-green-soft text-accent-green"
                      : "text-body hover:bg-surface-soft hover:text-ink"
                  }`}
                >
                  <span
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md border text-[11px] font-black ${
                      active
                        ? "border-accent-green/20 bg-surface-card text-accent-green"
                        : "border-hairline-soft bg-surface-card text-mute"
                    }`}
                    aria-hidden
                  >
                    <Icon className="h-4 w-4 stroke-[1.9]" />
                  </span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

type NavUser = {
  displayName: string;
  initials: string;
  currency: string;
};

function deriveInitials(name: string, email: string): string {
  const source = name.trim() || email.trim();
  if (!source) return "U";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

function useNavUser(): NavUser | null {
  const [user, setUser] = useState<NavUser | null>(null);
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { user: profile } = await getMe();
        if (cancelled) return;
        const displayName = profile.full_name?.trim() || profile.email;
        setUser({
          displayName,
          initials: deriveInitials(profile.full_name ?? "", profile.email),
          currency: profile.currency,
        });
      } catch {
        // chưa đăng nhập / lỗi mạng — giữ null, không hiển thị block user.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  return user;
}

export function Nav() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const user = useNavUser();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-hairline-soft bg-white md:flex">
        <div className="flex h-20 items-center gap-3 border-b border-hairline-soft px-6">
          <Link href="/dashboard" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-green-soft text-accent-green">
              <CreditCard className="h-5 w-5 stroke-[2.2]" aria-hidden />
            </span>
            <span>
              <span className="block text-body-strong text-ink">Ví Thông Minh</span>
              <span className="block font-mono text-[10px] font-medium uppercase tracking-wider text-ash">Finance Analyzer</span>
            </span>
          </Link>
        </div>

        <div className="border-b border-hairline-soft bg-surface-soft/50 p-5">
          <div className="flex items-center gap-3.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-accent-green-soft bg-accent-green-soft text-sm font-bold text-accent-green">
              {user?.initials ?? "··"}
            </div>
            <div className="min-w-0">
              <h4 className="truncate text-sm font-semibold leading-snug text-ink">
                {user?.displayName ?? "Đang tải..."}
              </h4>
              <span className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-accent-green-soft px-2 py-0.5 text-[10px] font-medium text-accent-green">
                <span className="h-1 w-1 rounded-full bg-accent-green" />
                Đơn vị: {user?.currency ?? "VND"}
              </span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-5">
          <NavGroups />
        </div>
      </aside>

      <header className="sticky top-0 z-50 border-b border-hairline-soft bg-surface-card md:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2 text-body-strong text-ink">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-green-soft text-[11px] font-black text-accent-green">
              <CreditCard className="h-4 w-4 stroke-[2.2]" aria-hidden />
            </span>
            <span>Ví Thông Minh</span>
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((value) => !value)}
            className="rounded-md border border-hairline-soft px-3 py-2 text-button-sm text-ink"
            aria-expanded={mobileOpen}
            aria-label="Toggle navigation"
          >
            {mobileOpen ? "Đóng" : "Menu"}
          </button>
        </div>
        {mobileOpen && (
          <div className="border-t border-hairline-soft px-4 py-4">
            <NavGroups onNavigate={() => setMobileOpen(false)} />
          </div>
        )}
      </header>
    </>
  );
}
