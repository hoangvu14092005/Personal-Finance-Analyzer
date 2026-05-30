"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle,
  Coins,
  Cpu,
  Download,
  History,
  RefreshCw,
  Save,
  ShieldAlert,
  Sliders,
  User,
  type LucideIcon,
} from "lucide-react";

import { getMe } from "@/lib/auth-api";
import {
  BillingPlan,
  BillingUsage,
  LoginHistoryItem,
  SecuritySession,
  AuditLogItem,
  createDataExport,
  getBillingPlan,
  getBillingUsage,
  listAuditLog,
  listLoginHistory,
  listSecuritySessions,
  revokeCurrentSession,
} from "@/lib/account-api";
import {
  SettingsBundle,
  getSettingsBundle,
  updateAISettings,
  updateFinanceSettings,
  updateNotificationSettings,
  updatePrivacySettings,
  updateUserProfile,
} from "@/lib/settings-api";
import { Badge, Button, Card, Input } from "@/components/ui";

type FormState = {
  fullName: string;
  currency: string;
  timezone: string;
  locale: string;
  analyticsRange: "7d" | "30d" | "this_month" | "last_month";
  monthStartDay: number;
  showDecimals: boolean;
  allowAI: boolean;
  autoInsights: boolean;
  assistantHistory: boolean;
  emailNotifications: boolean;
  pushNotifications: boolean;
  budgetAlerts: boolean;
  receiptNotifications: boolean;
  insightNotifications: boolean;
  receiptRetention: number;
  promptRetention: number;
};

type OpsState = {
  sessions: SecuritySession[];
  loginHistory: LoginHistoryItem[];
  billingPlan: BillingPlan | null;
  billingUsage: BillingUsage | null;
  audit: AuditLogItem[];
};

function formFromBundle(bundle: SettingsBundle): FormState {
  return {
    fullName: bundle.profile.full_name ?? "",
    currency: bundle.finance.default_currency,
    timezone: bundle.finance.timezone,
    locale: bundle.finance.locale,
    analyticsRange: bundle.finance.default_analytics_range,
    monthStartDay: bundle.finance.budget_month_start_day,
    showDecimals: bundle.finance.show_decimals,
    allowAI: bundle.ai.allow_ai_data_processing,
    autoInsights: bundle.ai.auto_generate_insights,
    assistantHistory: bundle.ai.assistant_use_history,
    emailNotifications: bundle.notifications.email_notifications_enabled,
    pushNotifications: bundle.notifications.push_notifications_enabled,
    budgetAlerts: bundle.notifications.budget_alerts_enabled,
    receiptNotifications: bundle.notifications.receipt_notifications_enabled,
    insightNotifications: bundle.notifications.insight_notifications_enabled,
    receiptRetention: bundle.privacy.receipt_file_retention_days,
    promptRetention: bundle.privacy.raw_prompt_retention_days,
  };
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("vi-VN");
}

function Toggle({ checked, onChange, label, help }: { checked: boolean; onChange: (value: boolean) => void; label: string; help: string }) {
  return (
    <label className="flex items-start gap-3 rounded-md border border-hairline-soft p-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-4 w-4 accent-accent-green"
      />
      <span>
        <span className="block text-caption-md text-ink">{label}</span>
        <span className="block text-caption-sm text-mute">{help}</span>
      </span>
    </label>
  );
}

