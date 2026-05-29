# Requirements Document — UI Redesign (Phase 8)

## Introduction

Redesign toàn bộ UI frontend theo design system mô tả trong `DESIGN.md` (PostHog-style).
Design hiện tại đang dùng slate palette, generic Tailwind defaults. Design mới mang tính
chất "engineering sketchbook" với white canvas, single yellow CTA, IBM Plex Sans typography,
card với hairline borders.

### Bối cảnh
- Sau Phase 6 (Chatbot) và Phase 7 (RAG), tất cả tính năng core đã hoạt động.
- Đây là lúc đánh bóng UX và làm cho sản phẩm có bản sắc.
- Đổi visual identity, không đổi functionality.

### Out of scope
- Không thay đổi backend API.
- Không thêm tính năng mới.
- Không đổi thông tin hiển thị, chỉ đổi cách hiển thị.
- Không làm dashboard/admin web riêng — giữ pages hiện tại.

## Glossary

- **Design Tokens**: màu, typography, spacing, radius được định nghĩa trong DESIGN.md.
- **White Canvas**: màu nền chủ đạo `#ffffff` (colors.canvas).
- **Yellow CTA**: màu primary action `#f7a501` (colors.primary).
- **Hairline Border**: đường viền 1px `#bfc1b7` (colors.hairline) thay cho drop-shadow.
- **Hedgehog Mascot**: illustration cartoon — brand decoration signature.
- **Callout Banner**: pastel tinted panel (blue/green/red/purple) cho thông báo inline.

## Requirements

### Requirement 1: Design tokens & theme foundation

**User Story:** Là frontend dev, tôi cần design tokens centralize để mọi page dùng nhất quán.

#### Acceptance Criteria
1. THE Tailwind config SHALL define custom color palette mapping từ DESIGN.md (canvas, primary, ink, body, hairline, v.v.).
2. THE Tailwind config SHALL define custom spacing scale (xxs, xs, sm, md, lg, xl, xxl, section).
3. THE Tailwind config SHALL define custom border radius scale (none, xs, sm, md, lg, full).
4. THE project SHALL load IBM Plex Sans Variable font từ Google Fonts (next/font/google).
5. THE global CSS SHALL apply `canvas` background và `body` text color mặc định cho `<body>`.
6. THE font stack fallback SHALL là `IBM Plex Sans → Inter → system-ui`.

### Requirement 2: Reusable UI components

**User Story:** Mỗi page phải dùng cùng một bộ component primitives.

#### Acceptance Criteria
1. THE system SHALL có thư mục `components/ui/` chứa primitives:
   - `Button` (primary / secondary / tertiary / disabled variants)
   - `Input` (text-input với focused state)
   - `Card` (product-card, doc-card, feature-tile variants)
   - `Badge` (uppercase, promo variants)
   - `PillTab` (default / active)
   - `CalloutBanner` (blue / green / red / purple với emoji icon)
   - `Link` (inline link-teal color)
2. EACH component SHALL follow DESIGN.md spec exactly (padding, radius, typography, colors).
3. EACH component SHALL có TypeScript props typed đầy đủ.
4. EACH component SHALL có default + active/pressed states (không cần hover theo policy DESIGN.md).

### Requirement 3: Global layout chrome

**User Story:** Navigation và footer phải theo style mới trên mọi page.

#### Acceptance Criteria
1. THE primary nav SHALL theo `primary-nav` spec: white background, ink text, height 56px, wordmark + yellow "Get started" CTA ở xa phải.
2. THE nav SHALL hiển thị app name kèm mascot illustration (emoji placeholder OK cho MVP: 🦔 hoặc 💰).
3. THE nav SHALL collapse thành hamburger drawer ở mobile (< 768px).
4. THE footer SHALL theo `footer-section` spec: white background, hairline top rule, 3-column link grid ở desktop, 2-up mobile.
5. THE page layout SHALL continue white canvas edge-to-edge, không có shaded section bands.

### Requirement 4: Page-specific redesign

#### 4.1 Landing page (/)
**User Story:** First impression phải nổi bật, call-to-action rõ ràng.

##### Acceptance Criteria
1. Hero section SHALL có display-xl headline + body-md subline + 2 CTAs (primary yellow + secondary).
2. Feature tiles 3-up grid describe 3 core features (Upload receipt, Dashboard analytics, AI Chatbot).
3. Section spacing SHALL là 80px giữa các major blocks.

#### 4.2 Auth pages (/login, /register)
**User Story:** Auth form phải đơn giản, không phân tâm.

##### Acceptance Criteria
1. Form centered ở viewport, max-width 480px.
2. Logo + tagline ở top.
3. Input fields dùng `text-input` spec.
4. Submit button dùng `button-primary` (yellow).
5. Link chuyển login ↔ register dùng `link-inline` (teal).

#### 4.3 Dashboard (/dashboard)
**User Story:** Dashboard hiển thị nhiều số liệu — phải dễ scan.

##### Acceptance Criteria
1. Range filter tabs dùng `pill-tab` (full rounded, flip ink/white khi active).
2. Summary cards (total spend, count, delta) trong grid 4-up dùng `feature-tile`.
3. Category chart trong `product-card`.
4. Recent transactions list dùng `doc-card` với hairline divider giữa rows.
5. Budget usage section dùng `callout-banner` màu tương ứng status (green=safe, purple=warning, red=exceeded).

