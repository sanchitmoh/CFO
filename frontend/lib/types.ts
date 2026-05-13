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

// ════════════════════════════════════════════════════════════════
// PHASE 2: Industry-Ready Feature Types
// ════════════════════════════════════════════════════════════════

// ── Vendor Management ────────────────────────────────────────────

export interface VendorContact {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  role?: string;
}

export interface Vendor {
  id: string;
  name: string;
  category?: string;
  payment_terms?: string;
  tax_id?: string;
  is_active: boolean;
  notes?: string;
  contacts: VendorContact[];
  total_spent: number;
  transaction_count: number;
  created_at: string;
}

export interface VendorCreate {
  name: string;
  category?: string;
  payment_terms?: string;
  tax_id?: string;
  notes?: string;
}

export interface VendorUpdate {
  name?: string;
  category?: string;
  payment_terms?: string;
  tax_id?: string;
  is_active?: boolean;
  notes?: string;
}

export interface VendorContactCreate {
  name: string;
  email?: string;
  phone?: string;
  role?: string;
}

export interface VendorSpendAnalysis {
  vendor_name: string;
  total_spend: number;
  transaction_count: number;
  avg_transaction: number;
  last_transaction_date?: string;
  category?: string;
}

export interface DuplicateVendorGroup {
  name: string;
  matches: { id: string; name: string; score: number }[];
}

// ── Vendor Reviews & Scorecards ──────────────────────────────────

export interface VendorReviewCreate {
  delivery_rating: number;
  quality_rating: number;
  responsiveness_rating: number;
  cost_rating: number;
  comment?: string;
}

export interface VendorReview {
  id: string;
  vendor_id: string;
  reviewer_user_id: string;
  delivery_rating: number;
  quality_rating: number;
  responsiveness_rating: number;
  cost_rating: number;
  comment?: string;
  review_date: string;
}

export interface VendorScorecard {
  vendor_id: string;
  vendor_name: string;
  total_reviews: number;
  avg_delivery: number;
  avg_quality: number;
  avg_responsiveness: number;
  avg_cost: number;
  composite_score: number;
}

// ── Vendor Contracts ─────────────────────────────────────────────

export interface ContractCreate {
  title: string;
  contract_type: string;
  start_date: string;
  end_date: string;
  value?: number;
  auto_renew?: boolean;
  renewal_notice_days?: number;
  notes?: string;
}

export interface ContractUpdate {
  title?: string;
  contract_type?: string;
  start_date?: string;
  end_date?: string;
  value?: number;
  auto_renew?: boolean;
  renewal_notice_days?: number;
  status?: string;
  notes?: string;
}

