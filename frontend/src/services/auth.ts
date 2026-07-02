import { apiGet } from "./api";
import type { HealthResponse } from "@/types/api";

export async function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}
