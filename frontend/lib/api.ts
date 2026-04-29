// ════════════════════════════════════════════════════════════════
// AI CFO — API Client
// Centralized API calls aligned with backend router structure.
// ════════════════════════════════════════════════════════════════

import type {
  User,
  DashboardSummary,
  Transaction,
  PaginatedTransactions,
  TransactionCreate,
  Budget,
  BudgetCreate,
  Goal,
  GoalCreate,
  GoalUpdate,
  Alert,
  ForecastResponse,
  ChatRequest,
  ChatResponse,
  ChatSession,
  ScanResult,
  HealthScoreResponse,
  ReportSummary,
  AffordabilityRequest,
  AffordabilityResponse,
  PaginatedAuditLogs,
  BenchmarkInsight,
  Workspace,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Global Token Provider ────────────────────────────────────────
// Clerk v7 does NOT reliably expose window.Clerk.session.getToken().
// Instead, the auth-aware layout calls setTokenProvider() once with
// useAuth().getToken, and fetchApi uses it as a fallback for ALL
// API calls that don't receive an explicit token.

let _tokenProvider: (() => Promise<string | null>) | null = null;

/** Call once from a Clerk-aware component to register the token getter. */
export function setTokenProvider(provider: () => Promise<string | null>) {
  _tokenProvider = provider;
}

// ── Helper ───────────────────────────────────────────────────────

async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  providedToken?: string | null
): Promise<T> {
  const url = `${API_BASE}${path}`;

  // 1) Use explicitly provided token
  // 2) Fall back to registered Clerk token provider
  let token: string | null = providedToken || null;



  if (!token && _tokenProvider) {
    try {
      token = await _tokenProvider();
    } catch (e) {
      console.error(`[fetchApi] ${path} | provider ERROR:`, e);
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }



  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    console.error(`[fetchApi] ${path} | FAILED ${response.status}: ${error.detail}`);
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}


// ── Auth ─────────────────────────────────────────────────────────

export const authApi = {
  getMe: () => fetchApi<User>("/auth/me"),
  /** @deprecated Use onboardingApi.provision() for first-time setup */
  sync: () => fetchApi<{ status: string; user_id: string; workspace_id: string }>("/auth/sync", { method: "POST" }),
};


// ── Onboarding ──────────────────────────────────────────────────

export const onboardingApi = {
  /**
   * Provision workspace + user on first login.
   * Idempotent — safe to call multiple times.
   * Frontend should call this once after Clerk sign-in.
   */
  provision: () =>
    fetchApi<{ status: string; user: User; workspace_id: string }>(
      "/onboarding/provision",
      { method: "POST" }
    ),
};


// ── Dashboard ────────────────────────────────────────────────────

export const dashboardApi = {
  getSummary: (months = 6) =>
    fetchApi<DashboardSummary>(`/dashboard/summary?months=${months}`),
};


// ── Transactions ─────────────────────────────────────────────────

export const transactionsApi = {
  list: (params?: {
    page?: number;
    per_page?: number;
    category?: string;
    type?: string;
    search?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.per_page) query.set("per_page", String(params.per_page));
    if (params?.category) query.set("category", params.category);
    if (params?.type) query.set("type", params.type);
    if (params?.search) query.set("search", params.search);
    return fetchApi<PaginatedTransactions>(`/transactions?${query}`);
  },

  create: (data: TransactionCreate) =>
    fetchApi<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/transactions/${id}`, { method: "DELETE" }),

  uploadCsv: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${API_BASE}/transactions/upload-csv`;
    let token: string | null = null;
    if (_tokenProvider) {
      try { token = await _tokenProvider(); } catch { /* ignore */ }
    }

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });
    return resp.json();
  },
};


// ── Budgets ──────────────────────────────────────────────────────

export const budgetsApi = {
  list: (month?: string) => {
    const query = month ? `?month=${month}` : "";
    return fetchApi<Budget[]>(`/budgets${query}`);
  },

  create: (data: BudgetCreate) =>
    fetchApi<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: BudgetCreate) =>
    fetchApi<Budget>(`/budgets/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/budgets/${id}`, { method: "DELETE" }),
};


// ── Goals ────────────────────────────────────────────────────────

export const goalsApi = {
  list: (status?: string) => {
    const query = status ? `?status_filter=${status}` : "";
    return fetchApi<Goal[]>(`/goals${query}`);
  },

  create: (data: GoalCreate) =>
    fetchApi<Goal>("/goals", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: GoalUpdate) =>
    fetchApi<Goal>(`/goals/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/goals/${id}`, { method: "DELETE" }),
};


// ── Alerts ───────────────────────────────────────────────────────

