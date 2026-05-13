"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/transactions", label: "Giao dịch" },
  { href: "/receipts/upload", label: "Hóa đơn" },
  { href: "/budgets", label: "Ngân sách" },
  { href: "/chat", label: "💬 Trợ lý" },
];

export function Nav() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 bg-canvas border-b border-hairline-soft">
      <div className="mx-auto max-w-6xl h-14 px-6 flex items-center justify-between gap-6">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-ink text-body-strong flex-shrink-0"
        >
          <span aria-hidden className="text-xl leading-none">💰</span>
          <span>PFA</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6 flex-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`text-body-strong transition-colors ${
                  active ? "text-ink" : "text-body hover:text-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right cluster */}
        <div className="hidden md:flex items-center gap-3 flex-shrink-0">
          <Link
            href="/login"
            className="text-body-strong text-body hover:text-ink"
          >
            Đăng nhập
          </Link>
          <Link href="/register">
            <Button variant="primary" size="sm">
              Bắt đầu miễn phí
            </Button>
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="md:hidden p-2 text-ink"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            {mobileOpen ? (
              <path d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path d="M3 12h18M3 6h18M3 18h18" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden border-t border-hairline-soft bg-canvas">
          <nav className="px-6 py-4 flex flex-col gap-3">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-body-strong text-body hover:text-ink py-2"
                onClick={() => setMobileOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <div className="border-t border-hairline-soft pt-3 flex flex-col gap-2">
              <Link
                href="/login"
                className="text-body-strong text-body hover:text-ink py-2"
                onClick={() => setMobileOpen(false)}
              >
                Đăng nhập
              </Link>
              <Link href="/register" onClick={() => setMobileOpen(false)}>
                <Button variant="primary" size="sm" className="w-full">
                  Bắt đầu miễn phí
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
