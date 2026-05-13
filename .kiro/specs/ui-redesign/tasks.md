# Implementation Tasks — UI Redesign (Phase 8)

## Prerequisites
- Phase 6 (Chatbot) + Phase 7 (RAG) complete.
- Frontend build pass hiện tại.

---

## Task 8.1 — Design tokens foundation (1 ngày)

### Steps
1. Update `frontend/web/tailwind.config.ts`:
   - Extend `theme.extend.colors` với full palette từ DESIGN.md.
   - Extend `fontSize` với typography scale.
   - Extend `spacing`, `borderRadius`.
2. Install IBM Plex Sans:
   ```tsx
   // app/layout.tsx
   import { IBM_Plex_Sans } from "next/font/google";
   const ibmPlex = IBM_Plex_Sans({
     weight: ["400", "500", "600", "700"],
     subsets: ["latin", "vietnamese"],
     variable: "--font-ibm-plex",
     display: "swap",
   });
   ```
3. Update `app/globals.css`:
   - Reset với Tailwind base.
   - Set `body` bg-canvas text-body.
   - Set default font family.
4. Tạo `lib/design-tokens.ts` export JS constants cho charts/color usage ngoài CSS.
5. Tạo `/styleguide` page (dev-only) show all tokens + components.

### Validation
- `pnpm dev` → `/styleguide` hiển thị đúng colors + typography.
- No Tailwind errors.

---

## Task 8.2 — Primitive components (1.5 ngày)

### Steps
Tạo trong `components/ui/`:

1. **Button.tsx** — 4 variants (primary / secondary / tertiary / disabled), sizes md/sm.
2. **Input.tsx** — text-input với focus ring.
3. **Card.tsx** — 4 variants (product / doc / feature / pricing).
4. **Badge.tsx** — uppercase + promo variants.
5. **PillTab.tsx** — default + active states.
6. **CalloutBanner.tsx** — 4 severities với emoji icons.
7. **Link.tsx** — link-teal inline color.
8. **Mascot.tsx** — emoji wrapper với size prop (sm/md/lg).
9. **Heading.tsx** — display-lg, heading-lg, heading-md variants.

### Tests
- Render mỗi component trong `/styleguide`.
- Verify props work (variants, sizes, disabled states).

### Validation
- TypeScript clean (`tsc --noEmit`).
- ESLint pass.

---

## Task 8.3 — Layout chrome: Nav + Footer (1 ngày)

### Steps
1. Tạo `components/layout/Nav.tsx`:
   - Desktop horizontal nav với links.
   - Mobile hamburger drawer.
   - Sticky top, cream bg.
   - App logo (💰 emoji) + "PFA" name.
   - Yellow "Bắt đầu" CTA.
2. Tạo `components/layout/Footer.tsx`:
   - 3-column link grid (Sản phẩm / Tài nguyên / Công ty).
   - Copyright row.
   - Cream bg + hairline top.
3. Tạo `components/layout/MobileDrawer.tsx`:
   - Slide from left.
   - Same nav items.
   - Close on link click.
4. Update `app/layout.tsx` dùng Nav + Footer mới.
5. Auth-aware: nav hiển thị khác khi logged in (account menu thay "Đăng nhập/Đăng ký").

### Validation
- Nav links dẫn đúng pages.
- Mobile drawer open/close smooth.
- E2E Playwright tests vẫn pass.

---

## Task 8.4 — Landing page (0.5 ngày)

### Steps
1. Redesign `app/page.tsx`:
   - Hero: display-xl headline tiếng Việt.
   - 2 CTAs: "Bắt đầu miễn phí" (primary) + "Xem demo" (secondary).
   - 3 feature tiles (🧾 Upload, 📊 Dashboard, 💬 AI Chat).
   - Section rhythm 80px.
2. Wire CTAs dẫn `/register` và `/dashboard`.

### Validation
- Visual check mobile + desktop.
- Accessibility: headings semantic đúng (h1 → h2 → h3).

---

## Task 8.5 — Auth pages (0.5 ngày)

### Steps
1. `/login`: form centered max-w-md.
   - Page title: "Đăng nhập".
   - Email + Password Input.
   - Submit Button primary.
   - Link đến /register.
2. `/register`: tương tự với fullname field.
3. Error states dùng CalloutBanner severity="warning".

### Validation
- Existing auth flow test (Playwright) pass.
- Form validation hiển thị rõ errors.

---

