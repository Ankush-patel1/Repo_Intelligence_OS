# Repo Intelligence OS — UI Screens

## Shared Layout

- **Left sidebar**: Navigation with icons — Dashboard, Analyze, History, Reports, Settings. Active state highlighted. Collapsible on smaller screens.
- **Top bar**: User avatar + name, GitHub connection status, logout button.
- **Main content area**: Responsive grid, max-width 1400px centered.
- **Theme**: Light mode default, dark mode toggle in Settings. Consistent spacing scale (4px base).

---

## 1. Dashboard

**Purpose**: Home screen showing an overview of the user's analysis activity and repo health.

**Sections**:

- **Welcome banner**: Greeting + quick-start CTA ("Analyze your first repository" if no analyses exist).
- **Stats cards** (horizontal row of 3–4 cards):
  - Total analyses
  - Completed reports
  - Repositories tracked
  - Average quality score (across all reports)
- **Recent analyses** (list, last 5): Repository name, status badge (color-coded), date, duration. Click navigates to report.
- **Recent reports** (list, last 5): Title, repository, score summary (radar or bar chart miniature), date. Click navigates to full report.
- **Quick analyze**: Dropdown to select a repo + "Analyze" button.

**States**:
- **Empty**: Illustration + "No analyses yet. Get started by analyzing your first repository." + CTA button.
- **Loading**: Skeleton cards and list rows.
- **Error**: Inline error banner with retry button.

---

## 2. Analyze Repository

**Purpose**: Trigger a new analysis on a GitHub repository.

**Sections**:

- **Step 1: Select repository**
  - Search input with autocomplete (searches user's synced repos).
  - "Sync repositories" button to refresh from GitHub.
  - Repository list with avatar, name, description, language badge, and last analysis date.
- **Step 2: Configure analysis**
  - Branch selector (default: default branch).
  - Depth toggle: "Full" / "Quick scan" (shallow).
  - (Optional) File/folder exclusion patterns.
- **Step 3: Review & launch**
  - Summary card: repo name, branch, depth, estimated time.
  - "Start Analysis" button (primary).
- **Analysis progress** (after launch):
  - Animated progress bar.
  - Agent checklist: list of all agents with status icons (pending → spinner → checkmark → cross).
  - Current agent name and description.
  - Estimated time remaining.
  - "Cancel" button (if still in progress).
  - On completion: "View Report" button (links to report).

**States**:
- **No repos synced**: "Connect your GitHub account to get started." + sync button.
- **Search empty**: "No repositories match your search."
- **Analysis in progress**: Progress view replaces configuration view.
- **Analysis failed**: Error state with error message + "Retry" button.

---

## 3. History

**Purpose**: Browse and manage all past analyses.

**Sections**:

- **Search & filters** (horizontal bar):
  - Search input (by repo name).
  - Status filter dropdown (All, Pending, In Progress, Completed, Failed).
  - Date range picker.
  - Sort by (Date, Repository, Status).
- **Analysis list** (table or card list):
  - Repository name + avatar.
  - Status badge (color-coded).
  - Date and time.
  - Duration.
  - Actions: View Report, View Details, Delete.
- **Bulk actions**: Select multiple → Delete selected (with confirmation dialog).

**States**:
- **Empty**: "No analyses found. Try adjusting your filters or analyze a repository."
- **Loading**: Skeleton table rows.
- **Delete confirmation**: Modal dialog: "Are you sure? This will permanently delete the analysis and its report."

---

## 4. Reports

**Purpose**: View a specific analysis report with all sections.

**Sections**:

- **Report header**:
  - Repository name + avatar + link to GitHub.
  - Analysis date, duration, commit SHA.
  - Overall score (0–10) displayed as a large number.
  - Action buttons: Export (Markdown / JSON), Share (future), Re-analyze.
- **Executive summary** (hero section):
  - 2–3 paragraph AI-generated summary.
  - Key metrics strip: Files analyzed, lines of code, languages, total findings.
- **Section navigation** (sticky sidebar or tabs):
  - Repository Overview
  - Architecture Analysis
  - Feature Inventory
  - Security Audit
  - Performance Review
  - Documentation Review
  - Testing Review
  - Gap Analysis
  - Roadmap
  - Sprint Plan
- **Section content**:
  - Each section has a score badge (0–10).
  - Findings listed with severity badge, title, expandable description.
  - Expandable finding detail: location, evidence snippet, recommendation.
  - Roadmap section: timeline view with phases and sprint items.
- **Export flow**: Click Export → Choose format → Download.

**States**:
- **Loading**: Skeleton layout matching the section structure.
- **No report**: "This analysis does not have a report yet." (should not occur for completed analyses).
- **Error loading section**: Inline error with retry.

---

## 5. Settings

**Purpose**: Manage user account, preferences, and integrations.

**Sections**:

- **Profile**:
  - Avatar, GitHub username, name, email (read-only, synced from GitHub).
  - "Sync from GitHub" button.
- **Preferences**:
  - Theme toggle: Light / Dark / System.
  - Language (future: report language preference).
  - Notification preferences: Email on analysis complete (toggle).
- **GitHub integration**:
  - Connection status (Connected / Disconnected).
  - "Reconnect" or "Disconnect" button.
  - Last synced timestamp.
  - "Sync repositories now" button.
- **Danger zone**:
  - "Delete Account" button with confirmation flow (type account name to confirm).
- **About**:
  - App version.
  - Terms of service link.
  - Privacy policy link.
  - Feedback link.

**States**:
- **Loading**: Skeleton form fields.
- **Saved confirmation**: Inline toast: "Preferences saved."
- **Disconnect confirmation**: Modal: "Are you sure? You will need to re-authorize to analyze repos."
- **Delete confirmation**: Multi-step modal: "Type DELETE to confirm" → "This action is irreversible" → Confirm button.
