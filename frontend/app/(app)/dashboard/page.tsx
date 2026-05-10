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
  ComposedChart, Bar, Line,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
  PieChart, Pie, Cell,
} from "recharts";

const fmtShort = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 1, notation: "compact" }).format(n);

const DashTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "rgba(8,8,8,0.96)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 12, padding: "12px 16px", minWidth: 180, boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}>
      <p style={{ color: "#9A948A", fontSize: 11, fontWeight: 600, marginBottom: 8 }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ display: "flex", justifyContent: "space-between", gap: 20, marginBottom: 3 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: p.color }} />
            <span style={{ color: "#9A948A", fontSize: 11 }}>{p.name}</span>
          </div>
          <span style={{ color: "#E8E4DE", fontSize: 11, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const COLORS = ["#C9A962", "#6B8EC2", "#9B7CB8", "#D4965A", "#C75050", "#5E9E7E"];

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
    data.monthly_income?.map((inc, i) => {
      const exp = data.monthly_expenses?.[i] ?? 0;
      return {
        month: `Month ${i + 1}`,
        income: inc,
        expenses: exp,
        net: inc - exp,
      };
    }).filter(d => d.income > 0 || d.expenses > 0) ?? [];

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
      <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
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
          <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>Cash Flow Trend</h3>
          <p className="text-xs mb-4" style={{ color: "var(--text-dim)" }}>{cashFlowData.length} months with activity</p>
          {cashFlowData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220} minWidth={300}>
              <ComposedChart data={cashFlowData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5E9E7E" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#5E9E7E" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#C75050" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#C75050" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: "#5C5750", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#5C5750", fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => fmtShort(v)} width={60} />
                <Tooltip content={<DashTooltip />} cursor={{ stroke: "rgba(255,255,255,0.04)" }} />
                <Legend wrapperStyle={{ fontSize: 10, paddingTop: 8 }}
                  formatter={(v: string) => <span style={{ color: "#9A948A" }}>{v}</span>} />
                <Bar dataKey="income" name="Income" fill="#5E9E7E" radius={[3,3,0,0]} barSize={14} fillOpacity={0.85} />
                <Bar dataKey="expenses" name="Expenses" fill="#C75050" radius={[3,3,0,0]} barSize={14} fillOpacity={0.85} />
                <Line type="monotone" dataKey="net" name="Net" stroke="#C9A962" strokeWidth={2.5}
                  dot={{ r: 3, fill: "#C9A962", strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: "#C9A962", stroke: "#E8E4DE", strokeWidth: 2 }} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              </ComposedChart>
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
              <ResponsiveContainer width="100%" height={160} minWidth={200}>
                <PieChart>
                  <Pie data={categoryData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#111111", border: "1px solid #232323", borderRadius: 8, fontSize: 12 }}
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
            <div className="overflow-x-auto -mx-2 px-2" style={{ WebkitOverflowScrolling: "touch" }}>
              <table className="w-full text-sm" style={{ minWidth: 480 }}>
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
      <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
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