## Task 8.6 — Dashboard (1.5 ngày)

### Steps
1. Redesign `app/dashboard/dashboard-client.tsx`:
   - Page header với title display-lg.
   - Range filter dùng PillTab group.
   - Summary row: 4 feature-tile cards (total, count, delta, budget status).
   - Delta arrow với accent-green (down) / accent-red (up).
   - Category chart trong product-card.
   - Recent transactions trong doc-card, hairline-soft row dividers.
   - Budget usage section dùng CalloutBanner color theo status.
2. Update `CategoryChart` colors với design tokens.
3. Empty state: friendly message + CTA "Thêm giao dịch đầu tiên".

### Validation
- Dashboard render đúng số liệu thật.
- Responsive desktop/mobile.

---

## Task 8.7 — Transactions (0.5 ngày)

### Steps
1. `/transactions`:
   - Filter bar: Input + PillTab cho date range.
   - List trong doc-card.
   - Action buttons tertiary.
   - Header buttons primary "Nhập tay" + secondary "Upload".
2. `/transactions/new`:
   - Form trong product-card max-w-2xl centered.
   - Label + Input pairs.
   - Submit primary button.
3. Delete confirmation dùng CalloutBanner warning inline.

### Validation
- CRUD flow E2E test pass.

---

## Task 8.8 — Receipts (0.5 ngày)

### Steps
1. `/receipts/upload`:
   - Dropzone với dashed hairline border.
   - Progress indicator dùng accent-blue.
2. `/receipts/[id]/review`:
   - Form pre-filled trong product-card.
   - Low-confidence fields highlight với accent-red-soft bg.
   - Raw OCR text trong code-block surface-dark.
   - CalloutBanner note với OCR confidence score.

### Validation
- Upload flow pass.

---

## Task 8.9 — Budgets (0.5 ngày)

### Steps
1. `/budgets`:
   - Grid 3-up feature-tile mỗi budget.
   - Progress bar:
     - safe: accent-green width %
     - warning: accent-purple width %
     - exceeded: accent-red width %
   - Create budget modal với Input + Button primary.
   - Delete với confirm CalloutBanner.

### Validation
- CRUD budget E2E test pass.

---

## Task 8.10 — Chat (1 ngày)

### Steps
1. Redesign `app/chat/chat-client.tsx`:
   - Header với display-lg title + mascot.
   - Messages area scrollable, max-w-2xl centered.
   - User bubble: bg-ink text-on-dark rounded-lg.
   - Assistant bubble: bg-surface-card border-hairline rounded-lg.
   - Streaming cursor: dot pulse với mute color.
2. Tách `MessageBubble.tsx` component.
3. Tách `SuggestedQuestions.tsx` dùng PillTab.
4. Tách `ChatInput.tsx` sticky bottom.
5. Empty state: mascot 💬 + welcoming copy.

### Validation
- Chat E2E: gõ → streaming → response hiển thị đúng.

---

## Task 8.11 — Responsive polish (1 ngày)

### Steps
1. Test mỗi page ở 375px (mobile), 768px (tablet), 1280px (desktop).
2. Fix layouts gãy.
3. Test touch targets ≥ 40px.
4. Mobile nav drawer smooth.
5. Hero typography scale.

### Validation
- Chrome DevTools device emulation pass.
- Real device test iOS/Android Chrome.

---

## Task 8.12 — Accessibility audit (0.5 ngày)

### Steps
1. Lighthouse audit mỗi page.
2. Fix color contrast issues (nếu có).
3. Add missing `aria-label` cho icon buttons.
4. Keyboard navigation test: Tab qua form, Enter submit.
5. Focus ring visible mọi interactive element.

### Validation
- Lighthouse Accessibility ≥ 90 mỗi page.
- Manual keyboard test pass.

---

## Task 8.13 — Documentation (0.5 ngày)

### Steps
1. Update `README.md` với screenshot homepage mới.
2. Update `progress_log.md` entry Phase 8 complete.
3. Save screenshots before/after mỗi page vào `docs/ui-migration/`.
4. Update `project_map.md` với `components/ui/` và `components/layout/` structure.

---

## Total estimate
**10-12 ngày làm việc**

## Risk mitigation
- Nếu thời gian không đủ: ưu tiên 8.1-8.3 (foundation) + 8.6 (dashboard) + 8.10 (chat). Auth/receipts có thể giữ style cũ tạm.
- Nếu IBM Plex Sans có vấn đề: fallback Inter.