export const alertsApi = {
  list: (unreadOnly = false) =>
    fetchApi<Alert[]>(`/alerts?unread_only=${unreadOnly}`),

  count: () =>
    fetchApi<{ unread_count: number }>("/alerts/count"),

  markRead: (id: string) =>
    fetchApi<void>(`/alerts/${id}/read`, { method: "PUT" }),

  markAllRead: () =>
    fetchApi<void>("/alerts/read-all", { method: "PUT" }),

  dismiss: (id: string) =>
    fetchApi<void>(`/alerts/${id}/dismiss`, { method: "PUT" }),
};


// ── Chat ─────────────────────────────────────────────────────────

export const chatApi = {
  send: (data: ChatRequest) =>
    fetchApi<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sessions: () => fetchApi<ChatSession[]>("/chat/sessions"),

  history: (sessionId: string) =>
    fetchApi<{ role: string; content: string; created_at: string }[]>(
      `/chat/history?session_id=${sessionId}`
    ),
};


// ── Forecasting ──────────────────────────────────────────────────

export const forecastApi = {
  get: (monthsAhead = 6, scenario = "base") =>
    fetchApi<ForecastResponse>(
      `/forecasting/?months_ahead=${monthsAhead}&scenario=${scenario}`
    ),
};


// ── Anomaly Detection ────────────────────────────────────────────

export const anomalyApi = {
  scan: (threshold = 2.0, days = 90) =>
    fetchApi<ScanResult>(
      `/anomaly/scan?z_threshold=${threshold}&days=${days}`
    ),

  list: () => fetchApi<ScanResult["anomalies"]>("/anomaly"),
};


// ── Health Score ─────────────────────────────────────────────────

export const healthScoreApi = {
  get: () => fetchApi<HealthScoreResponse>("/health-score"),
};


// ── Reports ──────────────────────────────────────────────────────

export const reportsApi = {
  summary: (startDate?: string, endDate?: string) => {
    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    return fetchApi<ReportSummary>(`/reports/summary?${query}`);
  },

  /** Trigger a CSV file download of transactions. */
  exportCsv: async (startDate?: string, endDate?: string) => {
    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);

    const url = `${API_BASE}/reports/export/csv?${query}`;
    let token: string | null = null;
    if (_tokenProvider) {
      try { token = await _tokenProvider(); } catch { /* ignore */ }
    }

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const resp = await fetch(url, { headers });
    if (!resp.ok) throw new Error(`Export failed: ${resp.status}`);

    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = resp.headers.get("Content-Disposition")?.match(/filename="?(.+?)"?$/)?.[1]
      || `transactions_export.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  },

  /** Trigger a PDF financial report download. */
  exportPdf: async (startDate?: string, endDate?: string) => {
    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);

    const url = `${API_BASE}/reports/export/pdf?${query}`;
    let token: string | null = null;
    if (_tokenProvider) {
      try { token = await _tokenProvider(); } catch { /* ignore */ }
    }

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const resp = await fetch(url, { headers });
    if (!resp.ok) throw new Error(`Export failed: ${resp.status}`);

    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = resp.headers.get("Content-Disposition")?.match(/filename="?(.+?)"?$/)?.[1]
      || `financial_report.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  },
};


// ── Calculator ───────────────────────────────────────────────────

