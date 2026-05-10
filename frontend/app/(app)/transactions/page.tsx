"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import type { TransactionOut } from "@/lib/types";
import {
  Plus,
  Upload,
  ArrowUpRight,
  ArrowDownRight,
  Search,
  X,
} from "lucide-react";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);

export default function TransactionsPage() {
  const { getToken } = useAuth();
  const [txs, setTxs] = useState<TransactionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"" | "income" | "expense">("");

  const load = useCallback(async () => {
    try {
      const token = await getToken();
      const data = await api.getTransactions(1, 20, "", token);
      setTxs(data.items);
    } catch {
      /* show empty state */
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = txs.filter((t) => {
    if (filterType && t.type !== filterType) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        t.description.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const handleCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const token = await getToken();
      await api.uploadCSV(file, token);
      load();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Transactions</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{txs.length} total transactions</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="btn-ghost flex items-center gap-2 cursor-pointer">
            <Upload size={16} /> Import CSV
            <input type="file" accept=".csv" onChange={handleCSV} className="hidden" />
          </label>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
            {showForm ? <X size={16} /> : <Plus size={16} />}
            {showForm ? "Cancel" : "Add Transaction"}
          </button>
        </div>
      </div>

      {showForm && <AddTransactionForm onSuccess={() => { setShowForm(false); load(); }} />}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 animate-fade-up delay-1">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-dim)" }} />
          <input type="text" placeholder="Search transactions…" value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-10" />
        </div>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value as "" | "income" | "expense")} className="w-full sm:w-auto" style={{ minWidth: 140 }}>
          <option value="">All types</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
        </select>
      </div>

      {/* Table */}
      <div className="glass overflow-hidden animate-fade-up delay-2">
        {loading ? (
          <div className="p-8 space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 40 }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-sm" style={{ color: "var(--text-dim)" }}>
              {txs.length === 0 ? "No transactions yet. Add one above." : "No results match your filters."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: "touch" }}>
            <table className="w-full text-sm" style={{ minWidth: 580 }}>
              <thead>
                <tr className="text-xs uppercase tracking-wider text-left" style={{ color: "var(--text-dim)", borderBottom: "1px solid var(--border)", background: "var(--surface)" }}>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Description</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((tx) => (
                  <tr key={tx.id} className="transition-colors hover:bg-[var(--surface-hover)]" style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="px-5 py-3.5" style={{ color: "var(--text-muted)" }}>
                      {new Date(tx.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                    <td className="px-5 py-3.5 font-medium" style={{ color: "var(--text)" }}>{tx.description}</td>
                    <td className="px-5 py-3.5"><span className="badge badge-info">{tx.category}</span></td>
                    <td className="px-5 py-3.5">
                      <span className={`badge ${tx.type === "income" ? "badge-income" : "badge-expense"}`}>{tx.type}</span>
                    </td>
                    <td className="px-5 py-3.5 text-right font-medium">
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
        )}
      </div>
    </div>
  );
}

function AddTransactionForm({ onSuccess }: { onSuccess: () => void }) {
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
      await api.createTransaction({
        amount: parseFloat(fd.get("amount") as string),
        type: fd.get("type") as "income" | "expense",
        category: fd.get("category") as string,
        description: fd.get("description") as string,
        date: fd.get("date") as string,
      }, token);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add");
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
        {error && (
          <div className="sm:col-span-2 lg:col-span-6 text-xs px-3 py-2 rounded-lg" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>
            {error}
          </div>
        )}
        <div className="sm:col-span-2 lg:col-span-6 flex justify-end">
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? "Saving…" : "Add Transaction"}
          </button>
        </div>
      </form>
    </div>
  );
}
