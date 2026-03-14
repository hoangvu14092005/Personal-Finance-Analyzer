import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Personal Finance Analyzer",
  description: "Frontend shell for Personal Finance Analyzer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div className="min-h-screen">
          <header className="border-b border-slate-200 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
            <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
              <Link href="/" className="text-lg font-semibold tracking-tight text-slate-900">
                Personal Finance Analyzer
              </Link>
              <nav className="flex items-center gap-4 text-sm text-slate-600">
                <Link href="/" className="hover:text-slate-900">
                  Home
                </Link>
                <Link href="/health" className="hover:text-slate-900">
                  Health
                </Link>
              </nav>
            </div>
          </header>

          <main className="mx-auto w-full max-w-5xl px-6 py-10">{children}</main>

          <footer className="border-t border-slate-200 bg-white/70">
            <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4 text-xs text-slate-500">
              <span>Phase 0 Foundation</span>
              <span>Next.js 15 + Tailwind</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
