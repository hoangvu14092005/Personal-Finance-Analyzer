# Phase 8 - UI Redesign theo DESIGN.md

## Mục tiêu
Redesign toàn bộ UI frontend theo design system PostHog-style (DESIGN.md):
- White canvas (#ffffff) end-to-end
- Single yellow CTA (#f7a501) cho primary actions
- IBM Plex Sans typography
- Card với hairline borders (không drop-shadow)
- Callout banners pastel (blue/green/red/purple)
- Emoji mascots làm brand decoration

## Scope
- Đổi visual identity, không đổi functionality
- Page-by-page migration, không big-bang
- Giữ backend API, routes, data flow nguyên

## Out of scope
- Thay đổi backend
- Thêm tính năng mới
- Custom hedgehog illustrations (emoji placeholder OK)

## Task breakdown (chi tiết .kiro/specs/ui-redesign/tasks.md)

1. Design tokens foundation (Tailwind config + IBM Plex Sans)
2. Primitive components (Button, Card, Input, Badge, PillTab, CalloutBanner, v.v.)
3. Layout chrome: Nav + Footer + MobileDrawer
4. Landing page
5. Auth pages (login, register)
6. Dashboard
7. Transactions (list, new)
8. Receipts (upload, review)
9. Budgets
10. Chat UI
11. Responsive polish
12. Accessibility audit
13. Documentation

## Exit criteria
- Tất cả pages match DESIGN.md spec
- Typography consistent IBM Plex Sans
- Primary CTA dùng yellow #f7a501 nhất quán
- Canvas white #ffffff mọi page
- Cards flat với hairline, không shadow
- Responsive mobile/tablet/desktop
- Lighthouse accessibility ≥ 90
- E2E tests pass

## Ước tính
10-12 ngày làm việc.
