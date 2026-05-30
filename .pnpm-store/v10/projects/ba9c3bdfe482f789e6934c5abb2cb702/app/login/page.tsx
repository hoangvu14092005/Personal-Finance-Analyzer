"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { login } from "@/lib/auth-api";
import { Button, CalloutBanner, Card, DisplayLg, Input } from "@/components/ui";

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
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-10">
      <Card variant="product" className="space-y-6">
        <div>
          <DisplayLg>Đăng nhập</DisplayLg>
          <p className="mt-2 text-body-sm text-body">
            Sử dụng tài khoản để vào dashboard.
          </p>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block space-y-1.5">
            <span className="text-body-xs text-ink">Tài khoản hoặc email</span>
            <Input
              type="text"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="admin"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-body-xs text-ink">Mật khẩu</span>
            <Input
              type="password"
              aria-label="Mat khau"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              placeholder="••••••••"
            />
          </label>

          {error ? (
            <CalloutBanner severity="warning">{error}</CalloutBanner>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            aria-label="Dang nhap"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? "Đang xử lý..." : "Đăng nhập"}
          </Button>
        </form>

        <p className="text-body-sm text-body text-center">
          Chưa có tài khoản?{" "}
          <Link
            href="/register"
            className="text-link-teal font-semibold hover:underline"
          >
            Đăng ký
          </Link>
        </p>
      </Card>
    </div>
  );
}
