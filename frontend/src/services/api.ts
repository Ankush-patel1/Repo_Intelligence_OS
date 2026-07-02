const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const error: ApiError = {
      code: errorBody?.error?.code ?? "unknown_error",
      message: errorBody?.error?.message ?? "An unexpected error occurred",
      details: errorBody?.error?.details ?? {},
    };
    throw error;
  }

  return response.json() as Promise<T>;
}

export function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: "GET" });
}
