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
  // Phase 2
  Vendor,
  VendorCreate,
  VendorUpdate,
  VendorContactCreate,
  VendorSpendAnalysis,
  DuplicateVendorGroup,
  TaxCategory,
  TaxCategoryCreate,
  TaxJurisdiction,
  TaxJurisdictionCreate,
  TaxEstimate,
  TaxReport,
  IndiaTaxCalculationRequest,
  IndiaHRACalculationRequest,
  IndiaGratuityCalculationRequest,
  USTaxCalculationRequest,
  MultiCountryTaxRequest,
  IndiaRegimeComparisonRequest,
  EffectiveHourlyRateRequest,
  ExternalTaxCalculationResponse,
  IndiaRegimeComparisonResponse,
  EffectiveHourlyRateResponse,
  SupportedCountry,
  Invoice,
  InvoiceCreate,
  InvoiceUpdate,
  InvoicePaymentCreate,
  AgingReport,
  ApprovalPolicy,
  ApprovalPolicyCreate,
  ExpenseApproval,
  ApprovalDecision,
  Scenario,
  ScenarioCreate,
  ScenarioUpdate,
  ScenarioComparison,
  SensitivityResult,
  MonteCarloResult,
  ScenarioTemplate,
  ScenarioShare,
  ScenarioShareCreate,
  VendorReview,
  VendorReviewCreate,
  VendorScorecard,
  VendorContract,
  ContractCreate,
  ContractUpdate,
  ContractExpiringSoon,
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



  // Request timeout — no hanging requests (default 30s, overridable)
  const timeoutMs = (options as any)._timeoutMs || 30_000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    const { _timeoutMs, ...cleanOptions } = options as any;
    response = await fetch(url, {
      ...cleanOptions,
      headers,
      signal: controller.signal,
      cache: "no-store",     // no caching of external API responses
      keepalive: false,      // no connection pooling
    });
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new Error(`Request timeout: ${path} did not respond within ${timeoutMs / 1000}s`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

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
  scan: (threshold?: number, days = 365) => {
    const params = new URLSearchParams({ days: String(days) });
    if (threshold !== undefined) params.set("z_threshold", String(threshold));
    return fetchApi<ScanResult>(`/anomaly/scan?${params.toString()}`);
  },

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


// ════════════════════════════════════════════════════════════════
// PHASE 2: Industry-Ready Feature API Clients
// ════════════════════════════════════════════════════════════════

// ── Vendor Management ────────────────────────────────────────────

export const vendorsApi = {
  syncFromTransactions: () =>
    fetchApi<{ created: number; message: string }>("/vendors/sync-from-transactions", {
      method: "POST",
    }),

  list: (activeOnly = false) =>
    fetchApi<Vendor[]>(`/vendors?active_only=${activeOnly}`),

  get: (id: string) =>
    fetchApi<Vendor>(`/vendors/${id}`),

  create: (data: VendorCreate) =>
    fetchApi<Vendor>("/vendors", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: VendorUpdate) =>
    fetchApi<Vendor>(`/vendors/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/vendors/${id}`, { method: "DELETE" }),

  addContact: (vendorId: string, data: VendorContactCreate) =>
    fetchApi<Vendor>(`/vendors/${vendorId}/contacts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  spendAnalysis: () =>
    fetchApi<VendorSpendAnalysis[]>("/vendors/spend-analysis"),

  monthlyTrend: () =>
    fetchApi<{ month: string; vendor: string; total: number }[]>("/vendors/monthly-trend"),

  vendorTransactions: (vendorName: string, skip = 0, limit = 50) =>
    fetchApi<{ items: { id: string; date: string; description: string; amount: number; category: string; type: string }[]; total: number; skip: number; limit: number }>(
      `/vendors/vendor-transactions?name=${encodeURIComponent(vendorName)}&skip=${skip}&limit=${limit}`
    ),

  duplicates: (threshold = 0.7) =>
    fetchApi<DuplicateVendorGroup[]>(`/vendors/duplicates?threshold=${threshold}`),

  // ── Reviews & Scorecards ─────────────────────────────────────

  submitReview: (vendorId: string, data: VendorReviewCreate) =>
    fetchApi<VendorReview>(`/vendors/${vendorId}/reviews`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listReviews: (vendorId: string) =>
    fetchApi<VendorReview[]>(`/vendors/${vendorId}/reviews`),

  getScorecard: (vendorId: string) =>
    fetchApi<VendorScorecard>(`/vendors/${vendorId}/scorecard`),

  // ── Contract Management ──────────────────────────────────────

  expiringContracts: (days = 30) =>
    fetchApi<ContractExpiringSoon[]>(`/vendors/contracts/expiring?days=${days}`),

  createContract: (vendorId: string, data: ContractCreate) =>
    fetchApi<VendorContract>(`/vendors/${vendorId}/contracts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listContracts: (vendorId: string) =>
    fetchApi<VendorContract[]>(`/vendors/${vendorId}/contracts`),

  updateContract: (contractId: string, data: ContractUpdate) =>
    fetchApi<VendorContract>(`/vendors/contracts/${contractId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};


// ── Tax Management ───────────────────────────────────────────────

export const taxApi = {
  listCategories: () =>
    fetchApi<TaxCategory[]>("/tax/categories"),

  createCategory: (data: TaxCategoryCreate) =>
    fetchApi<TaxCategory>("/tax/categories", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listJurisdictions: () =>
    fetchApi<TaxJurisdiction[]>("/tax/jurisdictions"),

  createJurisdiction: (data: TaxJurisdictionCreate) =>
    fetchApi<TaxJurisdiction>("/tax/jurisdictions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listEstimates: (year?: number) => {
    const q = year ? `?year=${year}` : "";
    return fetchApi<TaxEstimate[]>(`/tax/estimates${q}`);
  },

  generateEstimate: (quarter: string, jurisdiction: string) =>
    fetchApi<TaxEstimate>("/tax/estimates", {
      method: "POST",
      body: JSON.stringify({ quarter, jurisdiction }),
    }),

  availableQuarters: () => fetchApi<string[]>("/tax/available-quarters"),

  getReport: (year?: number, jurisdiction?: string) => {
    const q = new URLSearchParams();
    if (year) q.set("year", String(year));
    if (jurisdiction) q.set("jurisdiction", jurisdiction);
    return fetchApi<TaxReport>(`/tax/report?${q}`);
  },

  // ── External Tax Calculation APIs ──────────────────────────────

  calculateIndiaTax: (data: IndiaTaxCalculationRequest) =>
    fetchApi<ExternalTaxCalculationResponse>("/tax/calculate/india", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  calculateIndiaHRA: (data: IndiaHRACalculationRequest) =>
    fetchApi<ExternalTaxCalculationResponse>("/tax/calculate/india/hra", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  calculateIndiaGratuity: (data: IndiaGratuityCalculationRequest) =>
    fetchApi<ExternalTaxCalculationResponse>("/tax/calculate/india/gratuity", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  calculateUSTax: (data: USTaxCalculationRequest) =>
    fetchApi<ExternalTaxCalculationResponse>("/tax/calculate/us", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  calculateGlobalTax: (data: MultiCountryTaxRequest) =>
    fetchApi<ExternalTaxCalculationResponse>("/tax/calculate/global", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listSupportedCountries: () =>
    fetchApi<SupportedCountry[]>("/tax/calculate/countries"),

  compareIndiaRegimes: (data: IndiaRegimeComparisonRequest) =>
    fetchApi<IndiaRegimeComparisonResponse>("/tax/calculate/india/compare-regimes", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  calculateHourlyRate: (data: EffectiveHourlyRateRequest) =>
    fetchApi<EffectiveHourlyRateResponse>("/tax/calculate/hourly-rate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};


// ── Invoice Management ───────────────────────────────────────────

export const invoicesApi = {
  list: (status?: string) => {
    const q = status ? `?status=${status}` : "";
    return fetchApi<Invoice[]>(`/invoices${q}`);
  },

  get: (id: string) =>
    fetchApi<Invoice>(`/invoices/${id}`),

  create: (data: InvoiceCreate) =>
    fetchApi<Invoice>("/invoices", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: InvoiceUpdate) =>
    fetchApi<Invoice>(`/invoices/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/invoices/${id}`, { method: "DELETE" }),

  send: (id: string) =>
    fetchApi<Invoice>(`/invoices/${id}/send`, { method: "POST" }),

  recordPayment: (id: string, data: InvoicePaymentCreate) =>
    fetchApi<Invoice>(`/invoices/${id}/payments`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  aging: () =>
    fetchApi<AgingReport>("/invoices/aging"),
};


// ── Expense Approvals ────────────────────────────────────────────

export const approvalsApi = {
  listPolicies: () =>
    fetchApi<ApprovalPolicy[]>("/approvals/policies"),

  createPolicy: (data: ApprovalPolicyCreate) =>
    fetchApi<ApprovalPolicy>("/approvals/policies", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: (status?: string) => {
    const q = status ? `?status=${status}` : "";
    return fetchApi<ExpenseApproval[]>(`/approvals${q}`);
  },

  pending: () =>
    fetchApi<ExpenseApproval[]>("/approvals/pending"),

  submit: (transactionId: string) =>
    fetchApi<ExpenseApproval>(`/approvals/submit/${transactionId}`, {
      method: "POST",
    }),

  approve: (id: string, data: ApprovalDecision) =>
    fetchApi<ExpenseApproval>(`/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  reject: (id: string, data: ApprovalDecision) =>
    fetchApi<ExpenseApproval>(`/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};


// ── Scenario Planning ────────────────────────────────────────────

export const scenariosApi = {
  list: () =>
    fetchApi<Scenario[]>("/scenarios"),

  get: (id: string) =>
    fetchApi<Scenario>(`/scenarios/${id}`),

  create: (data: ScenarioCreate) =>
    fetchApi<Scenario>("/scenarios", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: ScenarioUpdate) =>
    fetchApi<Scenario>(`/scenarios/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/scenarios/${id}`, { method: "DELETE" }),

  compare: (ids: string[]) =>
    fetchApi<{ comparisons: ScenarioComparison[] }>(`/scenarios/compare?ids=${ids.join(",")}`),

  sensitivity: (id: string, variables: string[], rangePct = 20, steps = 5) =>
    fetchApi<{ results: SensitivityResult[] }>(`/scenarios/${id}/sensitivity`, {
      method: "POST",
      body: JSON.stringify({ variables, range_pct: rangePct, steps }),
    }),

  monteCarlo: (revenueStd = 0.1, expenseStd = 0.08, months = 12, sims = 1000) =>
    fetchApi<MonteCarloResult>("/scenarios/monte-carlo", {
      method: "POST",
      body: JSON.stringify({
        revenue_std: revenueStd,
        expense_std: expenseStd,
        months_ahead: months,
        num_simulations: sims,
      }),
    }),

  // ── Templates ────────────────────────────────────────────────

  listTemplates: () =>
    fetchApi<ScenarioTemplate[]>("/scenarios/templates"),

  getTemplate: (id: string) =>
    fetchApi<ScenarioTemplate>(`/scenarios/templates/${id}`),

  // ── Sharing ──────────────────────────────────────────────────

  share: (scenarioId: string, data: ScenarioShareCreate) =>
    fetchApi<ScenarioShare>(`/scenarios/${scenarioId}/share`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listShares: (scenarioId: string) =>
    fetchApi<ScenarioShare[]>(`/scenarios/${scenarioId}/shares`),

  sharedWithMe: () =>
    fetchApi<ScenarioShare[]>("/scenarios/shared"),

  revokeShare: (scenarioId: string, shareId: string) =>
    fetchApi<void>(`/scenarios/${scenarioId}/share/${shareId}`, { method: "DELETE" }),
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
  // Phase 2
  vendors: vendorsApi,
  tax: taxApi,
  invoices: invoicesApi,
  approvals: approvalsApi,
  scenarios: scenariosApi,

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
    
    // Use provided token or fall back to token provider
    let token = _token;
    if (!token && _tokenProvider) {
      try { token = await _tokenProvider(); } catch { /* ignore */ }
    }
    
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
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
        alert_threshold: data.alert_threshold ?? 0.8,
        month: data.month || new Date().toISOString().slice(0, 7),
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
