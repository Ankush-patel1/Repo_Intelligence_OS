# Repo Intelligence OS — API Design

## Base URL

`/api/v1`

## Authentication

All endpoints except `/auth/*` require a Bearer JWT token in the `Authorization` header.

```
Authorization: Bearer <token>
```

## Standard Response Envelope

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-02T12:00:00Z"
  }
}
```

## Standard Error Envelope

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Analysis not found",
    "details": { "analysis_id": "uuid" }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-07-02T12:00:00Z"
  }
}
```

## Pagination

List endpoints accept `?page=1&per_page=20` (default: page=1, per_page=20, max per_page=100).

```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

## Authentication

### `GET /api/v1/auth/github`

Redirect user to GitHub OAuth authorization URL.

**Response**: `302 Redirect` to `https://github.com/login/oauth/authorize?client_id=...`

### `GET /api/v1/auth/github/callback`

GitHub OAuth callback. Exchanges code for tokens.

**Query params**: `code`, `state`

**Response**: `{ access_token, token_type, expires_in, user }` | Sets HTTP-only cookie with refresh token.

### `POST /api/v1/auth/refresh`

Refresh an expired access token.

**Request body**: `{ refresh_token }`

**Response**: `{ access_token, expires_in }`

### `POST /api/v1/auth/logout`

Invalidate current session.

**Response**: `204 No Content`

---

## Users

### `GET /api/v1/users/me`

Get current user profile.

**Response**: `{ id, github_login, github_name, github_avatar_url, github_email, role, preferences, created_at }`

### `PATCH /api/v1/users/me`

Update user preferences.

**Request body** (partial):
```json
{
  "preferences": {
    "theme": "dark",
    "notifications_enabled": false
  }
}
```

**Response**: Updated user object.

### `DELETE /api/v1/users/me`

Delete user account and all associated data.

**Response**: `204 No Content`

---

## Repositories

### `GET /api/v1/repositories`

List user's repositories.

**Query params**: `page`, `per_page`, `search` (full_name contains), `language`, `sort` (name | created_at | updated_at, default: updated_at), `order` (asc | desc)

**Response**: Paginated list of `{ id, full_name, owner, name, language, description, is_private, default_branch, last_analyzed_at, created_at }`

### `GET /api/v1/repositories/sync`

Synchronize repositories from GitHub (fetch user's repos and insert missing ones).

**Response**: `{ synced: 5, total: 12 }`

### `GET /api/v1/repositories/{id}`

Get repository details.

**Response**: Full repository object with analysis count.

### `DELETE /api/v1/repositories/{id}`

Remove repository (and all associated analyses, reports). Soft delete.

**Response**: `204 No Content`

---

## Analyses

### `POST /api/v1/analyses`

Trigger a new analysis.

**Request body**:
```json
{
  "repository_id": "uuid",
  "branch": "main",
  "depth": "full"
}
```

**Response**: `201 Created` — `{ id, status: "pending", repository_id, branch, depth, created_at }`

### `GET /api/v1/analyses`

List user's analyses.

**Query params**: `page`, `per_page`, `status` (pending | in_progress | completed | failed), `repository_id`, `sort` (created_at | completed_at, default: created_at), `order` (asc | desc)

**Response**: Paginated list of `{ id, status, repository { full_name }, branch, depth, started_at, completed_at, duration_seconds, error_message }`

### `GET /api/v1/analyses/{id}`

Get analysis details.

**Response**: Full analysis object including status, progress (agent completion), duration, error details if failed.

### `GET /api/v1/analyses/{id}/status`

Lightweight status check (for polling).

**Response**: `{ id, status, started_at, completed_at, progress: { completed_agents: 3, total_agents: 8, current_agent: "Security Agent" } }`

### `POST /api/v1/analyses/{id}/cancel`

Cancel a running analysis.

**Response**: `{ id, status: "cancelled" }`

### `DELETE /api/v1/analyses/{id}`

Delete an analysis and its associated findings, report, and file index. Soft delete.

**Response**: `204 No Content`

---

## Findings

### `GET /api/v1/analyses/{analysis_id}/findings`

List findings for an analysis.

**Query params**: `page`, `per_page`, `agent_name`, `severity` (critical | high | medium | low | info), `finding_type`, `sort` (severity | created_at, default: severity desc)

**Response**: Paginated list of `{ id, agent_name, finding_type, severity, confidence, title, description, location, evidence, recommendation, is_validated }`

### `GET /api/v1/analyses/{analysis_id}/findings/{id}`

Get single finding with full detail.

**Response**: Full finding object.

---

## Reports

### `GET /api/v1/reports`

List user's reports.

**Query params**: `page`, `per_page`, `repository_id`, `sort` (created_at, default: created_at desc)

**Response**: Paginated list of `{ id, title, summary, repository { full_name }, version, scores, created_at }`

### `GET /api/v1/reports/{id}`

Get full report.

**Response**: Full report object with all sections, scores, and metadata.

### `GET /api/v1/reports/{id}/sections/{section_slug}`

Get a single section of a report.

**Section slugs**: `executive_summary`, `repository_overview`, `architecture_analysis`, `feature_inventory`, `security_audit`, `performance_review`, `documentation_review`, `testing_review`, `gap_analysis`, `roadmap`, `sprint_plan`

**Response**: `{ slug, title, content, score }`

### `GET /api/v1/reports/{id}/export`

Export report as markdown.

**Query params**: `format` (md | json, default: md)

**Response**: `200` with `Content-Type: text/markdown` or `application/json`.

---

## Roadmap Items

### `GET /api/v1/reports/{report_id}/roadmap`

Get roadmap items for a report.

**Query params**: `page`, `per_page`, `priority`, `phase`, `category`, `sort` (sort_order | priority, default: sort_order)

**Response**: Paginated list of `{ id, title, description, priority, effort, phase, sprint, category, sort_order, finding_id }`

---

## Health

### `GET /api/v1/health`

Health check endpoint. Does not require authentication.

**Response**: `{ status: "ok", version: "1.0.0", uptime_seconds: 12345 }`

---

## Status Codes

| Code | Usage |
|---|---|
| 200 | Success |
| 201 | Created (analyses, resources) |
| 204 | No content (delete operations) |
| 302 | Redirect (OAuth) |
| 400 | Bad request (validation error) |
| 401 | Unauthenticated (missing / invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable entity (business rule violation) |
| 429 | Too many requests (rate limit) |
| 500 | Internal server error |
| 502 | Upstream error (GitHub, LLM provider) |
| 503 | Service unavailable (queue full, maintenance) |
