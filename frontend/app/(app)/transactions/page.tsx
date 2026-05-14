"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  ArrowDownRight,
  ArrowUpRight,
  Plus,
  Search,
  Upload,
  X,
} from "lucide-react";

import { useCurrency } from "@/components/CurrencyContext";
import { findMatchingPolicy } from "@/lib/approvals";
import { api, approvalsApi } from "@/lib/api";
import type { ApprovalPolicy, ExpenseApproval, TransactionOut } from "@/lib/types";

function getApprovalTone(status: ExpenseApproval["status"]) {
  if (status === "approved" || status === "auto_approved") {
    return {
      label: status === "auto_approved" ? "Auto-approved" : "Approved",
      className: "badge-income",
    };
  }

  if (status === "rejected") {
    return {
      label: "Rejected",
      className: "badge-critical",
    };
  }

  return {
    label: "Pending",
    className: "badge-warning",
  };
}

export default function TransactionsPage() {
  const { formatAmount: fmt } = useCurrency();
  const { getToken } = useAuth();
  const [txs, setTxs] = useState<TransactionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"" | "income" | "expense">("");
  const [policies, setPolicies] = useState<ApprovalPolicy[]>([]);
  const [approvalByTransactionId, setApprovalByTransactionId] = useState<Record<string, ExpenseApproval>>({});
  const [approvalMessage, setApprovalMessage] = useState<string | null>(null);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [submittingApprovalId, setSubmittingApprovalId] = useState<string | null>(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setApprovalError(null);

    try {
      const token = await getToken();
      const data = await api.getTransactions(
        currentPage, 
        perPage, 
        search, 
        token,
        filterType || undefined
      );
      setTxs(data.items);
      setTotalPages(data.pages);
      setTotalTransactions(data.total);

      const [approvalsResult, policiesResult] = await Promise.allSettled([
        approvalsApi.list(),
        approvalsApi.listPolicies(),
      ]);

      if (approvalsResult.status === "fulfilled") {
        setApprovalByTransactionId(
          Object.fromEntries(
            approvalsResult.value.map((approval) => [approval.transaction_id, approval]),
          ),
        );
      }

      if (policiesResult.status === "fulfilled") {
        setPolicies(policiesResult.value);
      }

      if (approvalsResult.status === "rejected" || policiesResult.status === "rejected") {
        setApprovalError("Transactions loaded, but approval context could not be fully refreshed.");
      }
    } catch {
      setApprovalError("Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }, [getToken, currentPage, perPage, search, filterType]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = txs; // Filtering is now handled by the backend API

  const handleCSV = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const token = await getToken();
      await api.uploadCSV(file, token);
      await load();
    } catch {
      setApprovalError("CSV import failed");
    }
  };

  const handleSubmitForApproval = async (transaction: TransactionOut) => {
    setSubmittingApprovalId(transaction.id);
    setApprovalMessage(null);
    setApprovalError(null);

    try {
      const approval = await approvalsApi.submit(transaction.id);
      setApprovalMessage(
        approval.status === "auto_approved"
          ? "Expense matched a policy and auto-approved immediately."
          : "Expense submitted to the approvals queue.",
      );
      await load();
    } catch (submitError) {
      setApprovalError(
        submitError instanceof Error ? submitError.message : "Failed to submit for approval",
      );
    } finally {
      setSubmittingApprovalId(null);
    }
  };

  const activePolicies = policies.filter((policy) => policy.is_active);
  const uncoveredExpenses = txs.filter((transaction) => {
    if (transaction.type !== "expense") {
      return false;
    }
    if (approvalByTransactionId[transaction.id]) {
      return false;
    }
    return !findMatchingPolicy(activePolicies, transaction);
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Transactions</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {totalTransactions} total transactions • Page {currentPage} of {totalPages}
          </p>
        </div>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
          <label className="btn-ghost flex w-full cursor-pointer items-center justify-center gap-2 sm:w-auto">
            <Upload size={16} /> Import CSV
            <input type="file" accept=".csv" onChange={handleCSV} className="hidden" />
          </label>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary flex w-full items-center justify-center gap-2 sm:w-auto">
            {showForm ? <X size={16} /> : <Plus size={16} />}
            {showForm ? "Cancel" : "Add Transaction"}
          </button>
        </div>
      </div>

      {approvalError ? (
        <div className="glass px-4 py-3 text-sm" style={{ color: "var(--danger)", borderColor: "rgba(199, 80, 80, 0.35)", background: "rgba(199, 80, 80, 0.08)" }}>
          {approvalError}
        </div>
      ) : null}

      {approvalMessage ? (
        <div className="glass px-4 py-3 text-sm" style={{ color: "var(--success)", borderColor: "rgba(94, 158, 126, 0.3)", background: "rgba(94, 158, 126, 0.08)" }}>
          {approvalMessage}
        </div>
      ) : null}

      {uncoveredExpenses.length ? (
        <div className="glass animate-fade-up p-4" style={{ borderColor: "rgba(212, 150, 90, 0.24)", background: "rgba(212, 150, 90, 0.08)" }}>
          <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
            {uncoveredExpenses.length} expense transaction{uncoveredExpenses.length === 1 ? "" : "s"} cannot reach the pending queue yet.
          </p>
          <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
            They do not match any active approval policy, so no request can be created from them yet.
            <Link href="/approvals" className="ml-2 font-medium" style={{ color: "var(--accent)" }}>
              Add or expand a policy
            </Link>
          </p>
        </div>
      ) : null}

      {showForm ? <AddTransactionForm onSuccess={() => { setShowForm(false); load(); }} /> : null}

      <div className="flex flex-col sm:flex-row gap-3 animate-fade-up delay-1">
        <div className="relative flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-dim)" }} />
            <input 
              type="text" 
              placeholder="Search transactions..." 
              value={search} 
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  setCurrentPage(1);
                  load();
                }
              }}
              className="w-full pl-10" 
            />
          </div>
          <button
            onClick={() => {
              setCurrentPage(1);
              load();
            }}
            className="btn-primary px-4"
          >
            Search
          </button>
        </div>
        <select 
          value={filterType} 
          onChange={(event) => {
            setFilterType(event.target.value as "" | "income" | "expense");
            setCurrentPage(1);
          }}
          className="w-full sm:w-auto" 
          style={{ minWidth: 140 }}
        >
          <option value="">All types</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
        <select 
          value={perPage} 
          onChange={(event) => {
            setPerPage(Number(event.target.value));
            setCurrentPage(1);
          }}
          className="w-full sm:w-auto" 
          style={{ minWidth: 120 }}
        >
          <option value="10">10 per page</option>
          <option value="20">20 per page</option>
          <option value="50">50 per page</option>
          <option value="100">100 per page</option>
        </select>
      </div>

      <div className="glass overflow-hidden animate-fade-up delay-2">
        {loading ? (
          <div className="p-8 space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="skeleton" style={{ height: 40 }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>
              {txs.length === 0 ? "No transactions yet. Add one above." : "No results match your filters."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: "touch" }}>
            <table className="w-full text-sm" style={{ minWidth: 860 }}>
              <thead>
                <tr className="text-xs uppercase tracking-wider text-left" style={{ color: "var(--text-dim)", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Description</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                  <th className="px-5 py-3">Approval</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((transaction) => {
                  const approval = approvalByTransactionId[transaction.id];
                  const matchingPolicy = approval ? null : findMatchingPolicy(activePolicies, transaction);
                  const approvalTone = approval ? getApprovalTone(approval.status) : null;
                  const isSubmitting = submittingApprovalId === transaction.id;

                  return (
                    <tr key={transaction.id} className="transition-colors hover:bg-[var(--surface-hover)]" style={{ borderBottom: "1px solid var(--border)" }}>
                      <td className="px-5 py-3.5" style={{ color: "var(--text-muted)" }}>
                        {new Date(transaction.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </td>
                      <td className="px-5 py-3.5 font-medium" style={{ color: "var(--text)" }}>{transaction.description}</td>
                      <td className="px-5 py-3.5"><span className="badge badge-info">{transaction.category}</span></td>
                      <td className="px-5 py-3.5">
                        <span className={`badge ${transaction.type === "income" ? "badge-income" : "badge-expense"}`}>{transaction.type}</span>
                      </td>
                      <td className="px-5 py-3.5 text-right font-medium">
                        <span className="flex items-center justify-end gap-1" style={{ color: transaction.type === "income" ? "var(--income)" : "var(--expense)" }}>
                          {transaction.type === "income" ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          {fmt(transaction.amount)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        {transaction.type === "income" ? (
                          <span className="text-xs" style={{ color: "var(--text-dim)" }}>No approval needed</span>
                        ) : approval && approvalTone ? (
                          <div className="space-y-1">
                            <span className={`badge ${approvalTone.className}`}>{approvalTone.label}</span>
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                              {approval.policy_name || "Existing request"}
                            </p>
                          </div>
                        ) : matchingPolicy ? (
                          <div className="space-y-2">
                            <button
                              type="button"
                              disabled={isSubmitting}
                              onClick={() => handleSubmitForApproval(transaction)}
                              className="btn-secondary inline-flex items-center justify-center"
                            >
                              {isSubmitting ? "Submitting..." : "Send for review"}
                            </button>
                            <p className="text-xs leading-6" style={{ color: "var(--text-muted)" }}>
                              Matches <span style={{ color: "var(--text)" }}>{matchingPolicy.name}</span>
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <span className="badge badge-warning">No policy</span>
                            <Link href="/approvals" className="text-xs font-medium" style={{ color: "var(--accent)" }}>
                              Create one
                            </Link>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {!loading && filtered.length > 0 && totalPages > 1 && (
        <div className="glass p-4 animate-fade-up delay-3">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-sm" style={{ color: "var(--text-muted)" }}>
              Showing {((currentPage - 1) * perPage) + 1} to {Math.min(currentPage * perPage, totalTransactions)} of {totalTransactions} transactions
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="btn-ghost px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                First
              </button>
              
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="btn-ghost px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                        currentPage === pageNum 
                          ? 'btn-primary' 
                          : 'btn-ghost'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="btn-ghost px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
              
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="btn-ghost px-3 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Last
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AddTransactionForm({ onSuccess }: { onSuccess: () => void }) {
  const { getToken } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const formData = new FormData(event.currentTarget);
    try {
      const token = await getToken();
      await api.createTransaction({
        amount: parseFloat(formData.get("amount") as string),
        type: formData.get("type") as "income" | "expense",
        category: formData.get("category") as string,
        description: formData.get("description") as string,
        date: formData.get("date") as string,
      }, token);
      onSuccess();
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Failed to add");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="glass p-6 animate-fade-up">
      <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>New Transaction</h3>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <input name="description" placeholder="Description" required className="lg:col-span-2" />
        <input name="amount" type="number" step="0.01" min="0" placeholder="Amount" required />
        <select name="type" required>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
        <input name="category" placeholder="Category" required />
        <input name="date" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} />
        {error ? (
          <div className="sm:col-span-2 lg:col-span-6 text-xs px-3 py-2 rounded-lg" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
            {error}
          </div>
        ) : null}
        <div className="sm:col-span-2 lg:col-span-6 flex justify-stretch sm:justify-end">
          <button type="submit" disabled={submitting} className="btn-primary w-full sm:w-auto">
            {submitting ? "Saving..." : "Add Transaction"}
          </button>
        </div>
      </form>
    </div>
  );
}
