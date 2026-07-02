export interface User {
  id: string;
  github_login: string;
  github_name: string | null;
  github_avatar_url: string | null;
  github_email: string | null;
  role: string;
  created_at: string;
}

export interface Repository {
  id: string;
  full_name: string;
  name: string;
  owner: string;
  language: string | null;
  description: string | null;
  is_private: boolean;
  default_branch: string;
  last_analyzed_at: string | null;
  created_at: string;
}

export interface Analysis {
  id: string;
  repository_id: string;
  status: AnalysisStatus;
  branch: string;
  depth: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
}

export type AnalysisStatus = "pending" | "in_progress" | "completed" | "failed" | "cancelled";

export interface Finding {
  id: string;
  analysis_id: string;
  agent_name: string;
  finding_type: string;
  severity: FindingSeverity;
  confidence: number;
  title: string;
  description: string;
  location: FindingLocation | null;
  evidence: string | null;
  recommendation: string | null;
  is_validated: boolean;
  created_at: string;
}

export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface FindingLocation {
  file_path: string;
  line_start: number;
  line_end: number;
}
