"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";
import HealthScoreGauge from "@/components/HealthScoreGauge";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Wallet,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Flame,
  Clock,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const COLORS = ["#00E5CC", "#3B82F6", "#A855F7", "#FFB020", "#FF4D6A", "#6366F1"];

/** Compute a simple health score from dashboard data */
function computeHealthScore(d: DashboardSummary): number {
  const runway = d.runway_months ?? ((d.cash_balance ?? 0) / Math.max(d.burn_rate ?? d.total_expenses, 1));
  const runwayScore = Math.min(100, (runway / 6) * 100) * 0.4;
  const burnTrendScore = 60 * 0.2;
  const budgetScore = Math.max(0, 100 - Math.max(0, d.budget_utilization - 80) * 3) * 0.2;
  const revenueScore = Math.min(100, (d.net_cash_flow > 0 ? 80 : 40)) * 0.2;
  return Math.round(runwayScore + burnTrendScore + budgetScore + revenueScore);
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const token = await getToken();
      const d = await api.getDashboard(token);
      setData(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <DashboardSkeleton />;
  if (error || !data) return <EmptyState message={error} />;

  const healthScore = computeHealthScore(data);
  const runwayMonths = data.runway_months ?? ((data.cash_balance ?? 0) / Math.max(data.burn_rate ?? data.total_expenses, 1));
  const burnRate = data.burn_rate ?? data.total_expenses;

  const kpis = [
    { label: "Total Income", value: fmt(data.total_income), icon: TrendingUp, color: "var(--income)", bg: "var(--accent-soft)" },
    { label: "Total Expenses", value: fmt(data.total_expenses), icon: TrendingDown, color: "var(--expense)", bg: "var(--danger-soft)" },
    { label: "Net Cash Flow", value: fmt(data.net_cash_flow), icon: DollarSign, color: data.net_cash_flow >= 0 ? "var(--income)" : "var(--expense)", bg: data.net_cash_flow >= 0 ? "var(--accent-soft)" : "var(--danger-soft)" },
    { label: "Burn Rate", value: `${fmt(burnRate)}/mo`, icon: Flame, color: burnRate > 25000 ? "var(--danger)" : "var(--warning)", bg: burnRate > 25000 ? "var(--danger-soft)" : "var(--warning-soft)" },
    { label: "Cash Runway", value: `${runwayMonths.toFixed(1)} mo`, icon: Clock, color: runwayMonths >= 6 ? "var(--accent)" : runwayMonths >= 3 ? "var(--warning)" : "var(--danger)", bg: runwayMonths >= 6 ? "var(--accent-soft)" : runwayMonths >= 3 ? "var(--warning-soft)" : "var(--danger-soft)" },
    { label: "Budget Used", value: `${data.budget_utilization.toFixed(0)}%`, icon: Wallet, color: data.budget_utilization > 90 ? "var(--danger)" : data.budget_utilization > 75 ? "var(--warning)" : "var(--accent)", bg: data.budget_utilization > 90 ? "var(--danger-soft)" : data.budget_utilization > 75 ? "var(--warning-soft)" : "var(--accent-soft)" },
    { label: "Active Alerts", value: data.active_alerts, icon: AlertTriangle, color: data.active_alerts > 0 ? "var(--warning)" : "var(--accent)", bg: data.active_alerts > 0 ? "var(--warning-soft)" : "var(--accent-soft)" },
  ];

  const cashFlowData =
    data.monthly_income?.map((inc, i) => ({
      month: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i],
      income: inc,
      expenses: data.monthly_expenses?.[i] ?? 0,
    })) ?? [];

  const categoryData =
    data.top_categories?.map((c) => ({ name: c.category, value: c.amount })) ?? [];

  const recentTx = data.recent_transactions ?? [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Dashboard</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Financial overview and key metrics</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        {kpis.map((k, i) => (
          <div key={k.label} className={`glass glass-hover p-4 animate-fade-up delay-${i + 1}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium uppercase tracking-wider leading-tight" style={{ color: "var(--text-muted)" }}>{k.label}</span>
              <div className="flex items-center justify-center shrink-0" style={{ width: 28, height: 28, borderRadius: 8, background: k.bg }}>
                <k.icon size={14} style={{ color: k.color }} />
              </div>
            </div>
            <div className="text-lg font-bold" style={{ color: k.color }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Health Score + Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <HealthScoreGauge
            score={healthScore}
            runwayMonths={runwayMonths}
            burnTrend="increasing"
            budgetVariance={data.budget_utilization > 100 ? 40 : 75}
            revenueGrowth={12}
          />
        </div>

        {/* Cash Flow Chart */}
        <div className="lg:col-span-2 glass p-6 animate-fade-up delay-3">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Cash Flow Trend (6 months)</h3>
          {cashFlowData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={cashFlowData}>
                <defs>
                  <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00E5CC" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#00E5CC" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FF4D6A" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#FF4D6A" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2A42" />
                <XAxis dataKey="month" tick={{ fill: "#7A8BA7", fontSize: 11 }} />
                <YAxis tick={{ fill: "#7A8BA7", fontSize: 11 }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}K`} />
                <Tooltip
                  contentStyle={{ background: "#141A2B", border: "1px solid #1E2A42", borderRadius: 8, color: "#E8ECF4", fontSize: 12 }}
                  formatter={(v) => fmt(Number(v ?? 0))}
                />
                <Area type="monotone" dataKey="income" name="Income" stroke="#00E5CC" fill="url(#incomeGrad)" strokeWidth={2} />
                <Area type="monotone" dataKey="expenses" name="Expenses" stroke="#FF4D6A" fill="url(#expenseGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center" style={{ height: 240, color: "var(--text-dim)" }}>
              <p className="text-sm">Add transactions to see cash flow trends</p>
            </div>
          )}
        </div>
      </div>

      {/* Expense Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass p-6 animate-fade-up delay-4">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Expense Breakdown</h3>
          {categoryData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={categoryData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#141A2B", border: "1px solid #1E2A42", borderRadius: 8, fontSize: 12 }}
                    formatter={(v) => fmt(Number(v ?? 0))}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1.5">
                {categoryData.slice(0, 5).map((c, i) => (
                  <div key={c.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length] }} />
                      <span style={{ color: "var(--text-muted)" }}>{c.name}</span>
                    </div>
                    <span style={{ color: "var(--text)" }}>{fmt(c.value)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center" style={{ height: 200, color: "var(--text-dim)" }}>
              <p className="text-sm">No expense data yet</p>
            </div>
          )}
        </div>

        {/* Recent Transactions */}
        <div className="lg:col-span-2 glass p-6 animate-fade-up delay-5">
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>Recent Transactions</h3>
          {recentTx.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-left" style={{ color: "var(--text-dim)", borderBottom: "1px solid var(--border)" }}>
                    <th className="pb-3 pr-4">Date</th>
                    <th className="pb-3 pr-4">Description</th>
                    <th className="pb-3 pr-4 hidden sm:table-cell">Category</th>
                    <th className="pb-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTx.slice(0, 8).map((tx) => (
                    <tr key={tx.id} className="transition-colors" style={{ borderBottom: "1px solid var(--border)" }}>
                      <td className="py-3 pr-4" style={{ color: "var(--text-muted)" }}>
                        {new Date(tx.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </td>
                      <td className="py-3 pr-4" style={{ color: "var(--text)" }}>{tx.description}</td>
                      <td className="py-3 pr-4 hidden sm:table-cell">
                        <span className="badge badge-info">{tx.category}</span>
                      </td>
                      <td className="py-3 text-right font-medium">
                        <span className="flex items-center justify-end gap-1" style={{ color: tx.type === "income" ? "var(--income)" : "var(--expense)" }}>
                          {tx.type === "income" ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          {fmt(tx.amount)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>No transactions yet. Go to the Transactions page to add some.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <div className="skeleton" style={{ width: 160, height: 28 }} />
        <div className="skeleton mt-2" style={{ width: 240, height: 16 }} />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 80 }} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="skeleton" style={{ height: 240 }} />
        <div className="lg:col-span-2 skeleton" style={{ height: 240 }} />
      </div>
    </div>
  );
}

function EmptyState({ message }: { message?: string }) {
  return (
    <div className="max-w-7xl mx-auto">
      <div className="glass p-12 text-center">
        <DollarSign size={48} className="mx-auto mb-4" style={{ color: "var(--text-dim)" }} />
        <h2 className="text-lg font-semibold mb-2" style={{ color: "var(--text)" }}>Welcome to AI CFO</h2>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {message || "Start by adding transactions to see your financial overview."}
        </p>
      </div>
    </div>
  );
}
