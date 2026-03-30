"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getMe, logout } from "@/lib/auth-api";

export default function DashboardPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    const checkSession = async () => {
      try {
        const result = await getMe();
        if (!isCancelled) {
          setUserEmail(result.user.email);
        }
      } catch {
        if (!isCancelled) {
          router.replace("/login");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    void checkSession();

    return () => {
      isCancelled = true;
    };
  }, [router]);

  const onLogout = async () => {
    await logout();
    router.replace("/login");
  };

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-sm text-slate-600">Dang xac thuc phien dang nhap...</p>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
      <p className="text-sm text-slate-600">Ban dang dang nhap voi: {userEmail}</p>
      <p className="text-sm text-slate-600">
        Day la protected page baseline cho phase 1.
      </p>
      <button
        className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
        onClick={onLogout}
        type="button"
      >
        Dang xuat
      </button>
    </section>
  );
}
