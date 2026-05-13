"use client";

import { useState, useEffect, useCallback } from "react";
import type { Goal } from "@/lib/types";
import { goalsApi } from "@/lib/api";
import {
  Target,
  Plus,
  TrendingUp,
  Calendar,
  CheckCircle,
  AlertCircle,
  Trash2,
  ChevronDown,
  type LucideIcon,
  Ban,
  Save,
} from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";

type GoalCardStatus = "active" | "completed" | "abandoned";

const STATUS_META: Record<
  GoalCardStatus,
  { label: string; color: string; bg: string; icon: LucideIcon }
> = {
  active: { label: "Active", color: "var(--accent)", bg: "var(--accent-soft)", icon: TrendingUp },
  completed: { label: "Completed", color: "var(--accent)", bg: "var(--accent-soft)", icon: CheckCircle },
  abandoned: { label: "Abandoned", color: "var(--danger)", bg: "var(--danger-soft)", icon: Ban },
};

function getGoalCardStatus(goal: Goal): GoalCardStatus {
  if (goal.status === "abandoned") {
    return "abandoned";
  }
  if (goal.status === "completed" || goal.progress_pct >= 100) {
    return "completed";
  }
  return "active";
}

function formatGoalValue(goal: Goal, value: number, fmt: (amount: number) => string) {
  if (goal.metric_type === "expense_reduction") {
    return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
  }
  return fmt(value);
}

