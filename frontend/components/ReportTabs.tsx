"use client";

import { useState } from "react";
import {
  BarChart,
  ChartSkeleton,
  ComparisonTable,
  DonutChart,
  LineChart,
  MetricCard,
  VarianceBar,
} from "@/components/ReportCharts";
import { useCurrency } from "@/components/CurrencyContext";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  ChevronDown,
  ChevronRight,
  DollarSign,
  MessageSquare,
  Sparkles,
  StickyNote,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import type {
  DashboardSummary,
  ForecastResponse,
  ReportSummary,
  Transaction,
} from "@/lib/types";

interface Annotation {
  section: string;
  text: string;
}

interface DrillDownState {
  category: string | null;
  transactions: Transaction[];
  loading: boolean;
}

function formatMoney(value: number, currencyCode: string) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  }
}

function formatForecastMoney(value: number, currencyCode: string) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return formatMoney(value, "USD");
  }
}

function formatPeriodLabel(period: string) {
  const [year, month] = period.split("-");
  if (!year || !month) return period;
  const monthIndex = Number(month) - 1;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return monthIndex >= 0 && monthIndex < months.length
    ? `${months[monthIndex]} '${year.slice(2)}`
    : period;
}

export function AnnotationBox({
  section,
  annotations,
  onSave,
}: {
  section: string;
  annotations: Annotation[];
  onSave: (section: string, text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const existing = annotations.filter((annotation) => annotation.section === section);

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs"
        style={{ color: "var(--text-dim)" }}
      >
        <StickyNote size={12} />
        {existing.length > 0 ? `${existing.length} note(s)` : "Add note"}
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {existing.map((annotation, index) => (
            <div
              key={index}
              className="text-xs p-2 rounded-lg"
              style={{
                background: "var(--warning-soft)",
                color: "var(--warning)",
                border: "1px solid var(--warning)22",
              }}
            >
              {annotation.text}
            </div>
          ))}
          <div className="flex gap-2">
            <input
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Add a note..."
              className="flex-1 text-xs"
              onKeyDown={(event) => {
                if (event.key === "Enter" && text.trim()) {
                  onSave(section, text.trim());
                  setText("");
                }
              }}
            />
            <button
              onClick={() => {
                if (!text.trim()) return;
                onSave(section, text.trim());
                setText("");
              }}
              className="btn-primary text-xs px-3 py-1"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function CashFlowTab({
  data,
  annotations,
  onAnnotate,
  onDrillDown,
  drillDown,
}: {
  data: ReportSummary;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
  onDrillDown: (category: string) => void;
  drillDown: DrillDownState;
}) {
  const { currencyCode } = useCurrency();
  const reportCurrency = data.base_currency || currencyCode;
  const net = data.total_income - data.total_expenses;
  const savingsRate = data.total_income > 0 ? (net / data.total_income) * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="Total Income" value={formatMoney(data.total_income, reportCurrency)} icon={<ArrowUpCircle size={16} />} trend="up" subtext="Inflows" />
        <MetricCard label="Total Expenses" value={formatMoney(data.total_expenses, reportCurrency)} icon={<ArrowDownCircle size={16} />} trend="down" subtext="Outflows" />
        <MetricCard label="Net Cash Flow" value={formatMoney(net, reportCurrency)} icon={<DollarSign size={16} />} trend={net >= 0 ? "up" : "down"} subtext={net >= 0 ? "Positive" : "Negative"} />
        <MetricCard label="Savings Rate" value={`${savingsRate.toFixed(1)}%`} icon={<TrendingUp size={16} />} trend={savingsRate > 10 ? "up" : "down"} subtext={`${data.transaction_count} txns`} />
      </div>
      <AnnotationBox section="cashflow-kpi" annotations={annotations} onSave={onAnnotate} />

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Expense by Category
        </h3>
        {data.expense_by_category.length > 0 ? (
          <>
            <BarChart data={data.expense_by_category.map((item) => ({ label: item.category, value: item.total }))} height={180} currencyCode={reportCurrency} />
            <div className="mt-4 space-y-1">
              {data.expense_by_category.map((item) => (
                <button
                  key={item.category}
                  onClick={() => onDrillDown(item.category)}
                  className="w-full flex items-center justify-between py-2 px-3 rounded-lg text-xs hover:opacity-80 transition-all"
                  style={{
                    background: drillDown.category === item.category ? "var(--accent-soft)" : "var(--bg)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <span style={{ color: "var(--text)" }}>{item.category}</span>
                  <span className="flex items-center gap-2">
                    <span className="font-mono" style={{ color: "var(--text-muted)" }}>
                      {formatMoney(item.total, reportCurrency)} | {item.count} txns
                    </span>
                    <ChevronRight size={12} style={{ color: "var(--text-dim)" }} />
                  </span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <div className="text-xs text-center py-8" style={{ color: "var(--text-dim)" }}>
            No category data for this period
          </div>
        )}
        <AnnotationBox section="cashflow-categories" annotations={annotations} onSave={onAnnotate} />
      </div>

      {drillDown.category && (
        <div className="glass p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
            Transactions: {drillDown.category}
          </h3>
          {drillDown.loading ? (
            <ChartSkeleton height={100} />
          ) : drillDown.transactions.length > 0 ? (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {drillDown.transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  className="flex justify-between py-2 px-3 rounded-lg text-xs"
                  style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                >
                  <div>
                    <span style={{ color: "var(--text)" }}>{transaction.description}</span>
                    <span className="ml-2" style={{ color: "var(--text-dim)" }}>
                      {new Date(transaction.date).toLocaleDateString()}
                    </span>
                    {transaction.amount_original != null &&
                      transaction.currency_code &&
                      transaction.currency_code !== reportCurrency && (
                        <span className="ml-2" style={{ color: "var(--text-dim)" }}>
                          original {formatMoney(transaction.amount_original, transaction.currency_code)}
                        </span>
                      )}
                  </div>
                  <span className="font-mono" style={{ color: transaction.type === "income" ? "var(--success)" : "var(--danger)" }}>
                    {transaction.type === "income" ? "+" : "-"}
                    {formatMoney(transaction.amount, reportCurrency)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-center py-4" style={{ color: "var(--text-dim)" }}>
              No transactions found
            </div>
          )}
        </div>
      )}

      {data.top_vendors.length > 0 && (
        <div className="glass p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
            Top Vendors
          </h3>
          <div className="space-y-1">
            {data.top_vendors.map((vendor, index) => (
              <div
                key={index}
                className="flex justify-between py-2 px-3 rounded-lg text-xs"
                style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
              >
                <span style={{ color: "var(--text)" }}>{vendor.vendor}</span>
                <span className="font-mono" style={{ color: "var(--text-muted)" }}>
                  {formatMoney(vendor.total, reportCurrency)} | {vendor.count} txns
                </span>
              </div>
            ))}
          </div>
          <AnnotationBox section="cashflow-vendors" annotations={annotations} onSave={onAnnotate} />
        </div>
      )}
    </div>
  );
}

export function ForecastTab({
  forecast,
  scenario,
  onScenarioChange,
  loading,
  annotations,
  onAnnotate,
}: {
  forecast: ForecastResponse | null;
  scenario: string;
  onScenarioChange: (scenario: string) => void;
  loading: boolean;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
}) {
  const scenarios = ["optimistic", "base", "pessimistic"];
  const scenarioColors: Record<string, string> = {
    optimistic: "var(--success)",
    base: "var(--accent)",
    pessimistic: "var(--danger)",
  };

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        {scenarios.map((value) => (
          <button
            key={value}
            onClick={() => onScenarioChange(value)}
            className="px-4 py-1.5 text-xs font-medium rounded-lg transition-all capitalize"
            style={{
              background: scenario === value ? scenarioColors[value] : "var(--surface-hover)",
              color: scenario === value ? "#fff" : "var(--text)",
              border: `1px solid ${scenario === value ? scenarioColors[value] : "var(--border)"}`,
            }}
          >
            {value}
          </button>
        ))}
      </div>

      {loading ? (
        <ChartSkeleton height={280} />
      ) : forecast && forecast.data_points.length > 0 ? (
        <>
          <div className="glass p-5">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={14} style={{ color: scenarioColors[scenario] }} />
              <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {forecast.months_ahead}-Month Projection
              </h3>
              <span
                className="text-xs px-2 py-0.5 rounded-full capitalize"
                style={{ background: `${scenarioColors[scenario]}22`, color: scenarioColors[scenario] }}
              >
                {scenario}
              </span>
            </div>
            <LineChart
              labels={forecast.data_points.map((point) => point.period)}
              datasets={[
                { label: "Income", values: forecast.data_points.map((point) => point.projected_income), color: "#5E9E7E" },
                { label: "Expenses", values: forecast.data_points.map((point) => point.projected_expenses), color: "#C75050" },
                { label: "Net", values: forecast.data_points.map((point) => point.projected_net), color: "#C9A962" },
              ]}
              height={280}
              currencyCode={forecast.base_currency || "USD"}
            />
            <AnnotationBox section="forecast-chart" annotations={annotations} onSave={onAnnotate} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {(() => {
              const last = forecast.data_points[forecast.data_points.length - 1];
              const cumulativeNet = last.cumulative_net;
              const confidence = last.confidence;
              const currencyCode = forecast.base_currency || "USD";
              return (
                <>
                  <MetricCard label="End-of-Period Net" value={formatForecastMoney(cumulativeNet, currencyCode)} trend={cumulativeNet >= 0 ? "up" : "down"} subtext="Cumulative" />
                  <MetricCard label="Confidence" value={`${(confidence * 100).toFixed(0)}%`} trend={confidence > 0.7 ? "up" : "down"} subtext={confidence > 0.7 ? "High" : "Low"} />
                  <MetricCard
                    label="Monthly Avg Net"
                    value={formatForecastMoney(Math.round(cumulativeNet / forecast.data_points.length), currencyCode)}
                    trend={cumulativeNet >= 0 ? "up" : "down"}
                    subtext="Projected"
                  />
                </>
              );
            })()}
          </div>

          <div className="glass p-5">
            <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
              Projection Data
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs" style={{ borderCollapse: "separate", borderSpacing: "0 3px" }}>
                <thead>
                  <tr>
                    {["Period", "Income", "Expenses", "Net", "Cumulative", "Confidence"].map((heading) => (
                      <th key={heading} className="text-left px-3 pb-2 font-semibold" style={{ color: "var(--text-muted)" }}>
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {forecast.data_points.map((point, index) => (
                    <tr key={index} style={{ background: "var(--surface)" }}>
                      <td className="px-3 py-2 rounded-l-lg" style={{ color: "var(--text)" }}>{point.period}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--success)" }}>{formatForecastMoney(point.projected_income, forecast.base_currency || "USD")}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--danger)" }}>{formatForecastMoney(point.projected_expenses, forecast.base_currency || "USD")}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: point.projected_net >= 0 ? "var(--success)" : "var(--danger)" }}>{formatForecastMoney(point.projected_net, forecast.base_currency || "USD")}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--text)" }}>{formatForecastMoney(point.cumulative_net, forecast.base_currency || "USD")}</td>
                      <td className="px-3 py-2 rounded-r-lg">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 rounded-full overflow-hidden" style={{ height: 4, background: "var(--surface-hover)" }}>
                            <div
                              style={{
                                width: `${point.confidence * 100}%`,
                                height: "100%",
                                background: point.confidence > 0.7 ? "var(--success)" : "var(--warning)",
                                borderRadius: 4,
                              }}
                            />
                          </div>
                          <span className="font-mono" style={{ color: "var(--text-dim)" }}>
                            {(point.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>
          Not enough transaction history for forecasting. Upload at least 3 months of data.
        </div>
      )}
    </div>
  );
}

export function VarianceTab({
  summary,
  annotations,
  onAnnotate,
}: {
  summary: ReportSummary;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
}) {
  const { currencyCode } = useCurrency();
  const reportCurrency = summary.base_currency || currencyCode;
  const matched = summary.budget_variance;
  const totalBudget = matched.reduce((sum, item) => sum + item.budget, 0);
  const totalActual = matched.reduce((sum, item) => sum + item.actual, 0);
  const overallPct = totalBudget > 0 ? (totalActual / totalBudget) * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetricCard label="Budgeted Spend" value={formatMoney(totalBudget, reportCurrency)} />
        <MetricCard label="Actual Spend" value={formatMoney(totalActual, reportCurrency)} />
        <MetricCard
          label="Variance"
          value={formatMoney(Math.abs(totalActual - totalBudget), reportCurrency)}
          trend={totalActual <= totalBudget ? "up" : "down"}
          subtext={`${overallPct.toFixed(0)}% of budget | ${totalActual <= totalBudget ? "Under" : "Over"}`}
        />
      </div>

      {matched.length > 0 ? (
        <div className="glass p-5 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
              Budget vs. Actuals
            </h3>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: totalActual <= totalBudget ? "var(--success)18" : "var(--danger)18",
                color: totalActual <= totalBudget ? "var(--success)" : "var(--danger)",
              }}
            >
              {matched.filter((item) => item.actual > item.budget && item.budget > 0).length} over budget
            </span>
          </div>
          {matched.map((item) => (
            <VarianceBar key={item.category} label={item.category} budget={item.budget} actual={item.actual} currencyCode={reportCurrency} />
          ))}
          <AnnotationBox section="variance" annotations={annotations} onSave={onAnnotate} />
        </div>
      ) : (
        <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>
          <MessageSquare size={20} className="mx-auto mb-2" />
          No budgets overlap the selected report period.
        </div>
      )}
    </div>
  );
}

export function TrendsTab({
  dashboard,
  loading,
  annotations,
  onAnnotate,
}: {
  dashboard: DashboardSummary | null;
  loading: boolean;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
}) {
  if (loading) return <ChartSkeleton height={280} />;
  if (!dashboard) {
    return <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>No trend data</div>;
  }

  const labels = (dashboard.monthly_periods || []).map(formatPeriodLabel);
  const momIncome = dashboard.monthly_income.map((value, index) =>
    index > 0 && dashboard.monthly_income[index - 1] > 0
      ? ((value - dashboard.monthly_income[index - 1]) / dashboard.monthly_income[index - 1]) * 100
      : 0
  );

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Income vs Expenses Trend
        </h3>
        <LineChart
          labels={labels}
          datasets={[
            { label: "Income", values: dashboard.monthly_income, color: "#5E9E7E" },
            { label: "Expenses", values: dashboard.monthly_expenses, color: "#C75050" },
          ]}
          height={280}
        />
        <AnnotationBox section="trends-chart" annotations={annotations} onSave={onAnnotate} />
      </div>

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
          Month-over-Month Changes
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {labels.slice(1).map((label, index) => {
            const change = momIncome[index + 1];
            return (
              <div key={label} className="p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</div>
                <div className="flex items-center gap-1 mt-1">
                  {change >= 0 ? <TrendingUp size={12} style={{ color: "var(--success)" }} /> : <TrendingDown size={12} style={{ color: "var(--danger)" }} />}
                  <span className="text-sm font-mono font-semibold" style={{ color: change >= 0 ? "var(--success)" : "var(--danger)" }}>
                    {change >= 0 ? "+" : ""}{change.toFixed(1)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function CategoriesTab({
  data,
  annotations,
  onAnnotate,
}: {
  data: ReportSummary;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
}) {
  const { currencyCode } = useCurrency();
  const reportCurrency = data.base_currency || currencyCode;
  const totalExpenses = data.expense_by_category.reduce((sum, item) => sum + item.total, 0);
  const topCategory = data.expense_by_category[0];
  const topPct = totalExpenses > 0 && topCategory ? ((topCategory.total / totalExpenses) * 100).toFixed(1) : "0";
  const sorted = [...data.expense_by_category].sort((left, right) => right.total - left.total);
  const maxCategory = sorted[0]?.total ?? 1;

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Expense Distribution
        </h3>
        <DonutChart data={data.expense_by_category.map((item) => ({ label: item.category, value: item.total }))} currencyCode={reportCurrency} />
        <AnnotationBox section="categories-donut" annotations={annotations} onSave={onAnnotate} />
      </div>

      {topCategory && (
        <div className="p-4 rounded-xl" style={{ background: "var(--accent-soft)", border: "1px solid var(--accent)33" }}>
          <div className="flex items-start gap-3">
            <Sparkles size={16} style={{ color: "var(--accent)", marginTop: 2 }} />
            <div>
              <div className="text-xs font-semibold mb-1" style={{ color: "var(--accent)" }}>
                AI Category Insight
              </div>
              <p className="text-xs" style={{ color: "var(--text)" }}>
                <strong>{topCategory.category}</strong> is your largest expense at {topPct}% of total spend ({formatMoney(topCategory.total, reportCurrency)}).
                {Number(topPct) > 40
                  ? " This is highly concentrated. Consider diversifying or renegotiating major spend."
                  : Number(topPct) > 25
                    ? " This is a meaningful concentration area worth monitoring."
                    : " Spending is relatively well distributed across categories."}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>
          Category Breakdown
        </h3>
        <div className="space-y-3">
          {sorted.map((item, index) => {
            const pct = totalExpenses > 0 ? (item.total / totalExpenses) * 100 : 0;
            const barWidth = (item.total / maxCategory) * 100;
            const color = ["#C9A962", "#6B8EC2", "#9B7CB8", "#D4965A", "#5E9E7E", "#C75050", "#8B7355", "#7BA3A3"][index % 8];
            return (
              <div key={item.category}>
                <div className="flex justify-between text-xs mb-1">
                  <span style={{ color: "var(--text)", fontWeight: 500 }}>{item.category}</span>
                  <span className="font-mono" style={{ color: "var(--text-muted)" }}>
                    {formatMoney(item.total, reportCurrency)} | {pct.toFixed(1)}% | {item.count} txns
                  </span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 8, background: "var(--surface-hover)" }}>
                  <div
                    style={{
                      width: `${barWidth}%`,
                      height: "100%",
                      background: `linear-gradient(90deg, ${color}, ${color}aa)`,
                      borderRadius: 8,
                      transition: "width 0.6s ease",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function CompareTab({
  periodA,
  periodB,
  labelA,
  labelB,
  loading,
  annotations,
  onAnnotate,
}: {
  periodA: ReportSummary | null;
  periodB: ReportSummary | null;
  labelA: string;
  labelB: string;
  loading: boolean;
  annotations: Annotation[];
  onAnnotate: (section: string, text: string) => void;
}) {
  if (loading) return <ChartSkeleton height={300} />;
  if (!periodA || !periodB) {
    return <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>Select two periods to compare</div>;
  }

  const reportCurrency = periodA.base_currency || periodB.base_currency || "USD";
  const rows = [
    { metric: "Total Income", periodA: periodA.total_income, periodB: periodB.total_income, format: "currency" as const, direction: "higher" as const },
    { metric: "Total Expenses", periodA: periodA.total_expenses, periodB: periodB.total_expenses, format: "currency" as const, direction: "lower" as const },
    { metric: "Net Cash Flow", periodA: periodA.net_cash_flow, periodB: periodB.net_cash_flow, format: "currency" as const, direction: "higher" as const },
    { metric: "Transactions", periodA: periodA.transaction_count, periodB: periodB.transaction_count, format: "number" as const, direction: "neutral" as const },
  ];

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Period Comparison
        </h3>
        <ComparisonTable rows={rows} periodALabel={labelA} periodBLabel={labelB} currencyCode={reportCurrency} />
        <AnnotationBox section="compare" annotations={annotations} onSave={onAnnotate} />
      </div>

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>
          Visual Comparison
        </h3>
        <BarChart
          data={[
            { label: `Income (${labelA})`, value: periodA.total_income, color: "#5E9E7E" },
            { label: `Income (${labelB})`, value: periodB.total_income, color: "#7BA3A3" },
            { label: `Expenses (${labelA})`, value: periodA.total_expenses, color: "#C75050" },
            { label: `Expenses (${labelB})`, value: periodB.total_expenses, color: "#D4965A" },
          ]}
          height={220}
          currencyCode={reportCurrency}
        />
      </div>
    </div>
  );
}
