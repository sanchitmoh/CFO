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
  ScanResult,
  HealthScoreResponse,
  ReportSummary,
  AffordabilityRequest,
  AffordabilityResponse,
  PaginatedAuditLogs,
  BenchmarkInsight,
  Workspace,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Helper ───────────────────────────────────────────────────────

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  // Get auth token from Clerk
  let token: string | null = null;
  if (typeof window !== "undefined") {
    // @ts-ignore — Clerk exposes this globally
    const clerk = window.Clerk;
    if (clerk?.session) {
      token = await clerk.session.getToken();
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
  sync: () => fetchApi<{ status: string }>("/auth/sync", { method: "POST" }),
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
    if (typeof window !== "undefined") {
      // @ts-ignore
      const clerk = window.Clerk;
      if (clerk?.session) {
        token = await clerk.session.getToken();
      }
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

  history: (sessionId: string) =>
    fetchApi<{ role: string; content: string; created_at: string }[]>(
      `/chat/history?session_id=${sessionId}`
    ),
};


// ── Forecasting ──────────────────────────────────────────────────

export const forecastApi = {
  get: (monthsAhead = 6, scenario = "base") =>
    fetchApi<ForecastResponse>(
      `/forecasting?months_ahead=${monthsAhead}&scenario=${scenario}`
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
  inviteMember: (data: { email: string; full_name: string; role: string }) =>
    fetchApi<void>("/settings/team/invite", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateRole: (memberId: string, role: string) =>
    fetchApi<void>(`/settings/team/${memberId}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),
};


// ── Health Check ─────────────────────────────────────────────────

export const systemApi = {
  health: () => fetchApi<{ status: string; version: string }>("/health"),
};