#### 4.4 Transactions (/transactions, /transactions/new)
##### Acceptance Criteria
1. Filter bar dùng `text-input` và `pill-tab`.
2. Transaction list trong `doc-card`.
3. Delete/edit buttons dùng `button-tertiary`.
4. "Nhập tay" + "Upload hóa đơn" buttons ở header dùng `button-primary` + `button-secondary`.

#### 4.5 Receipts (/receipts/upload, /receipts/[id]/review)
##### Acceptance Criteria
1. Upload dropzone dùng dashed hairline border trên `surface-card`.
2. Review form trong `product-card` với low-confidence fields highlight bằng `accent-red-soft` callout.
3. Raw OCR text trong `code-block` (inverted dark surface).

#### 4.6 Budgets (/budgets)
##### Acceptance Criteria
1. Budget cards trong grid 3-up dùng `feature-tile`.
2. Progress bar dùng accent-blue (safe), accent-purple-soft (warning), accent-red (exceeded).
3. Create budget form trong modal/panel với `text-input` + `button-primary`.

#### 4.7 Chat (/chat)
**User Story:** Chat UI là showcase của brand — phải chỉn chu.

##### Acceptance Criteria
1. Chat layout: max-width 720px centered, full height.
2. User bubble: `ink` background, `on-dark` text, `rounded.lg`.
3. Assistant bubble: `surface-card` (white), `hairline` border, `ink` text.
4. Suggested questions dùng `pill-tab`.
5. Input bar sticky bottom với `text-input` + `button-primary` "Gửi".
6. Streaming cursor/indicator dùng dot animation với `mute` color.
7. Empty state có mascot illustration hoặc emoji + welcoming copy.

### Requirement 5: Typography hierarchy

**User Story:** Hierarchy rõ ràng giúp user scan content nhanh.

#### Acceptance Criteria
1. Page title SHALL dùng `display-lg` (24px/800).
2. Section heading SHALL dùng `heading-lg` (21px/700).
3. Card title SHALL dùng `heading-sm-mixed` (18px/600).
4. Section eyebrow (small caps) SHALL dùng `utility-xs` (12px/700 uppercase).
5. Body text SHALL dùng `body-md` (16px/400).
6. Metadata/caption SHALL dùng `body-xs` (14px/500).
7. Button text SHALL dùng `button-md` (14px/700).

### Requirement 6: Responsive behavior

**User Story:** App phải dùng được trên mobile, tablet, desktop.

#### Acceptance Criteria
1. Desktop (≥ 1280px): layouts 3-up/4-up grids, full sidebar navigation.
2. Tablet (768-1279px): 2-up grids, hamburger nav.
3. Mobile (< 768px): 1-up stacked, hamburger nav, touch targets ≥ 40px.
4. Section padding SHALL scale: 80px desktop → 64px tablet → 48px mobile.
5. Hero typography SHALL scale: display-xl 36px → 28px mobile.

### Requirement 7: Accessibility baseline

**User Story:** App phải dùng được với screen reader và keyboard.

#### Acceptance Criteria
1. Color contrast SHALL pass WCAG AA cho tất cả text (body 4d4f46 trên canvas eeefe9 = 7:1 ratio).
2. Focus rings SHALL hiển thị rõ với `focus-ring` color.
3. Interactive elements SHALL có `aria-label` khi không có visible text.
4. Form inputs SHALL có `<label>` associated.
5. Touch targets SHALL ≥ 40x40px.

### Requirement 8: Migration strategy

**User Story:** Không muốn broken UI giữa phase redesign.

#### Acceptance Criteria
1. THE migration SHALL page-by-page, không tất cả 1 lần.
2. EACH page migration SHALL giữ nguyên function, chỉ đổi visual.
3. THE system SHALL có 1 PR mỗi page (hoặc group 2-3 pages tương tự).
4. E2E tests Playwright SHALL pass sau mỗi migration.
5. THE project SHALL document screenshots before/after mỗi page.

### Requirement 9: Mascot placeholder strategy

**User Story:** Không có ngân sách vẽ hedgehog custom — cần placeholder hợp lý.

#### Acceptance Criteria
1. THE system SHALL dùng emoji (💰 🧾 📊 💬) làm mascot placeholder cho MVP.
2. WHERE DESIGN.md mô tả "hedgehog illustration", placeholder SHALL là emoji hoặc inline SVG đơn giản.
3. LATER iteration có thể thay bằng custom illustrations nếu có designer.

### Requirement 10: Exit criteria

#### Acceptance Criteria
1. Tất cả pages (auth, dashboard, transactions, receipts, budgets, chat) SHALL match DESIGN.md spec.
2. Typography consistent dùng IBM Plex Sans.
3. Primary CTA SHALL dùng yellow `#f7a501` nhất quán.
4. Canvas SHALL white `#ffffff` ở mọi page.
5. Card SHALL flat với hairline border, không drop-shadow.
6. Responsive ở mobile/tablet/desktop.
7. E2E tests pass.
8. Lighthouse accessibility ≥ 90.
