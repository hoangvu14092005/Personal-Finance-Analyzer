import { apiBaseUrl } from "@/lib/config";

type AuthUser = {
  id: number;
  email: string;
  full_name: string | null;
  currency: string;
  timezone: string;
  locale: string;
};

type AuthResponse = {
  user: AuthUser;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        errorMessage = body.detail;
      }
    } catch {
      // Ignore JSON parsing errors and keep generic message.
    }
    throw new Error(errorMessage);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
  currency?: string;
  timezone?: string;
  locale?: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout(): Promise<void> {
  await request<void>("/api/v1/auth/logout", {
    method: "POST",
  });
}

export async function getMe(): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/me", {
    method: "GET",
  });
}
