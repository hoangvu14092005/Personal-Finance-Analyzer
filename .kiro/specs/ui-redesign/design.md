# Design Document — UI Redesign (Phase 8)

## Overview

Áp dụng design system PostHog-style (mô tả trong `DESIGN.md`) cho toàn bộ frontend Next.js.
Triển khai từ bottom-up: design tokens → primitive components → layout chrome → page-by-page migration.

## Design Goals

1. **Consistency**: mọi page dùng cùng tokens (color, typography, spacing, radius).
2. **Brand identity**: cream canvas + yellow CTA + IBM Plex Sans là signature.
3. **Maintainability**: components primitives reusable, không viết lại CSS mỗi page.
4. **Accessibility**: WCAG AA baseline.
5. **Incremental migration**: không break existing functionality.

## Key Decisions

**Decision 1: Tailwind CSS với custom theme thay vì CSS framework mới**
- Project đã dùng Tailwind. Extend theme với design tokens.
- Không chuyển sang shadcn, Radix UI components — quá nặng cho MVP.
- Tradeoff: phải tự build components primitive. Nhưng controlled hoàn toàn.

**Decision 2: IBM Plex Sans qua next/font/google**
- Auto-optimize, no CLS, self-hosted.
- Fallback: Inter (geometric match), system-ui.

**Decision 3: Emoji mascot thay vì hedgehog custom**
- 💰 thay cho logo app.
- 🧾 📊 💬 cho feature cards.
- Lý do: không có designer, không có assets. Emoji phổ biến, accessible.
- Later: custom SVG mascot nếu có designer.

**Decision 4: Page-by-page migration, không big-bang rewrite**
- Giảm rủi ro break.
- Thứ tự: tokens → shared components → nav/footer → auth → dashboard → rest.

**Decision 5: Không install additional icon library**
- Dùng emoji + inline SVG tự viết khi cần.
- Giữ bundle nhỏ.

## Architecture

### File Structure

```
frontend/web/
├── app/
│   ├── globals.css            # MỚI: base styles, font loading, canvas color
│   ├── layout.tsx             # REDESIGN: nav + footer mới
│   ├── page.tsx               # REDESIGN: landing hero + features
│   ├── login/page.tsx         # REDESIGN
│   ├── register/page.tsx      # REDESIGN
│   ├── dashboard/             # REDESIGN
│   ├── transactions/          # REDESIGN
│   ├── receipts/              # REDESIGN
│   ├── budgets/               # REDESIGN
│   ├── chat/                  # REDESIGN
│   └── health/page.tsx        # keep minimal
├── components/
│   ├── ui/                    # MỚI: primitives
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── PillTab.tsx
│   │   ├── CalloutBanner.tsx
│   │   ├── Link.tsx
│   │   └── Mascot.tsx         # emoji wrapper
│   ├── layout/                # MỚI: Nav + Footer
│   │   ├── Nav.tsx
│   │   ├── Footer.tsx
│   │   └── MobileDrawer.tsx
│   └── chat/                  # MỚI: reusable chat parts (tách từ chat-client.tsx)
│       ├── MessageBubble.tsx
│       ├── SuggestedQuestions.tsx
│       └── ChatInput.tsx
├── lib/
│   ├── design-tokens.ts       # MỚI: JS constants cho non-CSS use (charts, v.v.)
│   └── (existing api files)
├── tailwind.config.ts         # UPDATE: extend theme
└── next.config.ts
```

### Tailwind Theme Extension

```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#eeefe9",
        "surface-soft": "#e5e7e0",
        "surface-card": "#ffffff",
        "surface-doc": "#fcfcfa",
        "surface-dark": "#23251d",
        ink: "#23251d",
        body: "#4d4f46",
        charcoal: "#33342d",
        mute: "#6c6e63",
        ash: "#9b9c92",
        stone: "#b6b7af",
        hairline: "#bfc1b7",
        "hairline-soft": "#dcdfd2",
        "on-dark": "#ffffff",
        primary: {
          DEFAULT: "#f7a501",
          pressed: "#dd9001",
          active: "#b17816",
          on: "#23251d",
        },
        "link-blue": "#1d4ed8",
        "link-teal": "#1078a3",
        "accent-blue": { DEFAULT: "#2c84e0", soft: "#dceaf6" },
        "accent-red": { DEFAULT: "#cd4239", soft: "#f7d6d3" },
        "accent-green": { DEFAULT: "#2c8c66", soft: "#d9eddf" },
        "accent-purple": { DEFAULT: "#7c44a6", soft: "#e7d8ee" },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "display-xl": ["36px", { lineHeight: "1.5", fontWeight: "700" }],
        "display-lg": ["24px", { lineHeight: "1.33", letterSpacing: "-0.6px", fontWeight: "800" }],
        "heading-lg": ["21px", { lineHeight: "1.4", letterSpacing: "-0.5px", fontWeight: "700" }],
        "heading-md": ["20px", { lineHeight: "1.4", fontWeight: "700" }],
        "heading-sm": ["18px", { lineHeight: "1.5", fontWeight: "700" }],
        "heading-sm-mixed": ["18px", { lineHeight: "1.56", fontWeight: "600" }],
        "body-md": ["16px", { lineHeight: "1.5", fontWeight: "400" }],
        "body-strong": ["16px", { lineHeight: "1.5", fontWeight: "600" }],
        "body-sm": ["15px", { lineHeight: "1.71", fontWeight: "400" }],
        "body-xs": ["14px", { lineHeight: "1.43", fontWeight: "500" }],
        "caption-md": ["14px", { lineHeight: "1.71", fontWeight: "700" }],
        "caption-sm": ["13px", { lineHeight: "1.5", fontWeight: "500" }],
        "caption-xs": ["12px", { lineHeight: "1.33", fontWeight: "600" }],
        "utility-xs": ["12px", { lineHeight: "1.33", fontWeight: "700", letterSpacing: "0" }],
        "button-md": ["14px", { lineHeight: "1.5", fontWeight: "700" }],
        "button-sm": ["13px", { lineHeight: "1", fontWeight: "500" }],
      },
      spacing: {
        xxs: "2px", xs: "4px", sm: "8px", md: "12px",
        lg: "16px", xl: "24px", xxl: "32px", section: "80px",
      },
      borderRadius: {
        none: "0px", xs: "2px", sm: "4px", md: "6px", lg: "8px", full: "9999px",
      },
    },
  },
  plugins: [],
};
```