export const calculatorApi = {
  checkAffordability: (data: AffordabilityRequest) =>
    fetchApi<AffordabilityResponse>("/calculator/affordability", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};


// ── Audit Log ────────────────────────────────────────────────────

export const auditApi = {
  list: (params?: { page?: number; entity_type?: string; days?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.entity_type) query.set("entity_type", params.entity_type);
    if (params?.days) query.set("days", String(params.days));
    return fetchApi<PaginatedAuditLogs>(`/audit?${query}`);
  },
};


// ── Benchmarks ───────────────────────────────────────────────────

export const benchmarksApi = {
  get: () => fetchApi<BenchmarkInsight[]>("/benchmarks"),
};


// ── Settings ─────────────────────────────────────────────────────

export const settingsApi = {
  getProfile: () => fetchApi<User>("/settings/profile"),
  updateProfile: (data: { full_name?: string; avatar_url?: string }) =>
    fetchApi<User>("/settings/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  getWorkspace: () => fetchApi<Workspace>("/settings/workspace"),
  updateWorkspace: (data: { name?: string; industry?: string; currency?: string }) =>
    fetchApi<Workspace>("/settings/workspace", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  listTeam: () => fetchApi<User[]>("/settings/team"),
  getTeam: () => fetchApi<{ members: User[] }>("/settings/team"),
  inviteMember: (data: { email: string; full_name: string; role: string }) =>
    fetchApi<void>("/settings/team/invite", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  inviteUser: (email: string, role: string) =>
    fetchApi<void>("/settings/team/invite", {
      method: "POST",
      body: JSON.stringify({ email, full_name: "", role }),
    }),
  updateRole: (memberId: string, role: string) =>
    fetchApi<void>(`/settings/team/${memberId}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),
  updateUserRole: (memberId: number, role: string) =>
    fetchApi<void>(`/settings/team/${memberId}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),
  removeUser: (memberId: number) =>
    fetchApi<void>(`/settings/team/${memberId}`, {
      method: "DELETE",
    }),
  getAlertSettings: () =>
    fetchApi<{
      low_cash_threshold: number;
      high_expense_threshold: number;
      anomaly_sensitivity: number;
      email_enabled: boolean;
      email_addresses: string[];
      slack_enabled: boolean;
      slack_webhook_url: string | null;
    }>("/settings/alerts"),
  updateAlertSettings: (data: {
    low_cash_threshold?: number;
    high_expense_threshold?: number;
    anomaly_sensitivity?: number;
    email_enabled?: boolean;
    email_addresses?: string[];
    slack_enabled?: boolean;
    slack_webhook_url?: string;
  }) =>
    fetchApi<{
      low_cash_threshold: number;
      high_expense_threshold: number;
      anomaly_sensitivity: number;
      email_enabled: boolean;
      email_addresses: string[];
      slack_enabled: boolean;
      slack_webhook_url: string | null;
    }>("/settings/alerts", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};


// ── Health Check ─────────────────────────────────────────────────

export const systemApi = {
  health: () => fetchApi<{ status: string; version: string }>("/health"),
};


// ── Investor View ────────────────────────────────────────────────

export const investorApi = {
  getSummary: () =>
    fetchApi<{
      health_score: number;
      health_label: string;
      metrics: { label: string; value: string; delta: string; positive: boolean; note: string }[];
      revenue_trend: { month: string; revenue: number; expenses: number }[];
      kpis: { label: string; value: string; trend: string; change: string }[];
    }>("/dashboard/investor-summary"),
};


// ══════════════════════════════════════════════════════════════════
// Unified namespace — supports `import { api } from "@/lib/api"`
// ══════════════════════════════════════════════════════════════════

export const api = {
  // ── Nested namespaces (preferred) ──────────────────────────────
  auth: authApi,
  onboarding: onboardingApi,
  dashboard: dashboardApi,
  transactions: transactionsApi,
  budgets: budgetsApi,
  goals: goalsApi,
  alerts: alertsApi,
  chat: chatApi,
  forecast: forecastApi,
  anomaly: anomalyApi,
  healthScore: healthScoreApi,
  reports: reportsApi,
  calculator: calculatorApi,
  audit: auditApi,
  benchmarks: benchmarksApi,
  settings: settingsApi,
  investor: investorApi,
  system: systemApi,

  // ── Flat compatibility methods (used by existing pages) ────────
  // These accept an optional trailing `_token` param for backward
  // compat — the token is actually resolved internally by fetchApi.

  getDashboard: (_token?: string | null) =>
    fetchApi<DashboardSummary>(`/dashboard/summary?months=6`, {}, _token),

  getAlerts: (_unreadOnly?: boolean, _token?: string | null) =>
    fetchApi<Alert[]>(
      `/alerts${_unreadOnly ? "?unread_only=true" : ""}`,
      {},
      _token
    ),

  dismissAlert: (id: string | number, _token?: string | null) =>
    fetchApi<void>(`/alerts/${id}/dismiss`, { method: "POST" }, _token),

  getTransactions: (
    page?: number,
    perPage?: number,
    search?: string,
    _token?: string | null,
  ) => {
    const query = new URLSearchParams();
    if (page) query.set("page", String(page));
    if (perPage) query.set("per_page", String(perPage));
    if (search) query.set("search", search);
    return fetchApi<PaginatedTransactions>(`/transactions?${query}`, {}, _token);
  },

  createTransaction: (
    data: TransactionCreate,
    _token?: string | null,
  ) =>
    fetchApi<Transaction>("/transactions", {
      method: "POST",
      body: JSON.stringify(data),
    }, _token),

  uploadCSV: async (file: File, _token?: string | null) => {
    const formData = new FormData();
    formData.append("file", file);
    const url = `${API_BASE}/transactions/upload-csv`;
    const headers: Record<string, string> = {};
    if (_token) headers["Authorization"] = `Bearer ${_token}`;
    const resp = await fetch(url, { method: "POST", headers, body: formData });
    return resp.json();
  },

  getBudgets: (_token?: string | null) =>
    fetchApi<Budget[]>(`/budgets`, {}, _token),

  createBudget: (
    data: { category: string; limit_amount?: number; monthly_limit?: number; period?: string; month?: string; alert_threshold?: number },
    _token?: string | null,
  ) =>
    fetchApi<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify({
        category: data.category,
        monthly_limit: data.limit_amount ?? data.monthly_limit ?? 0,
        alert_threshold: data.alert_threshold,
        month: data.period ?? data.month,
      }),
    }, _token),

  getForecast: (
    scenario?: string,
    months?: number,
    _token?: string | null,
  ) =>
    fetchApi<ForecastResponse>(
      `/forecasting/?months_ahead=${months}&scenario=${scenario}`,
      {},
      _token
    ),

  sendChat: (message: string, _token?: string | null) =>
    fetchApi<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }, _token),
};