export default function SettingsClient() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [bundle, setBundle] = useState<SettingsBundle | null>(null);
  const [ops, setOps] = useState<OpsState>({ sessions: [], loginHistory: [], billingPlan: null, billingUsage: null, audit: [] });
  const [form, setForm] = useState<FormState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await getMe();
        if (!cancelled) setAuthReady(true);
      } catch {
        router.replace("/login?next=/settings");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsBundle, sessions, loginHistory, billingPlan, billingUsage, audit] = await Promise.all([
        getSettingsBundle(),
        listSecuritySessions(),
        listLoginHistory(),
        getBillingPlan(),
        getBillingUsage(),
        listAuditLog(12),
      ]);
      setBundle(settingsBundle);
      setForm(formFromBundle(settingsBundle));
      setOps({
        sessions: sessions.items,
        loginHistory: loginHistory.items,
        billingPlan,
        billingUsage,
        audit: audit.items,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải cài đặt");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authReady) void load();
  }, [authReady, load]);

  const billingUsageLines = useMemo(() => {
    const usage = ops.billingUsage;
    if (!usage) return [];
    return [
      ["Giao dịch", usage.transaction_count],
      ["Hóa đơn", usage.receipt_count],
      ["Hóa đơn VAT", usage.invoice_count],
      ["Insights", usage.insight_count],
    ] as const;
  }, [ops.billingUsage]);

  const opsSummary = useMemo(() => ({
    sessions: ops.sessions.length,
    loginEvents: ops.loginHistory.length,
    auditEvents: ops.audit.length,
    plan: ops.billingPlan?.name ?? "Free",
  }), [ops]);

  const saveSettings = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await Promise.all([
        updateUserProfile({
          full_name: form.fullName || null,
          currency: form.currency,
          timezone: form.timezone,
          locale: form.locale,
        }),
        updateFinanceSettings({
          default_currency: form.currency,
          timezone: form.timezone,
          locale: form.locale,
          number_format_locale: form.locale,
          default_analytics_range: form.analyticsRange,
          budget_month_start_day: form.monthStartDay,
          show_decimals: form.showDecimals,
        }),
        updateAISettings({
          allow_ai_data_processing: form.allowAI,
          auto_generate_insights: form.autoInsights,
          assistant_use_history: form.assistantHistory,
        }),
        updateNotificationSettings({
          email_notifications_enabled: form.emailNotifications,
          push_notifications_enabled: form.pushNotifications,
          budget_alerts_enabled: form.budgetAlerts,
          receipt_notifications_enabled: form.receiptNotifications,
          insight_notifications_enabled: form.insightNotifications,
        }),
        updatePrivacySettings({
          receipt_file_retention_days: form.receiptRetention,
          raw_prompt_retention_days: form.promptRetention,
        }),
      ]);
      setNotice("Đã lưu cài đặt và ghi audit log.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể lưu cài đặt");
    } finally {
      setSaving(false);
    }
  };

  const requestExport = async () => {
    setError(null);
    setNotice(null);
    try {
      const response = await createDataExport();
      setNotice(response.message ?? `Export ${response.export_id} đã sẵn sàng.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tạo export");
    }
  };

  const revokeSession = async () => {
    if (!confirm("Đăng xuất phiên hiện tại?")) return;
    try {
      await revokeCurrentSession();
      router.replace("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể thu hồi phiên");
    }
  };

  if (!authReady) return <p className="text-body-sm text-mute">Đang kiểm tra phiên đăng nhập...</p>;
  if (loading || !form || !bundle) return <Card>Đang tải cài đặt...</Card>;

  return (
    <form onSubmit={saveSettings} className="space-y-6">
      <header className="space-y-4">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-xl font-bold tracking-tight text-ink">Cài Đặt Hệ Thống</h1>
            <p className="mt-0.5 text-sm text-ash">
              Cá nhân hóa tài khoản, điều chỉnh ngưỡng cảnh báo ngân sách và cấu hình công nghệ OCR.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => void load()}><RefreshCw className="h-4 w-4" aria-hidden />Làm mới</Button>
            <Button type="submit" disabled={saving}><Save className="h-4 w-4" aria-hidden />{saving ? "Đang lưu..." : "Lưu cài đặt"}</Button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SettingsStat icon={Coins} label="Gói hiện tại" value={opsSummary.plan} detail="Gói sử dụng hiện tại" tone="neutral" />
          <SettingsStat icon={ShieldAlert} label="Phiên đăng nhập" value={String(opsSummary.sessions)} detail="Thiết bị đang hoạt động" tone="green" />
          <SettingsStat icon={History} label="Lần đăng nhập" value={String(opsSummary.loginEvents)} detail="Lịch sử gần đây" tone="blue" />
          <SettingsStat icon={CheckCircle} label="Nhật ký hệ thống" value={String(opsSummary.auditEvents)} detail="Sự kiện đã ghi nhận" tone="purple" />
        </div>
      </header>

      {notice && <div className="rounded-md border border-accent-green bg-accent-green-soft p-3 text-body-sm text-accent-green">{notice}</div>}
      {error && <div className="rounded-md border border-accent-red bg-accent-red-soft p-3 text-body-sm text-accent-red">{error}</div>}

      <div className="grid gap-4 lg:grid-cols-12">
        <section className="space-y-4 lg:col-span-8">
          <Card className="space-y-4 border-hairline-soft bg-surface-card">
            <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
              <User className="h-4.5 w-4.5 text-mute" aria-hidden />
              Cá nhân hóa tài khoản
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Tên hiển thị</span>
                <Input value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} />
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Email</span>
                <Input value={bundle.profile.email} disabled />
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Tiền tệ</span>
                <select value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value })} className="h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink">
                  <option value="VND">VND</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Khoảng analytics mặc định</span>
                <select value={form.analyticsRange} onChange={(event) => setForm({ ...form, analyticsRange: event.target.value as FormState["analyticsRange"] })} className="h-9 w-full rounded-md border border-hairline bg-surface-card px-3 text-body-md text-ink">
                  <option value="7d">7 ngày</option>
                  <option value="30d">30 ngày</option>
                  <option value="this_month">Tháng này</option>
                  <option value="last_month">Tháng trước</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Timezone</span>
                <Input value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} />
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Locale</span>
                <Input value={form.locale} onChange={(event) => setForm({ ...form, locale: event.target.value })} />
              </label>
            </div>
          </Card>

          <Card className="space-y-4 border-hairline-soft bg-surface-card">
            <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
              <Sliders className="h-4.5 w-4.5 text-mute" aria-hidden />
              Định mức & Ngưỡng kiểm soát
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              <Toggle checked={form.allowAI} onChange={(value) => setForm({ ...form, allowAI: value })} label="Cho phép AI xử lý dữ liệu" help="Bật để assistant và insights dùng dữ liệu của bạn." />
              <Toggle checked={form.autoInsights} onChange={(value) => setForm({ ...form, autoInsights: value })} label="Tự tạo insight" help="Sinh cảnh báo định kỳ từ transactions." />
              <Toggle checked={form.assistantHistory} onChange={(value) => setForm({ ...form, assistantHistory: value })} label="Assistant dùng lịch sử" help="Cho phép bot tham chiếu hội thoại trước." />
              <Toggle checked={form.emailNotifications} onChange={(value) => setForm({ ...form, emailNotifications: value })} label="Thông báo qua email" help="Nhận thông báo quan trọng qua email." />
              <Toggle checked={form.budgetAlerts} onChange={(value) => setForm({ ...form, budgetAlerts: value })} label="Cảnh báo ngân sách" help="Cảnh báo khi ngân sách chạm ngưỡng." />
              <Toggle checked={form.receiptNotifications} onChange={(value) => setForm({ ...form, receiptNotifications: value })} label="Cập nhật hóa đơn" help="Thông báo khi OCR hoàn tất hoặc lỗi." />
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Ngày bắt đầu tháng ngân sách</span>
                <Input type="number" min={1} max={28} value={form.monthStartDay} onChange={(event) => setForm({ ...form, monthStartDay: Number(event.target.value) })} />
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Giữ file receipt</span>
                <Input type="number" min={1} max={3650} value={form.receiptRetention} onChange={(event) => setForm({ ...form, receiptRetention: Number(event.target.value) })} />
              </label>
              <label className="space-y-1">
                <span className="text-caption-xs text-mute">Giữ raw prompt</span>
                <Input type="number" min={1} max={3650} value={form.promptRetention} onChange={(event) => setForm({ ...form, promptRetention: Number(event.target.value) })} />
              </label>
            </div>
          </Card>
        </section>

        <aside className="space-y-4 lg:col-span-4">
          <Card className="space-y-4 border-hairline-soft bg-surface-card">
            <div className="flex items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
                <Coins className="h-4.5 w-4.5 text-mute" aria-hidden />
                Gói sử dụng
              </h2>
              <Badge tone="neutral">{ops.billingPlan?.status ?? "local"}</Badge>
            </div>
            <p className="text-body-sm text-body">{ops.billingPlan?.name ?? "Free"} · {ops.billingPlan?.monthly_price ?? "0"} {ops.billingPlan?.currency ?? "VND"}/tháng</p>
            <div className="grid grid-cols-2 gap-2">
              {billingUsageLines.map(([label, value]) => (
                <div key={label} className="rounded-md border border-hairline-soft p-3">
                  <p className="text-caption-xs text-mute">{label}</p>
                  <p className="text-heading-sm-mixed text-ink">{value}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="space-y-3 border-hairline-soft bg-surface-card">
            <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
              <ShieldAlert className="h-4.5 w-4.5 text-mute" aria-hidden />
              Bảo mật
            </h2>
            {ops.sessions.map((session) => (
              <div key={session.id} className="rounded-md border border-hairline-soft p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-caption-md text-ink">{session.email}</span>
                  <Badge tone="green">current</Badge>
                </div>
                <p className="mt-1 text-caption-sm text-mute">Tạo lúc {formatDateTime(session.created_at)}</p>
              </div>
            ))}
            <Button type="button" variant="danger" size="sm" onClick={() => void revokeSession()}>Đăng xuất phiên này</Button>
          </Card>

          <Card className="space-y-3 border-hairline-soft bg-surface-card">
            <div className="flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
                <Download className="h-4.5 w-4.5 text-mute" aria-hidden />
                Xuất dữ liệu
              </h2>
              <Button type="button" variant="secondary" size="sm" onClick={() => void requestExport()}>Tạo export</Button>
            </div>
            <p className="text-caption-sm text-mute">Export hiện là contract MVP, trả trạng thái và message từ backend.</p>
          </Card>
        </aside>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3 border-hairline-soft bg-surface-card">
          <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
            <History className="h-4.5 w-4.5 text-mute" aria-hidden />
            Lịch sử đăng nhập
          </h2>
          {ops.loginHistory.map((item) => (
            <div key={item.id} className="flex justify-between gap-3 border-b border-hairline-soft pb-2 text-caption-sm last:border-0">
              <span className="text-ink">{item.event}</span>
              <span className="text-mute">{formatDateTime(item.occurred_at)}</span>
            </div>
          ))}
          {ops.loginHistory.length === 0 && <p className="text-body-sm text-mute">Chưa có lịch sử đăng nhập.</p>}
        </Card>

        <Card className="space-y-3 border-hairline-soft bg-surface-card">
          <h2 className="flex items-center gap-2 text-heading-sm-mixed text-ink">
            <Cpu className="h-4.5 w-4.5 text-mute" aria-hidden />
            Audit log gần đây
          </h2>
          {ops.audit.map((item) => (
            <div key={item.id} className="border-b border-hairline-soft pb-2 last:border-0">
              <div className="flex justify-between gap-3 text-caption-sm">
                <span className="font-semibold text-ink">{item.event}</span>
                <span className="text-mute">{formatDateTime(item.occurred_at)}</span>
              </div>
              <p className="text-caption-sm text-mute">{item.target_type ?? "system"}{item.target_id ? ` #${item.target_id}` : ""}</p>
            </div>
          ))}
          {ops.audit.length === 0 && <p className="text-body-sm text-mute">Chưa có audit event.</p>}
        </Card>
      </section>
    </form>
  );
}

function SettingsStat({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: "neutral" | "green" | "blue" | "purple" }) {
  const toneClass = {
    neutral: "bg-surface-doc text-ink",
    green: "bg-accent-green-soft text-accent-green",
    blue: "bg-accent-blue-soft text-link-blue",
    purple: "bg-accent-purple-soft text-accent-purple",
  }[tone];
  return (
    <article className="rounded-xl border border-hairline-soft bg-surface-doc p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-caption-xs font-bold uppercase tracking-wide text-mute">{label}</p>
          <p className="mt-2 truncate text-xl font-black text-ink">{value}</p>
        </div>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-4.5 w-4.5" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-caption-sm text-mute">{detail}</p>
    </article>
  );
}
