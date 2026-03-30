"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { login } from "@/lib/auth-api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dang nhap that bai");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="mx-auto max-w-md space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">Dang nhap</h1>
      <p className="text-sm text-slate-600">Su dung tai khoan de vao dashboard.</p>

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
          <span className="text-sm font-medium text-slate-700">Mat khau</span>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-teal-500 focus:ring"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <button
          className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Dang xu ly..." : "Dang nhap"}
        </button>
      </form>

      <p className="text-sm text-slate-600">
        Chua co tai khoan?{" "}
        <Link href="/register" className="font-semibold text-teal-700 hover:text-teal-900">
          Dang ky
        </Link>
      </p>
    </section>
  );
}