### globals.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: var(--font-ibm-plex), Inter, system-ui, sans-serif;
  }
  body {
    @apply bg-canvas text-body;
    font-size: 16px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, h4 {
    @apply text-ink;
  }
}
```

## Component Specs

### Button

```tsx
// components/ui/Button.tsx
type ButtonVariant = "primary" | "secondary" | "tertiary" | "disabled";

interface ButtonProps {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  children: React.ReactNode;
  // ... standard button props
}

export function Button({ variant = "primary", ...props }: ButtonProps) {
  const base = "rounded-md font-bold transition-none";
  const variants = {
    primary: "bg-primary text-primary-on hover:bg-primary-pressed h-10 px-4 text-button-md",
    secondary: "bg-surface-soft text-ink h-10 px-4 text-button-md",
    tertiary: "bg-transparent text-ink h-10 px-3 text-button-md",
    disabled: "bg-surface-soft text-ash h-10 px-4 cursor-not-allowed",
  };
  return <button className={`${base} ${variants[variant]}`} {...props} />;
}
```

### Card

```tsx
// components/ui/Card.tsx
type CardVariant = "product" | "doc" | "feature" | "pricing";

export function Card({ variant = "product", className, children }: CardProps) {
  const variants = {
    product: "bg-surface-card border border-hairline rounded-md p-xl",
    doc: "bg-surface-doc border border-hairline rounded-md p-xl",
    feature: "bg-surface-card border border-hairline rounded-md p-lg",
    pricing: "bg-surface-card border border-hairline rounded-md p-xxl",
  };
  return <div className={`${variants[variant]} ${className || ""}`}>{children}</div>;
}
```

### CalloutBanner

```tsx
type Severity = "info" | "success" | "warning" | "note";

const emojiMap = { info: "💡", success: "✅", warning: "⚠️", note: "📘" };
const bgMap = {
  info: "bg-accent-blue-soft",
  success: "bg-accent-green-soft",
  warning: "bg-accent-red-soft",
  note: "bg-accent-purple-soft",
};