export interface VendorContract {
  id: string;
  vendor_id: string;
  title: string;
  contract_type: string;
  start_date: string;
  end_date: string;
  value?: number;
  auto_renew: boolean;
  renewal_notice_days: number;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ContractExpiringSoon {
  contract: VendorContract;
  vendor_name: string;
  days_remaining: number;
}

// ── Tax Management ───────────────────────────────────────────────

export interface TaxCategory {
  id: string;
  category: string;
  tax_code: "fully_deductible" | "partially_deductible" | "non_deductible";
  deduction_rate: number;
  jurisdiction: string;
  notes?: string;
  created_at: string;
}

export interface TaxCategoryCreate {
  category: string;
  tax_code?: string;
  deduction_rate?: number;
  jurisdiction?: string;
  notes?: string;
}

export interface TaxJurisdiction {
  id: string;
  code: string;
  name: string;
  tax_rates_json?: Record<string, unknown> | null;
  filing_frequency: string;
  is_active: boolean;
  created_at: string;
}

export interface TaxJurisdictionCreate {
  code: string;
  name: string;
  tax_rates_json?: Record<string, unknown>;
  filing_frequency?: string;
}

export interface TaxEstimate {
  id: string;
  quarter: string;
  jurisdiction: string;
  jurisdiction_code: string;   // computed alias
  gross_income: number;        // computed: taxable_income + deductions_total
  total_deductions: number;    // computed alias for deductions_total
  taxable_income: number;
  estimated_tax: number;
  effective_rate: number;
  deductions_total: number;
  status: string;
  due_date: string | null;
  paid_date: string | null;
  created_at: string;
}

export interface TaxReport {
  fiscal_year: number;
  jurisdiction: string;
  gross_income: number;
  total_deductions: number;
  taxable_income: number;
  estimated_annual_tax: number;
  effective_rate: number;
  quarterly_estimates: TaxEstimate[];
  deduction_breakdown: { category: string; amount: number; deductibility: string }[];
}

// ── External Tax Calculation APIs ────────────────────────────────

export interface IndiaTaxCalculationRequest {
  gross_income: number;
  regime?: string;
  apply_standard_deduction?: boolean;
}

export interface IndiaHRACalculationRequest {
  basic_salary: number;
  hra_received: number;
  rent_paid: number;
  is_metro?: boolean;
}

export interface IndiaGratuityCalculationRequest {
  monthly_basic: number;
  years_of_service: number;
  covered_by_act?: boolean;
}

export interface USTaxCalculationRequest {
  income: number;
  filing_status?: string;
  qbi_deduction?: boolean;
}

export interface MultiCountryTaxRequest {
  country_code: string;
  income: number;
  extra_params?: Record<string, unknown>;
}

export interface IndiaRegimeComparisonRequest {
  gross_income: number;
}

export interface EffectiveHourlyRateRequest {
  country_code: string;
  annual_income: number;
  weekly_hours?: number;
  paid_days_off?: number;
}

export interface ExternalTaxCalculationResponse {
  source: string;
  country: string;
  data: Record<string, unknown>;
}

export interface IndiaRegimeComparisonResponse {
  gross_income: number;
  old_regime: Record<string, unknown>;
  new_regime: Record<string, unknown>;
  savings: number;
  recommendation: string;
}

export interface EffectiveHourlyRateResponse {
  country: string;
  gross_income: number;
  net_income: number;
  hourly_rate: number;
  daily_rate: number;
  working_days: number;
  effective_tax_rate: number;
}

export interface SupportedCountry {
  code: string;
  name: string;
  features?: string;
}

// ── Invoice Management ───────────────────────────────────────────

export interface InvoicePayment {
  id: string;
  amount: number;
  payment_date: string;
  method?: string;
  reference?: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  client_name: string;
  client_email?: string;
  issue_date: string;
  due_date: string;
  line_items: { description: string; quantity: number; unit_price: number; amount: number }[];
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  amount_paid: number;
  amount_due: number;
  status: "draft" | "sent" | "paid" | "partially_paid" | "overdue" | "cancelled";
  notes?: string;
  payments: InvoicePayment[];
  created_at: string;
}

export interface InvoiceCreate {
  client_name: string;
  client_email?: string;
  issue_date: string;
  due_date: string;
  line_items: { description: string; quantity: number; unit_price: number }[];
  tax_rate?: number;
  notes?: string;
}

export interface InvoiceUpdate {
  client_name?: string;
  client_email?: string;
  due_date?: string;
  line_items?: { description: string; quantity: number; unit_price: number }[];
  tax_rate?: number;
  notes?: string;
  status?: string;
}

export interface InvoicePaymentCreate {
  amount: number;
  payment_date: string;
  method?: string;
  reference?: string;
}

export interface AgingBucket {
  bucket: string;
  count: number;
  total: number;
  invoices: { id: string; invoice_number: string; client_name: string; total: number; amount_due: number; due_date: string; days_overdue: number }[];
}

export interface AgingReport {
  as_of: string;
  total_outstanding: number;
  buckets: AgingBucket[];
}

// ── Expense Approvals ────────────────────────────────────────────

export interface ApprovalPolicy {
  id: string;
  name: string;
  min_amount: number;
  max_amount?: number;
  categories: string[];
  approver_roles: string[];
  is_active: boolean;
  created_at: string;
}

export interface ApprovalPolicyCreate {
  name: string;
  min_amount: number;
  max_amount?: number;
  categories?: string[];
  approver_roles?: string[];
}

export interface ExpenseApproval {
  id: string;
  transaction_id: string;
  policy_id: string;
  requested_by: string;
  decided_by?: string;
  status: "pending" | "approved" | "rejected";
  notes?: string;
  rejection_reason?: string;
  requested_at: string;
  decided_at?: string;
}

export interface ApprovalDecision {
  notes?: string;
  rejection_reason?: string;
}

// ── Scenario Planning ────────────────────────────────────────────

export interface ScenarioAssumptions {
  // Core
  revenue_growth_pct: number;
  expense_change_pct: number;
  new_monthly_revenue?: number;
  removed_monthly_expense?: number;
  one_time_income?: number;
  one_time_expense?: number;
  // Extended
  headcount_change?: number;
  avg_salary_per_head?: number;
  customer_churn_pct?: number;
  pricing_change_pct?: number;
  tax_rate_pct?: number;
  capex_monthly?: number;
  loan_repayment_monthly?: number;
  seasonal_dip_months?: number[];
}

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  assumptions: ScenarioAssumptions;
  months_ahead: number;
  created_by: string;
  created_at: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string;
  assumptions: ScenarioAssumptions;
  months_ahead?: number;
}

export interface ScenarioUpdate {
  name?: string;
  description?: string;
  assumptions?: Partial<ScenarioAssumptions>;
  months_ahead?: number;
}

export interface ScenarioProjection {
  month: string;
  revenue: number;
  expenses: number;
  net_cash_flow: number;
  cumulative_cash: number;
}

export interface ScenarioComparison {
  scenario_id: string;
  scenario_name: string;
  projections: ScenarioProjection[];
  final_cash: number;
  runway_months: number;
}

export interface SensitivityResult {
  variable: string;
  delta_pct: number;
  runway_months: number;
  final_cash: number;
}

export interface MonteCarloResult {
  p10_runway: number;
  p50_runway: number;
  p90_runway: number;
  p10_cash: number;
  p50_cash: number;
  p90_cash: number;
  months_ahead: number;
  num_simulations: number;
  simulations?: number;      // Keep for backward compatibility
  distribution: { percentile: number; runway: number; cash: number }[];
  histogram?: { bucket: string; count: number }[];  // Keep for backward compatibility
  // Baseline transparency — inputs that drove the simulation
  baseline_monthly_income?: number;
  baseline_monthly_expense?: number;
  starting_cash?: number;
}

// ── Scenario Templates ───────────────────────────────────────────

export interface ScenarioTemplate {
  id: string;
  name: string;
  description: string;
  industry: string;
  assumptions: ScenarioAssumptions;
}

// ── Scenario Sharing ─────────────────────────────────────────────

export interface ScenarioShareCreate {
  shared_with_user_id: string;
  permission: "viewer" | "editor";
}

export interface ScenarioShare {
  id: string;
  scenario_id: string;
  shared_by_user_id: string;
  shared_with_user_id: string;
  permission: string;
  created_at: string;
}
