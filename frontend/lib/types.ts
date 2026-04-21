// ════════════════════════════════════════════════════════════════
// AI CFO — Frontend Type Definitions
// Aligned 1:1 with backend schemas.py
// ════════════════════════════════════════════════════════════════

// ── Auth / User ──────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  workspace_id: string;
  avatar_url?: string;
  is_active: boolean;
}

// ── Workspace ────────────────────────────────────────────────────

export interface Workspace {
  id: string;
  name: string;
  industry: string;
  currency: string;
  is_demo: boolean;
}

// ── Transactions ─────────────────────────────────────────────────

export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: string;
  type: "income" | "expense";
  account: string;
  vendor?: string;
  is_anomaly: boolean;
  anomaly_score?: number;
  source: string;
  created_at: string;
}

/** Alias for backward compatibility with pages importing TransactionOut */
export type TransactionOut = Transaction;

export interface PaginatedTransactions {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface TransactionCreate {
  date: string;
  description: string;
  amount: number;
  category: string;
  type: "income" | "expense";
  account?: string;
  vendor?: string;
  notes?: string;
}

// ── Dashboard ────────────────────────────────────────────────────

export interface CategoryAmount {
  category: string;
  amount: number;
}

export interface DashboardSummary {
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  transaction_count: number;
  burn_rate: number;
  runway_months: number;
  budget_utilization: number;
  active_alerts: number;
  cash_balance: number;
  monthly_income: number[];
  monthly_expenses: number[];
  top_categories: CategoryAmount[];
  recent_transactions: Transaction[];
  period_months: number;
}

// ── Budgets ──────────────────────────────────────────────────────

export interface Budget {
  id: string;
  category: string;
  monthly_limit: number;
  alert_threshold: number;
  current_spend: number;
  percentage_used: number;
  status: "on_track" | "warning" | "over_budget";
  month: string;
}

export interface BudgetCreate {
  category: string;
  monthly_limit: number;
  alert_threshold?: number;
  month?: string;
}

// ── Goals ────────────────────────────────────────────────────────

export interface Goal {
  id: string;
  title: string;
  target_value: number;
  current_value: number;
  metric_type: string;
  deadline?: string;
  status: "active" | "completed" | "abandoned";
  progress_pct: number;
  created_at: string;
}

export interface GoalCreate {
  title: string;
  target_value: number;
  metric_type: string;
  deadline?: string;
}

export interface GoalUpdate {
  title?: string;
  target_value?: number;
  current_value?: number;
  status?: string;
  deadline?: string;
}

// ── Alerts ───────────────────────────────────────────────────────

export interface Alert {
  id: string;
  title: string;
  message: string;
  severity: "info" | "warning" | "critical";
  category: string;
  action_url?: string;
  is_read: boolean;
  is_dismissed: boolean;
  created_at: string;
}

// ── Forecasting ──────────────────────────────────────────────────

export interface ForecastPoint {
  period: string;
  projected_income: number;
  projected_expenses: number;
  projected_net: number;
  cumulative_net: number;
  confidence: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface ForecastResponse {
  scenario: string;
  months_ahead: number;
  historical_months: number;
  data_points: ForecastPoint[];
  model_version: string;
  assumptions?: Record<string, number | string>;
}

// ── Chat ─────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  session_id?: string; // UUID
}

export interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
  last_active_at: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string; // UUID — persist this for follow-up messages
  sources: string[];
  suggested_actions: string[];
  confidence: string;
}

/** Simple chat message used by the chat page UI */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// ── Anomaly Detection ────────────────────────────────────────────

export interface Anomaly {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: string;
  type: string;
  account: string;
  anomaly_score: number;
  reason: string;
}

export interface ScanResult {
  scanned: number;
  anomalies_found: number;
  anomalies: Anomaly[];
}

// ── Health Score ──────────────────────────────────────────────────

export interface ScoreComponent {
  name: string;
  score: number;
  max_score: number;
  description: string;
  status: "excellent" | "good" | "fair" | "poor";
}

export interface HealthScoreResponse {
  overall_score: number;
  grade: string;
  stage: string;
  components: ScoreComponent[];
  recommendations: string[];
  computed_at: string;
}

// ── Reports ──────────────────────────────────────────────────────

export interface CategorySummary {
  category: string;
  total: number;
  count: number;
}

export interface ReportSummary {
  period_start: string;
  period_end: string;
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  transaction_count: number;
  expense_by_category: CategorySummary[];
  top_vendors: { vendor: string; total: number; count: number }[];
}

// ── Calculator ───────────────────────────────────────────────────

export interface AffordabilityRequest {
  expense_name: string;
  amount: number;
  frequency: "one_time" | "monthly" | "annual";
}

export interface AffordabilityResponse {
  can_afford: boolean;
  current_runway_months: number;
  projected_runway_months: number;
  current_balance_3m: number;
  projected_balance_3m: number;
  break_even_revenue?: number;
  ai_suggestion: string;
}

// ── Audit Log ────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  user_email: string;
  user_name: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedAuditLogs {
  items: AuditLogEntry[];
  total: number;
  page: number;
  per_page: number;
}

// ── Benchmarks ───────────────────────────────────────────────────

export interface BenchmarkInsight {
  metric_name: string;
  your_value: number;
  benchmark_value: number;
  unit: string;
  delta_pct: number;
  insight: string;
  status: "above" | "below" | "on_par";
}
