import { apiBaseUrl } from "@/lib/config";

export type Category = {
  id: number;
  name: string;
  color: string | null;
  is_system: boolean;
  user_id: number | null;
  created_at: string;
};

export type CategoryListResponse = {
  items: Category[];
};

export async function listCategories(): Promise<CategoryListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/categories`, {
    method: "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // Non-JSON body — keep generic message.
    }
    throw new Error(detail);
  }

  return (await response.json()) as CategoryListResponse;
}
