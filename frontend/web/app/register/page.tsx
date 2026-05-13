"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { register } from "@/lib/auth-api";
import { Button, CalloutBanner, Card, DisplayLg, Input } from "@/components/ui";

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
        timezone:
          Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Ho_Chi_Minh",
        locale: navigator.language || "vi-VN",
      });
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-10">
      <Card variant="product" className="space-y-6">
        <div>
          <DisplayLg>Tạo tài khoản</DisplayLg>
          <p className="mt-2 text-body-sm text-body">
            Bắt đầu miễn phí, quản lý chi tiêu dễ dàng hơn.
          </p>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block space-y-1.5">
            <span className="text-body-xs text-ink">Email</span>
            <Input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="you@example.com"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-body-xs text-ink">Họ và tên</span>
            <Input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="(tuỳ chọn)"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-body-xs text-ink">Mật khẩu</span>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              placeholder="••••••••"
            />
            <span className="text-caption-sm text-mute">
              Tối thiểu 8 ký tự, gồm chữ và số.
            </span>
          </label>

          {error ? (
            <CalloutBanner severity="warning">{error}</CalloutBanner>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? "Đang xử lý..." : "Tạo tài khoản"}
          </Button>
        </form>

        <p className="text-body-sm text-body text-center">
          Đã có tài khoản?{" "}
          <Link
            href="/login"
            className="text-link-teal font-semibold hover:underline"
          >
            Đăng nhập
          </Link>
        </p>
      </Card>
    </div>
  );
}
