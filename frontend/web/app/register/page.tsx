"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { register } from "@/lib/auth-api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await register({
        email,
        password,
        full_name: fullName || undefined,
        currency: "VND",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Ho_Chi_Minh",
        locale: navigator.language || "vi-VN",
      });
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dang ky that bai");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="mx-auto max-w-md space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">Dang ky tai khoan</h1>
      <p className="text-sm text-slate-600">Tao tai khoan moi de bat dau quan ly chi tieu.</p>

      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Email</span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Ho va ten</span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring"
            type="text"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="(Tuy chon)"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Mat khau</span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <p className="text-xs text-slate-500">Toi thieu 8 ky tu, gom chu va so.</p>
        </label>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <button
          className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Dang xu ly..." : "Tao tai khoan"}
        </button>
      </form>

      <p className="text-sm text-slate-600">
        Da co tai khoan?{" "}
        <Link href="/login" className="font-semibold text-teal-700 hover:text-teal-900">
          Dang nhap
        </Link>
      </p>
    </section>
  );
}
