export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
  meta: {
    request_id: string;
    timestamp: string;
  };
}
