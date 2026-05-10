"use client";

import { useState } from "react";
import {
  DonutChart, BarChart, LineChart, VarianceBar,
  ComparisonTable, MetricCard, ChartSkeleton,
} from "@/components/ReportCharts";
import {
  TrendingUp, TrendingDown, DollarSign,
  ArrowUpCircle, ArrowDownCircle, ChevronDown,
  ChevronRight, MessageSquare, StickyNote, Sparkles,
} from "lucide-react";
import type {
  ReportSummary, ForecastResponse, Budget,
  DashboardSummary, Transaction,
} from "@/lib/types";

// ═══════════════════════════════════════════════════════════════
// Shared types
// ═══════════════════════════════════════════════════════════════

interface Annotation { section: string; text: string; }
interface DrillDownState { category: string | null; transactions: Transaction[]; loading: boolean; }

// ═══════════════════════════════════════════════════════════════
// Annotation Widget
// ═══════════════════════════════════════════════════════════════

export function AnnotationBox({ section, annotations, onSave }: {
  section: string; annotations: Annotation[];
  onSave: (section: string, text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const existing = annotations.filter((a) => a.section === section);

  return (
    <div className="mt-3">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-dim)" }}>
        <StickyNote size={12} />
        {existing.length > 0 ? `${existing.length} note(s)` : "Add note"}
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {existing.map((a, i) => (
            <div key={i} className="text-xs p-2 rounded-lg" style={{ background: "var(--warning-soft)", color: "var(--warning)", border: "1px solid var(--warning)22" }}>
              {a.text}
            </div>
          ))}
          <div className="flex gap-2">
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Add a note…" className="flex-1 text-xs"
              onKeyDown={(e) => { if (e.key === "Enter" && text.trim()) { onSave(section, text.trim()); setText(""); } }} />
            <button onClick={() => { if (text.trim()) { onSave(section, text.trim()); setText(""); } }} className="btn-primary text-xs px-3 py-1">Save</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Tab: Cash Flow
// ═══════════════════════════════════════════════════════════════

export function CashFlowTab({ data, annotations, onAnnotate, onDrillDown, drillDown }: {
  data: ReportSummary; annotations: Annotation[];
  onAnnotate: (s: string, t: string) => void;
  onDrillDown: (category: string) => void; drillDown: DrillDownState;
}) {
  const net = data.total_income - data.total_expenses;
  const savingsRate = data.total_income > 0 ? (net / data.total_income) * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="Total Income" value={`$${data.total_income.toLocaleString()}`} icon={<ArrowUpCircle size={16} />} trend="up" subtext="Inflows" />
        <MetricCard label="Total Expenses" value={`$${data.total_expenses.toLocaleString()}`} icon={<ArrowDownCircle size={16} />} trend="down" subtext="Outflows" />
        <MetricCard label="Net Cash Flow" value={`$${net.toLocaleString()}`} icon={<DollarSign size={16} />} trend={net >= 0 ? "up" : "down"} subtext={net >= 0 ? "Positive" : "Negative"} />
        <MetricCard label="Savings Rate" value={`${savingsRate.toFixed(1)}%`} icon={<TrendingUp size={16} />} trend={savingsRate > 10 ? "up" : "down"} subtext={`${data.transaction_count} txns`} />
      </div>
      <AnnotationBox section="cashflow-kpi" annotations={annotations} onSave={onAnnotate} />

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Expense by Category</h3>
        {data.expense_by_category.length > 0 ? (
          <>
            <BarChart data={data.expense_by_category.map((c) => ({ label: c.category, value: c.total }))} height={180} />
            <div className="mt-4 space-y-1">
              {data.expense_by_category.map((c) => (
                <button key={c.category} onClick={() => onDrillDown(c.category)}
                  className="w-full flex items-center justify-between py-2 px-3 rounded-lg text-xs hover:opacity-80 transition-all"
                  style={{ background: drillDown.category === c.category ? "var(--accent-soft)" : "var(--bg)", border: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--text)" }}>{c.category}</span>
                  <span className="flex items-center gap-2">
                    <span className="font-mono" style={{ color: "var(--text-muted)" }}>${c.total.toLocaleString()} · {c.count} txns</span>
                    <ChevronRight size={12} style={{ color: "var(--text-dim)" }} />
                  </span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <div className="text-xs text-center py-8" style={{ color: "var(--text-dim)" }}>No category data for this period</div>
        )}
        <AnnotationBox section="cashflow-categories" annotations={annotations} onSave={onAnnotate} />
      </div>

      {drillDown.category && (
        <div className="glass p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Transactions: {drillDown.category}</h3>
          {drillDown.loading ? <ChartSkeleton height={100} /> : drillDown.transactions.length > 0 ? (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {drillDown.transactions.map((t) => (
                <div key={t.id} className="flex justify-between py-2 px-3 rounded-lg text-xs" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                  <div>
                    <span style={{ color: "var(--text)" }}>{t.description}</span>
                    <span className="ml-2" style={{ color: "var(--text-dim)" }}>{new Date(t.date).toLocaleDateString()}</span>
                  </div>
                  <span className="font-mono" style={{ color: t.type === "income" ? "var(--success)" : "var(--danger)" }}>
                    {t.type === "income" ? "+" : "-"}${t.amount.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-center py-4" style={{ color: "var(--text-dim)" }}>No transactions found</div>
          )}
        </div>
      )}

      {data.top_vendors.length > 0 && (
        <div className="glass p-5">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Top Vendors</h3>
          <div className="space-y-1">
            {data.top_vendors.map((v, i) => (
              <div key={i} className="flex justify-between py-2 px-3 rounded-lg text-xs" style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                <span style={{ color: "var(--text)" }}>{v.vendor}</span>
                <span className="font-mono" style={{ color: "var(--text-muted)" }}>${v.total.toLocaleString()} · {v.count} txns</span>
              </div>
            ))}
          </div>
          <AnnotationBox section="cashflow-vendors" annotations={annotations} onSave={onAnnotate} />
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Tab: Forecast
// ═══════════════════════════════════════════════════════════════

export function ForecastTab({ forecast, scenario, onScenarioChange, loading, annotations, onAnnotate }: {
  forecast: ForecastResponse | null; scenario: string;
  onScenarioChange: (s: string) => void; loading: boolean;
  annotations: Annotation[]; onAnnotate: (s: string, t: string) => void;
}) {
  const scenarios = ["optimistic", "base", "pessimistic"];
  const scenarioColors: Record<string, string> = { optimistic: "var(--success)", base: "var(--accent)", pessimistic: "var(--danger)" };

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        {scenarios.map((s) => (
          <button key={s} onClick={() => onScenarioChange(s)}
            className="px-4 py-1.5 text-xs font-medium rounded-lg transition-all capitalize"
            style={{
              background: scenario === s ? scenarioColors[s] : "var(--surface-hover)",
              color: scenario === s ? "#fff" : "var(--text)",
              border: `1px solid ${scenario === s ? scenarioColors[s] : "var(--border)"}`,
            }}>
            {s}
          </button>
        ))}
      </div>

      {loading ? <ChartSkeleton height={280} /> : forecast && forecast.data_points.length > 0 ? (
        <>
          <div className="glass p-5">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={14} style={{ color: scenarioColors[scenario] }} />
              <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {forecast.months_ahead}-Month Projection
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full capitalize" style={{ background: `${scenarioColors[scenario]}22`, color: scenarioColors[scenario] }}>
                {scenario}
              </span>
            </div>
            <LineChart
              labels={forecast.data_points.map((p) => p.period)}
              datasets={[
                { label: "Income", values: forecast.data_points.map((p) => p.projected_income), color: "#5E9E7E" },
                { label: "Expenses", values: forecast.data_points.map((p) => p.projected_expenses), color: "#C75050" },
                { label: "Net", values: forecast.data_points.map((p) => p.projected_net), color: "#C9A962" },
              ]}
              height={280}
            />
            <AnnotationBox section="forecast-chart" annotations={annotations} onSave={onAnnotate} />
          </div>

          {/* Confidence band summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {forecast.data_points.length > 0 && (() => {
              const last = forecast.data_points[forecast.data_points.length - 1];
              const cumNet = last.cumulative_net;
              const conf = last.confidence;
              return (
                <>
                  <MetricCard label="End-of-Period Net" value={`$${cumNet.toLocaleString()}`} trend={cumNet >= 0 ? "up" : "down"} subtext={`Cumulative`} />
                  <MetricCard label="Confidence" value={`${(conf * 100).toFixed(0)}%`} trend={conf > 0.7 ? "up" : "down"} subtext={conf > 0.7 ? "High" : "Low"} />
                  <MetricCard label="Monthly Avg Net" value={`$${Math.round(cumNet / forecast.data_points.length).toLocaleString()}`} trend={cumNet >= 0 ? "up" : "down"} subtext="Projected" />
                </>
              );
            })()}
          </div>

          <div className="glass p-5">
            <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Projection Data</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs" style={{ borderCollapse: "separate", borderSpacing: "0 3px" }}>
                <thead>
                  <tr>
                    {["Period", "Income", "Expenses", "Net", "Cumulative", "Confidence"].map((h) => (
                      <th key={h} className="text-left px-3 pb-2 font-semibold" style={{ color: "var(--text-muted)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {forecast.data_points.map((p, i) => (
                    <tr key={i} style={{ background: "var(--surface)" }}>
                      <td className="px-3 py-2 rounded-l-lg" style={{ color: "var(--text)" }}>{p.period}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--success)" }}>${p.projected_income.toLocaleString()}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--danger)" }}>${p.projected_expenses.toLocaleString()}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: p.projected_net >= 0 ? "var(--success)" : "var(--danger)" }}>${p.projected_net.toLocaleString()}</td>
                      <td className="px-3 py-2 font-mono" style={{ color: "var(--text)" }}>${p.cumulative_net.toLocaleString()}</td>
                      <td className="px-3 py-2 rounded-r-lg">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 rounded-full overflow-hidden" style={{ height: 4, background: "var(--surface-hover)" }}>
                            <div style={{ width: `${p.confidence * 100}%`, height: "100%", background: p.confidence > 0.7 ? "var(--success)" : "var(--warning)", borderRadius: 4 }} />
                          </div>
                          <span className="font-mono" style={{ color: "var(--text-dim)" }}>{(p.confidence * 100).toFixed(0)}%</span>
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

// ═══════════════════════════════════════════════════════════════
// Tab: Variance (Budget vs Actuals) — case-insensitive matching
// ═══════════════════════════════════════════════════════════════

export function VarianceTab({ summary, budgets, annotations, onAnnotate }: {
  summary: ReportSummary; budgets: Budget[];
  annotations: Annotation[]; onAnnotate: (s: string, t: string) => void;
}) {
  // Case-insensitive + trimmed matching
  const catMap = new Map(
    summary.expense_by_category.map((c) => [c.category.trim().toLowerCase(), c.total])
  );

  const matched = budgets.map((b) => {
    const key = b.category.trim().toLowerCase();
    return {
      category: b.category,
      budget: b.monthly_limit,
      actual: catMap.get(key) ?? b.current_spend ?? 0,
    };
  });

  const totalBudget = matched.reduce((s, m) => s + m.budget, 0);
  const totalActual = matched.reduce((s, m) => s + m.actual, 0);
  const overallPct = totalBudget > 0 ? (totalActual / totalBudget) * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total Budget" value={`$${totalBudget.toLocaleString()}`} />
        <MetricCard label="Total Actual" value={`$${totalActual.toLocaleString()}`} />
        <MetricCard
          label="Variance"
          value={`$${Math.abs(totalActual - totalBudget).toLocaleString()}`}
          trend={totalActual <= totalBudget ? "up" : "down"}
          subtext={`${overallPct.toFixed(0)}% of budget · ${totalActual <= totalBudget ? "Under" : "Over"}`}
        />
      </div>

      {matched.length > 0 ? (
        <div className="glass p-5 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Budget vs. Actuals</h3>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              background: totalActual <= totalBudget ? "var(--success)18" : "var(--danger)18",
              color: totalActual <= totalBudget ? "var(--success)" : "var(--danger)",
            }}>
              {matched.filter(m => m.actual > m.budget).length} over budget
            </span>
          </div>
          {matched.map((m) => (
            <VarianceBar key={m.category} label={m.category} budget={m.budget} actual={m.actual} />
          ))}
          <AnnotationBox section="variance" annotations={annotations} onSave={onAnnotate} />
        </div>
      ) : (
        <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>
          <MessageSquare size={20} className="mx-auto mb-2" />
          No budgets set. Create budgets on the Budgets page to see variance analysis.
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Tab: Trends
// ═══════════════════════════════════════════════════════════════

export function TrendsTab({ dashboard, loading, annotations, onAnnotate }: {
  dashboard: DashboardSummary | null; loading: boolean;
  annotations: Annotation[]; onAnnotate: (s: string, t: string) => void;
}) {
  if (loading) return <ChartSkeleton height={280} />;
  if (!dashboard) return <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>No trend data</div>;

  const months = dashboard.monthly_income.length;
  const now = new Date();
  const labels = Array.from({ length: months }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - months + 1 + i, 1);
    return d.toLocaleDateString("en-US", { month: "short" });
  });

  const momIncome = dashboard.monthly_income.map((v, i) =>
    i > 0 && dashboard.monthly_income[i - 1] > 0
      ? ((v - dashboard.monthly_income[i - 1]) / dashboard.monthly_income[i - 1]) * 100
      : 0
  );

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Income vs Expenses Trend</h3>
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
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Month-over-Month Changes</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {labels.slice(1).map((l, i) => {
            const change = momIncome[i + 1];
            return (
              <div key={l} className="p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>{l}</div>
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

// ═══════════════════════════════════════════════════════════════
// Tab: Categories (AI Insights) — enhanced donut + horizontal bars
// ═══════════════════════════════════════════════════════════════

export function CategoriesTab({ data, annotations, onAnnotate }: {
  data: ReportSummary; annotations: Annotation[];
  onAnnotate: (s: string, t: string) => void;
}) {
  const totalExp = data.expense_by_category.reduce((s, c) => s + c.total, 0);
  const top = data.expense_by_category[0];
  const topPct = totalExp > 0 && top ? ((top.total / totalExp) * 100).toFixed(1) : "0";
  const sorted = [...data.expense_by_category].sort((a, b) => b.total - a.total);
  const maxCat = sorted[0]?.total ?? 1;

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Expense Distribution</h3>
        <DonutChart data={data.expense_by_category.map((c) => ({ label: c.category, value: c.total }))} />
        <AnnotationBox section="categories-donut" annotations={annotations} onSave={onAnnotate} />
      </div>

      {top && (
        <div className="p-4 rounded-xl" style={{ background: "var(--accent-soft)", border: "1px solid var(--accent)33" }}>
          <div className="flex items-start gap-3">
            <Sparkles size={16} style={{ color: "var(--accent)", marginTop: 2 }} />
            <div>
              <div className="text-xs font-semibold mb-1" style={{ color: "var(--accent)" }}>AI Category Insight</div>
              <p className="text-xs" style={{ color: "var(--text)" }}>
                <strong>{top.category}</strong> is your largest expense at {topPct}% of total spend (${top.total.toLocaleString()}).
                {Number(topPct) > 40
                  ? " This is highly concentrated — consider diversifying or negotiating better rates."
                  : Number(topPct) > 25
                    ? " This is a significant portion. Monitor for cost optimization opportunities."
                    : " Your spending is well-distributed across categories."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Horizontal bar breakdown */}
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text)" }}>Category Breakdown</h3>
        <div className="space-y-3">
          {sorted.map((c, i) => {
            const pct = totalExp > 0 ? (c.total / totalExp) * 100 : 0;
            const barW = (c.total / maxCat) * 100;
            const color = ["#C9A962", "#6B8EC2", "#9B7CB8", "#D4965A", "#5E9E7E", "#C75050", "#8B7355", "#7BA3A3"][i % 8];
            return (
              <div key={c.category}>
                <div className="flex justify-between text-xs mb-1">
                  <span style={{ color: "var(--text)", fontWeight: 500 }}>{c.category}</span>
                  <span className="font-mono" style={{ color: "var(--text-muted)" }}>
                    ${c.total.toLocaleString()} · {pct.toFixed(1)}% · {c.count} txns
                  </span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 8, background: "var(--surface-hover)" }}>
                  <div style={{ width: `${barW}%`, height: "100%", background: `linear-gradient(90deg, ${color}, ${color}aa)`, borderRadius: 8, transition: "width 0.6s ease" }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Tab: Compare (Side-by-Side Periods)
// ═══════════════════════════════════════════════════════════════

export function CompareTab({ periodA, periodB, labelA, labelB, loading, annotations, onAnnotate }: {
  periodA: ReportSummary | null; periodB: ReportSummary | null;
  labelA: string; labelB: string; loading: boolean;
  annotations: Annotation[]; onAnnotate: (s: string, t: string) => void;
}) {
  if (loading) return <ChartSkeleton height={300} />;
  if (!periodA || !periodB) {
    return <div className="glass p-8 text-center text-sm" style={{ color: "var(--text-dim)" }}>Select two periods to compare</div>;
  }

  const rows = [
    { metric: "Total Income", periodA: periodA.total_income, periodB: periodB.total_income, format: "currency" as const },
    { metric: "Total Expenses", periodA: periodA.total_expenses, periodB: periodB.total_expenses, format: "currency" as const },
    { metric: "Net Cash Flow", periodA: periodA.net_cash_flow, periodB: periodB.net_cash_flow, format: "currency" as const },
    { metric: "Transactions", periodA: periodA.transaction_count, periodB: periodB.transaction_count, format: "number" as const },
  ];

  return (
    <div className="space-y-5">
      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Period Comparison</h3>
        <ComparisonTable rows={rows} periodALabel={labelA} periodBLabel={labelB} />
        <AnnotationBox section="compare" annotations={annotations} onSave={onAnnotate} />
      </div>

      <div className="glass p-5">
        <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Visual Comparison</h3>
        <BarChart
          data={[
            { label: `Income (${labelA})`, value: periodA.total_income, color: "#5E9E7E" },
            { label: `Income (${labelB})`, value: periodB.total_income, color: "#7BA3A3" },
            { label: `Expense (${labelA})`, value: periodA.total_expenses, color: "#C75050" },
            { label: `Expense (${labelB})`, value: periodB.total_expenses, color: "#D4965A" },
          ]}
          height={220}
        />
      </div>
    </div>
  );
}
