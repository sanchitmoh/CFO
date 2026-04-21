"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { Budget } from "@/lib/types";
import { Plus, X, Wallet } from "lucide-react";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

export default function BudgetsPage() {
  const { getToken } = useAuth();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      const token = await getToken();
      const data = await api.getBudgets(token);
      setBudgets(data);
    } catch {
      /* show empty state */
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const totalBudget = budgets.reduce((s, b) => s + b.monthly_limit, 0);
  const totalSpent = budgets.reduce((s, b) => s + b.current_spend, 0);
  const overallPct = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Budgets</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Track spending limits and financial objectives</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? "Cancel" : "New Budget"}
        </button>
      </div>

      {showForm && <CreateBudgetForm onSuccess={() => { setShowForm(false); load(); }} />}

      {/* Overall progress */}
      {!loading && budgets.length > 0 && (
        <div className="glass p-5 animate-fade-up delay-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Overall Budget Utilization</span>
            <span className="text-sm font-bold" style={{ color: overallPct > 90 ? "var(--danger)" : overallPct > 75 ? "var(--warning)" : "var(--accent)" }}>
              {fmt(totalSpent)} / {fmt(totalBudget)} ({overallPct.toFixed(0)}%)
            </span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 8, background: "var(--bg)" }}>
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(overallPct, 100)}%`, background: overallPct > 90 ? "var(--danger)" : overallPct > 75 ? "var(--warning)" : "var(--accent)" }} />
          </div>
        </div>
      )}

      {/* Budget Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 160 }} />
          ))}
        </div>
      ) : budgets.length === 0 ? (
        <div className="glass p-12 text-center">
          <Wallet size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
          <p className="text-sm" style={{ color: "var(--text-dim)" }}>No budgets created yet. Create one to start tracking.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {budgets.map((b, i) => {
            const pct = b.monthly_limit > 0 ? Math.min((b.current_spend / b.monthly_limit) * 100, 100) : 0;
            const over = pct >= 100;
            const warn = pct >= 80 && !over;
            const barColor = over ? "var(--danger)" : warn ? "var(--warning)" : "var(--accent)";
            const remaining = b.monthly_limit - b.current_spend;

            return (
              <div key={b.id} className={`glass glass-hover p-5 animate-fade-up delay-${(i % 6) + 1}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>{b.category}</span>
                  {over && <span className="badge badge-critical">Over budget</span>}
                  {warn && <span className="badge badge-warning">Warning</span>}
                  {!over && !warn && pct < 50 && <span className="badge badge-income">On track</span>}
                </div>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-lg font-bold" style={{ color: barColor }}>{fmt(b.current_spend)}</span>
                  <span className="text-xs" style={{ color: "var(--text-dim)" }}>/ {fmt(b.monthly_limit)}</span>
                </div>
                <div className="mt-3 rounded-full overflow-hidden" style={{ height: 6, background: "var(--bg)" }}>
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: barColor }} />
                </div>
                <div className="flex items-center justify-between text-xs mt-2" style={{ color: "var(--text-dim)" }}>
                  <span>{pct.toFixed(0)}% used</span>
                  <span>{remaining >= 0 ? `${fmt(remaining)} remaining` : `${fmt(Math.abs(remaining))} over`}</span>
                </div>
                {b.month && (
                  <span className="badge mt-2" style={{ background: "var(--surface-hover)", color: "var(--text-dim)" }}>{b.month}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CreateBudgetForm({ onSuccess }: { onSuccess: () => void }) {
  const { getToken } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const fd = new FormData(e.currentTarget);
    try {
      const token = await getToken();
      await api.createBudget({
        category: fd.get("category") as string,
        limit_amount: parseFloat(fd.get("limit_amount") as string),
        period: fd.get("period") as string,
      }, token);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="glass p-6 animate-fade-up">
      <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>New Budget</h3>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <input name="category" placeholder="Category (e.g. Marketing)" required />
        <input name="limit_amount" type="number" step="0.01" min="0" placeholder="Budget Limit" required />
        <select name="period" required>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="yearly">Yearly</option>
        </select>
        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? "Creating…" : "Create Budget"}
        </button>
        {error && (
          <div className="sm:col-span-4 text-xs px-3 py-2 rounded-lg" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{error}</div>
        )}
      </form>
    </div>
  );
}
