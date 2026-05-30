import { apiRequest } from "@/lib/api-client";

export type UserProfile = {
  id: number;
  email: string;
  full_name: string | null;
  currency: string;
  timezone: string;
  locale: string;
  is_active: boolean;
  created_at: string;
};

export type FinanceSettings = {
  default_currency: string;
  timezone: string;
  locale: string;
  default_analytics_range: "7d" | "30d" | "this_month" | "last_month";
  budget_month_start_day: number;
  number_format_locale: string;
  show_decimals: boolean;
  updated_at: string;
};

export type AISettings = {
  allow_ai_data_processing: boolean;
  auto_generate_insights: boolean;
  assistant_use_history: boolean;
  updated_at: string;
};

export type NotificationSettings = {
  email_notifications_enabled: boolean;
  push_notifications_enabled: boolean;
  budget_alerts_enabled: boolean;
  receipt_notifications_enabled: boolean;
  insight_notifications_enabled: boolean;
  updated_at: string;
};

export type PrivacySettings = {
  receipt_file_retention_days: number;
  raw_prompt_retention_days: number;
  updated_at: string;
};

export type SettingsBundle = {
  profile: UserProfile;
  finance: FinanceSettings;
  ai: AISettings;
  notifications: NotificationSettings;
  privacy: PrivacySettings;
};

export function getUserProfile() {
  return apiRequest<UserProfile>("/api/v1/users/me");
}

export function updateUserProfile(payload: Partial<Pick<UserProfile, "full_name" | "currency" | "timezone" | "locale">>) {
  return apiRequest<UserProfile>("/api/v1/users/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getFinanceSettings() {
  return apiRequest<FinanceSettings>("/api/v1/settings/finance");
}

export function updateFinanceSettings(payload: Partial<Omit<FinanceSettings, "updated_at">>) {
  return apiRequest<FinanceSettings>("/api/v1/settings/finance", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAISettings() {
  return apiRequest<AISettings>("/api/v1/settings/ai");
}

export function updateAISettings(payload: Partial<Omit<AISettings, "updated_at">>) {
  return apiRequest<AISettings>("/api/v1/settings/ai", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getNotificationSettings() {
  return apiRequest<NotificationSettings>("/api/v1/settings/notifications");
}

export function updateNotificationSettings(payload: Partial<Omit<NotificationSettings, "updated_at">>) {
  return apiRequest<NotificationSettings>("/api/v1/settings/notifications", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getPrivacySettings() {
  return apiRequest<PrivacySettings>("/api/v1/settings/privacy");
}

export function updatePrivacySettings(payload: Partial<Omit<PrivacySettings, "updated_at">>) {
  return apiRequest<PrivacySettings>("/api/v1/settings/privacy", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getSettingsBundle(): Promise<SettingsBundle> {
  const [profile, finance, ai, notifications, privacy] = await Promise.all([
    getUserProfile(),
    getFinanceSettings(),
    getAISettings(),
    getNotificationSettings(),
    getPrivacySettings(),
  ]);
  return { profile, finance, ai, notifications, privacy };
}
