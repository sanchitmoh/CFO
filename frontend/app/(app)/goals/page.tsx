"use client";

import { useState, useEffect, useCallback } from "react";
import { goalsApi } from "@/lib/api";
import {
  Target,
  Plus,
  TrendingUp,
  Calendar,
  CheckCircle,
  Clock,
  AlertCircle,
  Trash2,
  ChevronDown,
} from "lucide-react";

interface Goal {
  id: number | string;
  title: string;
  target_amount: number;
  current_amount: number;
  category: string;
  deadline: string;
  status: "on_track" | "at_risk" | "behind" | "completed";
  notes?: string;
}

const STATUS_META: Record<
  string,
  { label: string; color: string; bg: string; icon: React.ElementType }
> = {
  on_track: { label: "On Track", color: "var(--accent)", bg: "var(--accent-soft)", icon: TrendingUp },
  at_risk: { label: "At Risk", color: "var(--warning)", bg: "var(--warning-soft)", icon: AlertCircle },
  behind: { label: "Behind", color: "var(--danger)", bg: "var(--danger-soft)", icon: Clock },
  completed: { label: "Completed", color: "var(--accent)", bg: "var(--accent-soft)", icon: CheckCircle },
};

const DEMO_GOALS: Goal[] = [
  {
    id: 1,
    title: "Build Emergency Fund",
    target_amount: 50000,
    current_amount: 32000,
    category: "savings",
    deadline: "2025-06-30",
    status: "on_track",
    notes: "Targeting 3 months of operating expenses",
  },
  {
    id: 2,
    title: "Reduce Monthly Burn Rate",
    target_amount: 4000,
    current_amount: 5600,
    category: "cost_reduction",
    deadline: "2025-03-31",
    status: "at_risk",
    notes: "Need to cut marketing and overhead",
  },
  {
    id: 3,
    title: "Hit $35K MRR",
    target_amount: 35000,
    current_amount: 28000,
    category: "revenue",
    deadline: "2025-04-30",
    status: "on_track",
    notes: "Growing 12% MoM currently",
  },
  {
    id: 4,
    title: "Gross Margin > 65%",
    target_amount: 65,
    current_amount: 62,
    category: "profitability",
    deadline: "2025-06-30",
    status: "on_track",
    notes: "Currently at 62%, trending up",
  },
];

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>(DEMO_GOALS);
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<number | string | null>(null);
  const [form, setForm] = useState({
    title: "",
    target_amount: "",
    category: "savings",
    deadline: "",
    notes: "",
  });

  const loadGoals = useCallback(async () => {
    try {
      const data = await goalsApi.list();
      if (data && Array.isArray(data) && data.length > 0) {
        setGoals(
          data.map((g: any) => ({
            id: g.id,
            title: g.title || g.name || "",
            target_amount: g.target_amount || g.target || 0,
            current_amount: g.current_amount || g.current || 0,
            category: g.category || "savings",
            deadline: g.deadline || g.target_date || "",
            status: g.status || "on_track",
            notes: g.notes || g.description || "",
          }))
        );
      }
    } catch {
      // API unavailable — keep demo data
    }
  }, []);

  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  const createGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    const newGoal: Goal = {
      id: goals.length + 1,
      title: form.title,
      target_amount: Number(form.target_amount),
      current_amount: 0,
      category: form.category,
      deadline: form.deadline,
      status: "on_track",
      notes: form.notes,
    };

    try {
      const resp = await goalsApi.create({
        title: form.title,
        target_value: Number(form.target_amount),
        metric_type: form.category,
        deadline: form.deadline || undefined,
      });
      if (resp?.id) newGoal.id = resp.id;
    } catch {
      // API unavailable — add locally
    }

    setGoals((g) => [...g, newGoal]);
    setShowCreate(false);
    setForm({ title: "", target_amount: "", category: "savings", deadline: "", notes: "" });
  };

  const deleteGoal = async (id: number | string) => {
    try {
      await goalsApi.delete(String(id));
    } catch {
      // API unavailable — remove locally
    }
    setGoals((g) => g.filter((goal) => goal.id !== id));
  };

  const completedCount = goals.filter((g) => g.status === "completed").length;
  const onTrackCount = goals.filter((g) => g.status === "on_track").length;
  const atRiskCount = goals.filter((g) => g.status === "at_risk" || g.status === "behind").length;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            Financial Goals
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Track progress toward your financial targets
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={15} />
          New Goal
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 animate-fade-up delay-1">
        {[
          { label: "On Track", value: onTrackCount, color: "var(--accent)" },
          { label: "At Risk", value: atRiskCount, color: "var(--danger)" },
          { label: "Completed", value: completedCount, color: "var(--info)" },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass p-4 text-center">
            <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>
              {label}
            </p>
            <p className="text-3xl font-bold" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Goals list */}
      <div className="space-y-3 animate-fade-up delay-2">
        {goals.map((goal) => {
          const progress = goal.category === "cost_reduction"
            ? Math.max(0, Math.min(100, ((goal.target_amount / goal.current_amount) * 100)))
            : Math.max(0, Math.min(100, (goal.current_amount / goal.target_amount) * 100));
          const isComplete = goal.status === "completed";
          const meta = STATUS_META[goal.status] || STATUS_META.on_track;
          const StatusIcon = meta.icon;
          const isExpanded = expanded === goal.id;

          return (
            <div
              key={goal.id}
              className="glass transition-all"
              style={{ borderColor: isExpanded ? `${meta.color}33` : "var(--border)" }}
            >
              <button
                className="w-full text-left p-5 flex items-center justify-between gap-4"
                onClick={() => setExpanded(isExpanded ? null : goal.id)}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Icon */}
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      background: meta.bg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <StatusIcon size={16} style={{ color: meta.color }} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="text-sm font-semibold truncate"
                        style={{ color: "var(--text)" }}
                      >
                        {goal.title}
                      </span>
                      <span
                        className="badge"
                        style={{ background: meta.bg, color: meta.color }}
                      >
                        {meta.label}
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="mt-2 flex items-center gap-3">
                      <div
                        className="flex-1 rounded-full overflow-hidden"
                        style={{ height: 6, background: "var(--surface-hover)" }}
                      >
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${progress}%`,
                            background: meta.color,
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono font-semibold" style={{ color: meta.color }}>
                        {Math.round(progress)}%
                      </span>
                    </div>
                  </div>
                </div>

                <ChevronDown
                  size={16}
                  style={{
                    color: "var(--text-dim)",
                    transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s",
                    flexShrink: 0,
                  }}
                />
              </button>

              {isExpanded && (
                <div className="px-5 pb-5" style={{ borderTop: "1px solid var(--border)" }}>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Target</p>
                      <p className="font-bold mt-0.5" style={{ color: "var(--text)" }}>
                        {goal.category === "profitability" ? `${goal.target_amount}%` : fmt(goal.target_amount)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Current</p>
                      <p className="font-bold mt-0.5" style={{ color: meta.color }}>
                        {goal.category === "profitability" ? `${goal.current_amount}%` : fmt(goal.current_amount)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Category</p>
                      <p className="font-medium mt-0.5 capitalize text-sm" style={{ color: "var(--text-muted)" }}>
                        {goal.category.replace("_", " ")}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Deadline</p>
                      <p className="font-medium mt-0.5 text-sm flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
                        <Calendar size={12} />
                        {new Date(goal.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </p>
                    </div>
                  </div>

                  {goal.notes && (
                    <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: "var(--bg)", color: "var(--text-muted)" }}>
                      {goal.notes}
                    </div>
                  )}

                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={() => deleteGoal(goal.id)}
                      className="flex items-center gap-1.5 text-xs p-1.5 rounded transition-colors"
                      style={{ color: "var(--danger)" }}
                    >
                      <Trash2 size={12} />
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {goals.length === 0 && (
          <div className="glass p-10 text-center">
            <Target size={32} className="mx-auto mb-2" style={{ color: "var(--text-dim)" }} />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>No financial goals yet. Create your first one!</p>
          </div>
        )}
      </div>

      {/* Create Goal Modal */}
      {showCreate && (
        <div className="glass p-6 animate-fade-up">
          <h2 className="font-semibold text-sm mb-5 flex items-center gap-2" style={{ color: "var(--text)" }}>
            <Target size={16} style={{ color: "var(--accent)" }} />
            Create Financial Goal
          </h2>

          <form onSubmit={createGoal} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Goal Title
              </label>
              <input
                type="text"
                required
                placeholder="e.g., Build Emergency Fund"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Target Amount ($)
              </label>
              <input
                type="number"
                required
                min={1}
                placeholder="50000"
                value={form.target_amount}
                onChange={(e) => setForm((f) => ({ ...f, target_amount: e.target.value }))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Deadline
              </label>
              <input
                type="date"
                required
                value={form.deadline}
                onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Category
              </label>
              <select
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                className="w-full"
              >
                <option value="savings">Savings</option>
                <option value="revenue">Revenue</option>
                <option value="cost_reduction">Cost Reduction</option>
                <option value="profitability">Profitability</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Notes (optional)
              </label>
              <input
                type="text"
                placeholder="Additional context..."
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full"
              />
            </div>
            <div className="sm:col-span-2 flex gap-3 mt-1">
              <button type="submit" className="btn-primary flex items-center gap-2">
                <CheckCircle size={14} />
                Create Goal
              </button>
              <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
