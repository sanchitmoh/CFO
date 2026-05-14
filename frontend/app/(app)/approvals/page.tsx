"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Check, CheckSquare, Plus, ShieldCheck, Sparkles, X, XCircle } from "lucide-react";

import { useCurrency } from "@/components/CurrencyContext";
import { findMatchingPolicy, parsePolicyCategories } from "@/lib/approvals";
import { approvalsApi, transactionsApi } from "@/lib/api";
import type { ApprovalPolicy, ApprovalPolicyCreate, ExpenseApproval, Transaction } from "@/lib/types";

const ROLE_OPTIONS = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Admin" },
  { value: "cfo", label: "CFO" },
  { value: "accountant", label: "Accountant" },
];

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

function formatPolicyRange(
  formatAmount: (value: number) => string,
  policy: Pick<ApprovalPolicy, "min_amount" | "max_amount">,
) {
  const floor = formatAmount(policy.min_amount);
  if (policy.max_amount == null) {
    return `${floor}+`;
  }
  return `${floor} - ${formatAmount(policy.max_amount)}`;
}

function formatDate(value?: string) {
  if (!value) {
    return "No date";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value.slice(0, 10) : dateFormatter.format(parsed);
}

function shortId(value?: string) {
  return value ? `${value.slice(0, 8)}...` : "Unknown";
}

function getApprovalTone(status: ExpenseApproval["status"]) {
  if (status === "approved" || status === "auto_approved") {
    return {
      label: status === "auto_approved" ? "Auto-approved" : "Approved",
      background: "var(--success-soft)",
      color: "var(--success)",
    };
  }

  if (status === "rejected") {
    return {
      label: "Rejected",
      background: "var(--danger-soft)",
      color: "var(--danger)",
    };
  }

  return {
    label: "Pending",
    background: "var(--warning-soft)",
    color: "var(--warning)",
  };
}

function replaceCategoriesText(currentText: string, category: string) {
  const nextCategories = parsePolicyCategories(currentText);
  const exists = nextCategories.includes(category);
  const updated = exists
    ? nextCategories.filter((item) => item !== category)
    : [...nextCategories, category];
  return updated.join(", ");
}

export default function ApprovalsPage() {
  const { formatAmount } = useCurrency();
  const [approvals, setApprovals] = useState<ExpenseApproval[]>([]);
  const [policies, setPolicies] = useState<ApprovalPolicy[]>([]);
  const [recentExpenses, setRecentExpenses] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"queue" | "all" | "policies">("queue");
  const [showPolicy, setShowPolicy] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [actingOnApprovalId, setActingOnApprovalId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [policyForm, setPolicyForm] = useState({
    name: "",
    minAmount: "",
    maxAmount: "",
    categoriesText: "",
    autoApproveRoles: [] as string[],
  });

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [approvalList, policyList, transactionPage] = await Promise.all([
        approvalsApi.list(),
        approvalsApi.listPolicies(),
        transactionsApi.list({ per_page: 100, type: "expense" }),
      ]);
      setApprovals(approvalList);
      setPolicies(policyList);
      setRecentExpenses(transactionPage.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleApprove = async (id: string) => {
    setError(null);
    setNotice(null);
    setActingOnApprovalId(id);
    try {
      await approvalsApi.approve(id, { notes: "Approved from approvals queue" });
      setNotice("Approval decision saved.");
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Failed to approve expense");
    } finally {
      setActingOnApprovalId(null);
    }
  };

  const handleReject = async (id: string) => {
    setError(null);
    setNotice(null);
    setActingOnApprovalId(id);
    try {
      await approvalsApi.reject(id, { rejection_reason: "Rejected from approvals queue" });
      setNotice("Rejection recorded.");
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Failed to reject expense");
    } finally {
      setActingOnApprovalId(null);
    }
  };

  const handleCreatePolicy = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingPolicy(true);
    setError(null);
    setNotice(null);

    const parsedCategories = parsePolicyCategories(policyForm.categoriesText);
    const payload: ApprovalPolicyCreate = {
      name: policyForm.name.trim(),
      min_amount: Number(policyForm.minAmount),
      required_approvers: 1,
      ...(policyForm.maxAmount ? { max_amount: Number(policyForm.maxAmount) } : {}),
      ...(parsedCategories.length ? { categories: parsedCategories } : {}),
      ...(policyForm.autoApproveRoles.length
        ? { auto_approve_roles: policyForm.autoApproveRoles }
        : {}),
    };

    try {
      await approvalsApi.createPolicy(payload);
      setNotice("Policy created and ready to match new expenses.");
      setPolicyForm({
        name: "",
        minAmount: "",
        maxAmount: "",
        categoriesText: "",
        autoApproveRoles: [],
      });
      setShowPolicy(false);
      setTab("policies");
      await load();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to create policy");
    } finally {
      setSavingPolicy(false);
    }
  };

  const pendingApprovals = approvals.filter((approval) => approval.status === "pending");
  const visibleApprovals = tab === "queue" ? pendingApprovals : approvals;
  const activePolicies = policies.filter((policy) => policy.is_active);
  const coveredExpenses = recentExpenses.filter((expense) => findMatchingPolicy(activePolicies, expense));
  const uncoveredExpenses = recentExpenses.filter((expense) => !findMatchingPolicy(activePolicies, expense));
  const suggestedCategories = Array.from(new Set(recentExpenses.map((expense) => expense.category))).slice(0, 8);
  const selectedCategories = parsePolicyCategories(policyForm.categoriesText);
  const autoApprovedCount = approvals.filter((approval) => approval.status === "auto_approved").length;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <section
        className="glass animate-fade-up overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(17, 17, 17, 0.98), rgba(8, 8, 8, 0.94))",
          borderColor: "rgba(201, 169, 98, 0.16)",
        }}
      >
        <div className="grid gap-6 p-6 lg:grid-cols-[1.35fr,0.65fr]">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em]" style={{ borderColor: "rgba(201, 169, 98, 0.18)", color: "var(--accent)" }}>
              <ShieldCheck size={14} />
              Approval Control Room
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold sm:text-4xl" style={{ color: "var(--text)" }}>
                Expense approvals with real policy context
              </h1>
              <p className="max-w-3xl text-sm leading-7 sm:text-base" style={{ color: "var(--text-muted)" }}>
                Policies now map cleanly to recent expense categories, pending approvals surface with usable detail, and transactions can be routed into review without leaving the workflow behind.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setShowPolicy((current) => !current)}
                className="btn-primary inline-flex items-center justify-center gap-2"
              >
                {showPolicy ? <X size={16} /> : <Plus size={16} />}
                {showPolicy ? "Close Policy Studio" : "Open Policy Studio"}
              </button>
              <Link href="/transactions" className="btn-secondary inline-flex items-center justify-center gap-2">
                Review Transactions
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255, 255, 255, 0.02)" }}>
              <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Pending queue</p>
              <p className="mt-3 text-3xl font-semibold" style={{ color: "var(--text)" }}>{pendingApprovals.length}</p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>Expenses currently waiting for a human decision.</p>
            </div>
            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255, 255, 255, 0.02)" }}>
              <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Policy coverage</p>
              <p className="mt-3 text-3xl font-semibold" style={{ color: "var(--text)" }}>
                {recentExpenses.length ? `${Math.round((coveredExpenses.length / recentExpenses.length) * 100)}%` : "0%"}
              </p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                Recent expense transactions that already match an active policy.
              </p>
            </div>
            <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255, 255, 255, 0.02)" }}>
              <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Auto-approved</p>
              <p className="mt-3 text-3xl font-semibold" style={{ color: "var(--text)" }}>{autoApprovedCount}</p>
              <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                Requests completed instantly because the requester matched policy roles.
              </p>
            </div>
          </div>
        </div>
      </section>

      {error ? (
        <div className="glass animate-fade-up px-4 py-3 text-sm" style={{ color: "var(--danger)", borderColor: "rgba(199, 80, 80, 0.35)", background: "rgba(199, 80, 80, 0.08)" }}>
          {error}
        </div>
      ) : null}

      {notice ? (
        <div className="glass animate-fade-up px-4 py-3 text-sm" style={{ color: "var(--success)", borderColor: "rgba(94, 158, 126, 0.3)", background: "rgba(94, 158, 126, 0.08)" }}>
          {notice}
        </div>
      ) : null}

      {showPolicy ? (
        <section className="glass animate-fade-up overflow-hidden">
          <div className="grid gap-0 xl:grid-cols-[1.15fr,0.85fr]">
            <div className="p-6">
              <div className="mb-6 space-y-2">
                <p className="text-xs uppercase tracking-[0.24em]" style={{ color: "var(--accent)" }}>Policy Studio</p>
                <h2 className="text-2xl font-semibold" style={{ color: "var(--text)" }}>Build a policy that matches the rest of the product</h2>
                <p className="text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                  Categories are pulled from recent expense activity so policy rules line up with real transactions instead of isolated form guesses.
                </p>
              </div>

              <form onSubmit={handleCreatePolicy} className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Policy name</span>
                    <input
                      name="name"
                      value={policyForm.name}
                      onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))}
                      placeholder="Travel over 5k"
                      required
                    />
                  </label>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Minimum amount</span>
                      <input
                        name="min_amount"
                        type="number"
                        step="0.01"
                        min="0"
                        value={policyForm.minAmount}
                        onChange={(event) => setPolicyForm((current) => ({ ...current, minAmount: event.target.value }))}
                        placeholder="5000"
                        required
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Maximum amount</span>
                      <input
                        name="max_amount"
                        type="number"
                        step="0.01"
                        min="0"
                        value={policyForm.maxAmount}
                        onChange={(event) => setPolicyForm((current) => ({ ...current, maxAmount: event.target.value }))}
                        placeholder="Optional cap"
                      />
                    </label>
                  </div>
                </div>

                <label className="space-y-2">
                  <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Category scope</span>
                  <input
                    value={policyForm.categoriesText}
                    onChange={(event) => setPolicyForm((current) => ({ ...current, categoriesText: event.target.value }))}
                    placeholder="Travel, Software, Marketing"
                  />
                  <p className="text-xs leading-6" style={{ color: "var(--text-dim)" }}>
                    Leave this blank to match any expense category. Use commas to scope the rule.
                  </p>
                </label>

                {suggestedCategories.length ? (
                  <div className="space-y-2">
                    <p className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--text-dim)" }}>Suggested from recent expenses</p>
                    <div className="flex flex-wrap gap-2">
                      {suggestedCategories.map((category) => {
                        const selected = selectedCategories.includes(category);
                        return (
                          <button
                            key={category}
                            type="button"
                            onClick={() =>
                              setPolicyForm((current) => ({
                                ...current,
                                categoriesText: replaceCategoriesText(current.categoriesText, category),
                              }))
                            }
                            className="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                            style={{
                              borderColor: selected ? "var(--accent)" : "var(--border)",
                              background: selected ? "var(--accent-soft)" : "transparent",
                              color: selected ? "var(--accent)" : "var(--text-muted)",
                            }}
                          >
                            {category}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null}

                <div className="space-y-2">
                  <span className="text-sm font-medium" style={{ color: "var(--text)" }}>Auto-approve roles</span>
                  <div className="flex flex-wrap gap-2">
                    {ROLE_OPTIONS.map((role) => {
                      const selected = policyForm.autoApproveRoles.includes(role.value);
                      return (
                        <button
                          key={role.value}
                          type="button"
                          onClick={() =>
                            setPolicyForm((current) => ({
                              ...current,
                              autoApproveRoles: selected
                                ? current.autoApproveRoles.filter((value) => value !== role.value)
                                : [...current.autoApproveRoles, role.value],
                            }))
                          }
                          className="rounded-full border px-3 py-2 text-sm font-medium transition"
                          style={{
                            borderColor: selected ? "var(--accent)" : "var(--border)",
                            background: selected ? "var(--accent-soft)" : "transparent",
                            color: selected ? "var(--accent)" : "var(--text-muted)",
                          }}
                        >
                          {role.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs leading-6" style={{ color: "var(--text-dim)" }}>
                    Matching requesters will skip the queue and land as auto-approved.
                  </p>
                </div>

                <div className="flex flex-col gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between" style={{ borderColor: "var(--border)" }}>
                  <div className="text-xs leading-6" style={{ color: "var(--text-dim)" }}>
                    New approval requests are created from the transactions table, not from this screen.
                  </div>
                  <button type="submit" disabled={savingPolicy} className="btn-primary inline-flex items-center justify-center gap-2">
                    {savingPolicy ? "Creating..." : "Create policy"}
                  </button>
                </div>
              </form>
            </div>

            <div className="border-l p-6" style={{ borderColor: "var(--border)", background: "rgba(255, 255, 255, 0.02)" }}>
              <div className="rounded-2xl border p-5" style={{ borderColor: "rgba(201, 169, 98, 0.18)", background: "rgba(201, 169, 98, 0.05)" }}>
                <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--accent)" }}>
                  <Sparkles size={16} />
                  Policy preview
                </div>
                <div className="mt-4 space-y-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Rule</p>
                    <p className="mt-2 text-lg font-semibold" style={{ color: "var(--text)" }}>
                      {policyForm.name.trim() || "Unnamed policy"}
                    </p>
                    <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                      {policyForm.minAmount
                        ? `Matches expenses from ${formatAmount(Number(policyForm.minAmount))}${policyForm.maxAmount ? ` up to ${formatAmount(Number(policyForm.maxAmount))}` : " upward"}.`
                        : "Choose a threshold to define when this policy should apply."}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Category scope</p>
                    <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                      {selectedCategories.length
                        ? selectedCategories.join(", ")
                        : "All expense categories are eligible until you narrow the scope."}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Auto-approval</p>
                    <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                      {policyForm.autoApproveRoles.length
                        ? `Requests from ${policyForm.autoApproveRoles.join(", ")} will be completed immediately.`
                        : "No roles skip the queue yet."}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border p-5" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Coverage watch</p>
                <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                  {uncoveredExpenses.length
                    ? `${uncoveredExpenses.length} recent expense${uncoveredExpenses.length === 1 ? "" : "s"} still have no matching active policy.`
                    : "Recent expense activity is fully covered by active policies."}
                </p>
                {uncoveredExpenses.slice(0, 3).map((expense) => (
                  <div key={expense.id} className="mt-3 rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium" style={{ color: "var(--text)" }}>{expense.description}</p>
                        <p className="text-xs" style={{ color: "var(--text-muted)" }}>{expense.category}</p>
                      </div>
                      <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{formatAmount(expense.amount)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <div className="flex flex-wrap gap-2 animate-fade-up delay-1">
        {([
          { key: "queue" as const, label: "Pending queue", count: pendingApprovals.length },
          { key: "all" as const, label: "All approvals", count: approvals.length },
          { key: "policies" as const, label: "Policies", count: policies.length },
        ]).map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className="rounded-full border px-4 py-2 text-sm font-medium transition"
            style={{
              borderColor: tab === item.key ? "var(--accent)" : "var(--border)",
              background: tab === item.key ? "var(--accent-soft)" : "var(--surface)",
              color: tab === item.key ? "var(--accent)" : "var(--text-muted)",
            }}
          >
            {item.label}
            <span className="ml-2 rounded-full px-2 py-0.5 text-[11px]" style={{ background: "rgba(255,255,255,0.05)" }}>
              {item.count}
            </span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="skeleton" style={{ height: 220 }} />
          ))}
        </div>
      ) : null}

      {!loading && (tab === "queue" || tab === "all") ? (
        visibleApprovals.length === 0 ? (
          <div className="glass animate-fade-up p-12 text-center">
            <CheckSquare size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
            <p className="text-base font-medium" style={{ color: "var(--text)" }}>
              {tab === "queue" ? "No pending approvals right now." : "No approvals recorded yet."}
            </p>
            <p className="mx-auto mt-2 max-w-2xl text-sm leading-7" style={{ color: "var(--text-muted)" }}>
              Submit expense transactions from the transactions page after creating a matching policy, and they will land here with live decision actions.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {visibleApprovals.map((approval, index) => {
              const tone = getApprovalTone(approval.status);
              const isWorking = actingOnApprovalId === approval.id;

              return (
                <article
                  key={approval.id}
                  className={`glass animate-fade-up p-5 delay-${(index % 4) + 1}`}
                  style={{ background: "linear-gradient(180deg, rgba(17, 17, 17, 0.96), rgba(8, 8, 8, 0.92))" }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>
                        {approval.policy_name || "Linked policy"}
                      </p>
                      <h2 className="text-xl font-semibold" style={{ color: "var(--text)" }}>
                        {approval.description || `Transaction ${shortId(approval.transaction_id)}`}
                      </h2>
                      <div className="flex flex-wrap gap-2">
                        <span className="badge" style={{ background: tone.background, color: tone.color }}>{tone.label}</span>
                        {approval.category ? <span className="badge badge-info">{approval.category}</span> : null}
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-2xl font-semibold" style={{ color: "var(--text)" }}>
                        {approval.amount != null ? formatAmount(approval.amount) : "Amount pending"}
                      </p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                        Requested {formatDate(approval.created_at)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Requested by</p>
                      <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                        {approval.requester_name || shortId(approval.requested_by)}
                      </p>
                    </div>
                    <div className="rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Decision owner</p>
                      <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                        {approval.approver_name || (approval.approved_by ? shortId(approval.approved_by) : "Awaiting reviewer")}
                      </p>
                    </div>
                  </div>

                  {approval.notes || approval.rejection_reason ? (
                    <div className="mt-4 rounded-xl border px-3 py-3 text-sm leading-7" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)", color: "var(--text-muted)" }}>
                      {approval.notes || approval.rejection_reason}
                    </div>
                  ) : null}

                  {tab === "queue" ? (
                    <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                      <button
                        type="button"
                        disabled={isWorking}
                        onClick={() => handleApprove(approval.id)}
                        className="btn-primary inline-flex flex-1 items-center justify-center gap-2"
                      >
                        <Check size={16} />
                        {isWorking ? "Saving..." : "Approve"}
                      </button>
                      <button
                        type="button"
                        disabled={isWorking}
                        onClick={() => handleReject(approval.id)}
                        className="btn-secondary inline-flex flex-1 items-center justify-center gap-2"
                      >
                        <XCircle size={16} />
                        {isWorking ? "Saving..." : "Reject"}
                      </button>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        )
      ) : null}

      {!loading && tab === "policies" ? (
        policies.length === 0 ? (
          <div className="glass animate-fade-up p-12 text-center">
            <p className="text-base font-medium" style={{ color: "var(--text)" }}>No policies configured yet.</p>
            <p className="mx-auto mt-2 max-w-2xl text-sm leading-7" style={{ color: "var(--text-muted)" }}>
              Create a policy above and expense transactions with matching thresholds will become eligible for the approval queue.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {policies.map((policy, index) => {
              const matches = recentExpenses.filter((expense) => findMatchingPolicy([policy], expense)).length;
              return (
                <article
                  key={policy.id}
                  className={`glass animate-fade-up p-5 delay-${(index % 4) + 1}`}
                  style={{ background: "linear-gradient(180deg, rgba(17, 17, 17, 0.96), rgba(8, 8, 8, 0.92))" }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em]" style={{ color: "var(--text-dim)" }}>Policy</p>
                      <h2 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>{policy.name}</h2>
                    </div>
                    <span className={`badge ${policy.is_active ? "badge-income" : "badge-critical"}`}>
                      {policy.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Threshold</p>
                      <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                        {formatPolicyRange(formatAmount, policy)}
                      </p>
                    </div>
                    <div className="rounded-xl border px-3 py-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Recent matches</p>
                      <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                        {matches} recent expense{matches === 1 ? "" : "s"}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Categories</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {policy.categories.length ? (
                          policy.categories.map((category) => (
                            <span key={category} className="badge" style={{ background: "rgba(255,255,255,0.05)", color: "var(--text-muted)" }}>
                              {category}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Applies to every expense category.</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>Auto-approve roles</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {policy.auto_approve_roles.length ? (
                          policy.auto_approve_roles.map((role) => (
                            <span key={role} className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>
                              {role}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Every matching expense enters the manual queue.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )
      ) : null}
    </div>
  );
}