export default function GoalsPage() {
  const { formatAmount: fmt } = useCurrency();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [savingGoalId, setSavingGoalId] = useState<string | null>(null);
  const [deletingGoalId, setDeletingGoalId] = useState<string | null>(null);
  const [progressDrafts, setProgressDrafts] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    title: "",
    target_value: "",
    current_value: "",
    metric_type: "savings",
    deadline: "",
  });

  const loadGoals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await goalsApi.list();
      setGoals(data);
      setProgressDrafts(
        Object.fromEntries(
          data.map((goal) => [goal.id, String(goal.current_value)])
        )
      );
    } catch {
      setError("Unable to load goals. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGoals();
  }, [loadGoals]);

  const createGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await goalsApi.create({
        title: form.title,
        target_value: Number(form.target_value),
        current_value: form.current_value ? Number(form.current_value) : undefined,
        metric_type: form.metric_type,
        deadline: form.deadline || undefined,
      });
      await loadGoals();
      setShowCreate(false);
      setForm({
        title: "",
        target_value: "",
        current_value: "",
        metric_type: "savings",
        deadline: "",
      });
    } catch {
      setError("Unable to create goal. Please review the values and try again.");
    }
  };

  const updateGoalProgress = async (goal: Goal) => {
    const draft = progressDrafts[goal.id];
    const value = Number(draft);
    if (Number.isNaN(value) || value < 0) {
      setError("Current progress must be a non-negative number.");
      return;
    }

    try {
      setSavingGoalId(goal.id);
      const updated = await goalsApi.update(goal.id, { current_value: value });
      setGoals((current) => current.map((item) => (item.id === goal.id ? updated : item)));
      setProgressDrafts((current) => ({ ...current, [goal.id]: String(updated.current_value) }));
    } catch {
      setError("Unable to update goal progress right now.");
    } finally {
      setSavingGoalId(null);
    }
  };

  const deleteGoal = async (id: string) => {
    try {
      setDeletingGoalId(id);
      await goalsApi.delete(id);
      setGoals((current) => current.filter((goal) => goal.id !== id));
      setProgressDrafts((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
    } catch {
      setError("Unable to delete the goal right now.");
    } finally {
      setDeletingGoalId(null);
    }
  };

  const completedCount = goals.filter((goal) => getGoalCardStatus(goal) === "completed").length;
  const activeCount = goals.filter((goal) => getGoalCardStatus(goal) === "active").length;
  const abandonedCount = goals.filter((goal) => getGoalCardStatus(goal) === "abandoned").length;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {error && (
        <div className="glass p-4 flex items-center gap-3 animate-fade-up" style={{ borderColor: "var(--danger)44", background: "var(--danger-soft)" }}>
          <AlertCircle size={18} style={{ color: "var(--danger)", flexShrink: 0 }} />
          <p className="text-sm" style={{ color: "var(--danger)" }}>{error}</p>
          <button onClick={loadGoals} className="ml-auto text-xs font-medium px-3 py-1.5 rounded-lg" style={{ background: "var(--danger)", color: "#fff" }}>Retry</button>
        </div>
      )}
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
          { label: "Active", value: activeCount, color: "var(--accent)" },
          { label: "Completed", value: completedCount, color: "var(--info)" },
          { label: "Abandoned", value: abandonedCount, color: "var(--danger)" },
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
        {loading && (
          <div className="grid grid-cols-1 gap-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="skeleton" style={{ height: 128 }} />
            ))}
          </div>
        )}

        {goals.map((goal) => {
          const cardStatus = getGoalCardStatus(goal);
          const progress = goal.progress_pct;
          const meta = STATUS_META[cardStatus];
          const StatusIcon = meta.icon;
          const isExpanded = expanded === goal.id;
          const progressDraft = progressDrafts[goal.id] ?? String(goal.current_value);
          const canEditProgress = !goal.is_auto_tracked && goal.status !== "abandoned";

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
                        {progress.toFixed(1)}%
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
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Target</p>
                      <p className="font-bold mt-0.5" style={{ color: "var(--text)" }}>
                        {formatGoalValue(goal, goal.target_value, fmt)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Current</p>
                      <p className="font-bold mt-0.5" style={{ color: meta.color }}>
                        {formatGoalValue(goal, goal.current_value, fmt)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Metric</p>
                      <p className="font-medium mt-0.5 capitalize text-sm" style={{ color: "var(--text-muted)" }}>
                        {goal.metric_type.replace("_", " ")}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>Deadline</p>
                      {goal.deadline ? (
                        <p className="font-medium mt-0.5 text-sm flex items-center gap-1" style={{ color: "var(--text-muted)" }}>
                          <Calendar size={12} />
                          {new Date(goal.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                        </p>
                      ) : (
                        <p className="font-medium mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
                          No deadline
                        </p>
                      )}
                    </div>
                  </div>

                  {goal.is_auto_tracked && (
                    <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: "var(--bg)", color: "var(--text-muted)" }}>
                      This goal auto-tracks from current-month revenue transactions.
                    </div>
                  )}

                  {canEditProgress && (
                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3">
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={progressDraft}
                        onChange={(e) =>
                          setProgressDrafts((current) => ({
                            ...current,
                            [goal.id]: e.target.value,
                          }))
                        }
                        placeholder={goal.metric_type === "expense_reduction" ? "Current percentage" : "Current value"}
                      />
                      <button
                        type="button"
                        onClick={() => updateGoalProgress(goal)}
                        disabled={savingGoalId === goal.id}
                        className="btn-primary flex items-center justify-center gap-2"
                      >
                        <Save size={14} />
                        {savingGoalId === goal.id ? "Saving..." : "Save Progress"}
                      </button>
                    </div>
                  )}

                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={() => deleteGoal(goal.id)}
                      disabled={deletingGoalId === goal.id}
                      className="flex items-center gap-1.5 text-xs p-1.5 rounded transition-colors"
                      style={{ color: "var(--danger)" }}
                    >
                      <Trash2 size={12} />
                      {deletingGoalId === goal.id ? "Removing..." : "Remove"}
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
                Target Value
              </label>
              <input
                type="number"
                required
                min={1}
                placeholder="50000"
                value={form.target_value}
                onChange={(e) => setForm((f) => ({ ...f, target_value: e.target.value }))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Current Value (optional)
              </label>
              <input
                type="number"
                min={0}
                placeholder="Leave blank to start at zero"
                value={form.current_value}
                onChange={(e) => setForm((f) => ({ ...f, current_value: e.target.value }))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Deadline
              </label>
              <input
                type="date"
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
                value={form.metric_type}
                onChange={(e) => setForm((f) => ({ ...f, metric_type: e.target.value }))}
                className="w-full"
              >
                <option value="savings">Savings</option>
                <option value="revenue">Revenue</option>
                <option value="expense_reduction">Expense Reduction</option>
              </select>
            </div>
            <div className="sm:col-span-2 text-xs" style={{ color: "var(--text-muted)" }}>
              Leave the current value at zero for revenue goals if you want them to auto-track from current-month income.
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
