import type { Metadata } from "next";
import { Bell } from "lucide-react";
import "./globals.css";
import { Nav } from "@/components/layout/Nav";

export const metadata: Metadata = {
  title: "Personal Finance Analyzer",
  description: "Quản lý chi tiêu thông minh với AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body
        suppressHydrationWarning
        className="antialiased bg-white text-body"
      >
        <div className="min-h-screen bg-white">
          <Nav />
          <div className="min-h-screen md:pl-64">
            <header className="hidden h-16 items-center justify-between border-b border-hairline-soft bg-white px-8 md:flex">
              <span className="text-sm font-semibold text-ink">
                Quản lý chi tiêu thông minh
              </span>
              <div className="flex items-center gap-4 text-mute">
                <span className="relative rounded-full p-1.5 text-ash" title="Thông báo">
                  <Bell className="h-5 w-5 stroke-[1.8]" aria-hidden />
                  <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-accent-red ring-2 ring-white" />
                </span>
              </div>
            </header>
            <main className="w-full px-4 py-6 md:px-8 md:py-8">
              <div className="mx-auto w-full max-w-7xl">{children}</div>
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
