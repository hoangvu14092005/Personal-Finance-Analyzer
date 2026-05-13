import Link from "next/link";
import { Button, Card, DisplayXl, Eyebrow, HeadingSmMixed } from "@/components/ui";

const FEATURES = [
  {
    icon: "🧾",
    title: "Upload hóa đơn",
    description:
      "Chụp hoặc tải ảnh hóa đơn, AI tự đọc thông tin và tạo giao dịch cho bạn.",
  },
  {
    icon: "📊",
    title: "Dashboard tổng quan",
    description:
      "Xem chi tiêu theo danh mục, so sánh kỳ trước, theo dõi ngân sách.",
  },
  {
    icon: "💬",
    title: "AI Trợ lý hỏi đáp",
    description:
      "Hỏi bất kỳ câu nào về chi tiêu bằng tiếng Việt tự nhiên.",
  },
];

export default function Home() {
  return (
    <div className="space-y-20">
      {/* Hero */}
      <section className="text-center pt-10 pb-6">
        <Eyebrow className="mb-4">Quản lý tài chính cá nhân</Eyebrow>
        <DisplayXl className="max-w-3xl mx-auto">
          Quản lý chi tiêu thông minh cùng AI
        </DisplayXl>
        <p className="mt-6 max-w-2xl mx-auto text-body-md text-body">
          Upload hóa đơn, theo dõi chi tiêu và hỏi đáp về tài chính cá nhân —
          tất cả bằng tiếng Việt, tự nhiên và nhanh chóng.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/register">
            <Button variant="primary">Bắt đầu miễn phí</Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary">Xem demo</Button>
          </Link>
        </div>
      </section>

      {/* Features grid */}
      <section>
        <div className="text-center mb-10">
          <Eyebrow className="mb-3">Tính năng chính</Eyebrow>
          <h2 className="text-heading-lg text-ink">
            3 cách giúp bạn quản lý chi tiêu tốt hơn
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card key={feature.title} variant="feature">
              <div className="text-4xl mb-3" aria-hidden>
                {feature.icon}
              </div>
              <HeadingSmMixed className="mb-2">{feature.title}</HeadingSmMixed>
              <p className="text-body-sm text-body">{feature.description}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA section */}
      <section className="text-center py-10">
        <h2 className="text-heading-lg text-ink mb-4">
          Sẵn sàng kiểm soát chi tiêu?
        </h2>
        <p className="text-body-md text-body mb-6 max-w-xl mx-auto">
          Tạo tài khoản miễn phí và bắt đầu upload hóa đơn đầu tiên chỉ trong 1 phút.
        </p>
        <Link href="/register">
          <Button variant="primary">Tạo tài khoản miễn phí</Button>
        </Link>
      </section>
    </div>
  );
}