export function CalloutBanner({ severity, title, children }: Props) {
  return (
    <div className={`rounded-md p-lg ${bgMap[severity]} text-ink`}>
      <div className="flex gap-sm">
        <span aria-hidden>{emojiMap[severity]}</span>
        <div>
          {title && <div className="font-semibold mb-xs">{title}</div>}
          <div className="text-body-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
```

### PillTab

```tsx
export function PillTab({ active, children, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-lg py-xs text-button-sm transition-colors ${
        active
          ? "bg-ink text-on-dark"
          : "bg-transparent text-body hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
```

### Input

```tsx
export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={`w-full h-9 px-md rounded-md border border-hairline bg-surface-card text-ink text-body-md focus:outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20 ${className || ""}`}
      {...props}
    />
  );
}
```

## Layout Chrome

### Nav

```tsx
// components/layout/Nav.tsx
export function Nav() {
  return (
    <header className="sticky top-0 z-50 h-14 bg-canvas border-b border-hairline-soft">
      <div className="mx-auto max-w-7xl h-full px-xl flex items-center justify-between">
        <Link href="/" className="flex items-center gap-sm text-ink text-body-strong">
          <span aria-hidden>💰</span>
          <span>PFA</span>
        </Link>
        
        <nav className="hidden md:flex items-center gap-lg text-body-strong">
          <Link href="/dashboard" className="text-body hover:text-ink">Dashboard</Link>
          <Link href="/transactions" className="text-body hover:text-ink">Giao dịch</Link>
          <Link href="/budgets" className="text-body hover:text-ink">Ngân sách</Link>
          <Link href="/chat" className="text-body hover:text-ink">💬 Trợ lý</Link>
        </nav>
        
        <div className="flex items-center gap-md">
          <Link href="/login" className="hidden sm:inline text-body">Đăng nhập</Link>
          <Button variant="primary" size="sm">Bắt đầu — miễn phí</Button>
        </div>
      </div>
    </header>
  );
}
```

### Footer

```tsx
export function Footer() {
  return (
    <footer className="bg-canvas border-t border-hairline py-xxl px-xl">
      <div className="mx-auto max-w-7xl grid grid-cols-2 md:grid-cols-3 gap-xl">
        <div>
          <h3 className="text-utility-xs text-body mb-md uppercase">Sản phẩm</h3>
          <ul className="space-y-xs text-body-xs">
            <li><Link href="/dashboard">Dashboard</Link></li>
            <li><Link href="/transactions">Giao dịch</Link></li>
            <li><Link href="/chat">Trợ lý AI</Link></li>
          </ul>
        </div>
        {/* more columns */}
      </div>
      <div className="mt-xl pt-lg border-t border-hairline-soft text-caption-xs text-mute">
        © 2026 Personal Finance Analyzer
      </div>
    </footer>
  );
}
```

## Page Designs

### Landing (/)

```
┌─────────────────────────────────────┐
│ [nav]                               │
├─────────────────────────────────────┤
│                                     │
│    Quản lý chi tiêu                 │
│    thông minh hơn       [display-xl]│
│                                     │
│    Upload hóa đơn → OCR tự động     │
│    → Hỏi chatbot về chi tiêu        │
│                                     │
│    [Yellow CTA] [Secondary]         │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  [🧾 Card]  [📊 Card]  [💬 Card]    │
│  Upload    Dashboard   AI Trợ lý    │
│                                     │
├─────────────────────────────────────┤
│ [footer]                            │
└─────────────────────────────────────┘
```

### Dashboard (/dashboard)

- Page title: `display-lg` "Dashboard"
- Range pills: `PillTab` group (7d / 30d / Tháng này / Tháng trước)
- Summary row: 4 `feature-tile` (Total spend, Count, Delta, Budget status)
- Category chart: `product-card` với Recharts
- Recent transactions: `doc-card` với hairline-soft dividers
- Budget alerts: `CalloutBanner` warning/exceeded

### Chat (/chat)

- Centered column max-w-2xl
- Header: `display-lg` "💬 Trợ lý chi tiêu" + clear button
- Messages area scrollable
- User bubble: `bg-ink text-on-dark rounded-lg`
- Assistant bubble: `bg-surface-card border-hairline rounded-lg`
- Suggested questions: `PillTab` chips
- Input: sticky bottom `Input` + `Button primary` "Gửi"

## Migration Strategy

### Phase 8.1: Foundation (tokens + primitives)
1. Update `tailwind.config.ts` với theme extension
2. Update `app/globals.css` với font + base styles
3. Install IBM Plex Sans via `next/font/google`
4. Build components primitives trong `components/ui/`
5. Storybook-like test page `/styleguide` để verify tokens apply đúng

### Phase 8.2: Layout chrome
1. Nav component mới
2. Footer component mới
3. Mobile drawer
4. Update `app/layout.tsx` dùng components mới
5. E2E test: nav links hoạt động

### Phase 8.3: Auth + Landing
1. `/` (landing page)
2. `/login`
3. `/register`
4. E2E test login flow

### Phase 8.4: Dashboard
1. Redesign `/dashboard`
2. Update `CategoryChart` với Recharts color tokens
3. Summary tiles + budget section
4. E2E test dashboard

### Phase 8.5: Transactions + Receipts
1. `/transactions`, `/transactions/new`
2. `/receipts/upload`, `/receipts/[id]/review`
3. E2E test transaction CRUD

### Phase 8.6: Budgets
1. `/budgets` list + create modal

### Phase 8.7: Chat
1. Redesign `/chat`
2. Message bubbles, suggested questions
3. Streaming animation

### Phase 8.8: Polish
1. Mobile responsive check
2. Accessibility audit (Lighthouse)
3. Screenshot before/after

## Testing Strategy

### Visual regression
- Screenshot mỗi page (desktop + mobile) trước và sau.
- Manual compare.

### E2E Playwright
- Existing tests phải pass sau migration.
- Update selectors nếu đổi structure.

### Accessibility
- Lighthouse run mỗi page → target ≥ 90.
- Keyboard tab qua form.
- Screen reader test cho chat page.

## Risks

| Risk | Mitigation |
|---|---|
| IBM Plex Sans load slow | Use next/font auto-optimize; swap fallback Inter |
| Breaking existing Playwright tests | Run E2E sau mỗi page migration, fix selectors |
| Tailwind theme collision với defaults | Use namespaced custom utilities, test layout ở dev |
| Mobile layout gãy | Test mỗi page ở 375px, 768px, 1280px |
| Emoji không render đồng nhất OS | Accept OS variance; consider Twemoji nếu cần |

## Ước tính
Tổng 8-12 ngày làm việc (tùy polish).
