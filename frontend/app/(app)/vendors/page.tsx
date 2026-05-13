"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { vendorsApi } from "@/lib/api";
import type { Vendor, VendorSpendAnalysis } from "@/lib/types";
import { Plus, X, Store, Search, TrendingUp, ArrowLeft, Calendar, DollarSign, BarChart3, Users, ChevronRight } from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";

const COLORS = ["#d4a853","#7ec8e3","#e07a5f","#81b29a","#f2cc8f","#a8dadc","#e5989b","#b5838d","#6d6875","#cdb4db"];

type VendorTxn = { id: string; date: string; description: string; amount: number; category: string; type: string };
type TrendPoint = { month: string; vendor: string; total: number };

export default function VendorsPage() {
  const { formatAmount: fmt } = useCurrency();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [spend, setSpend] = useState<VendorSpendAnalysis[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<"overview" | "list">("overview");
  const [selectedVendor, setSelectedVendor] = useState<string | null>(null);
  const [vendorTxns, setVendorTxns] = useState<VendorTxn[]>([]);
  const [txnLoading, setTxnLoading] = useState(false);
  const [txnTotal, setTxnTotal] = useState(0);
  const [txnPage, setTxnPage] = useState(0);
  const TXN_PER_PAGE = 20;

  const load = useCallback(async () => {
    try {
      await vendorsApi.syncFromTransactions().catch(() => {});
      const [v, s, t] = await Promise.all([
        vendorsApi.list(), vendorsApi.spendAnalysis(), vendorsApi.monthlyTrend().catch(() => []),
      ]);
      setVendors(v); setSpend(s); setTrend(t);
    } catch { /* empty */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadVendorTxns = async (name: string, page = 0) => {
    setSelectedVendor(name); setTxnLoading(true); setTxnPage(page);
    try {
      const res = await vendorsApi.vendorTransactions(name, page * TXN_PER_PAGE, TXN_PER_PAGE);
      setVendorTxns(res.items || []); setTxnTotal(res.total || 0);
    } catch { setVendorTxns([]); setTxnTotal(0); }
    finally { setTxnLoading(false); }
  };

  // KPIs
  const totalVendors = vendors.length;
  const totalSpent = spend.reduce((a, s) => a + (s.total_spend || 0), 0);
  const totalTxns = spend.reduce((a, s) => a + s.transaction_count, 0);
  const topCategory = useMemo(() => {
    const cats: Record<string, number> = {};
    spend.forEach(s => { const c = s.category || "Other"; cats[c] = (cats[c] || 0) + (s.total_spend || 0); });
    return Object.entries(cats).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";
  }, [spend]);

  // Top 8 vendors by spend for the bar chart
  const topVendors = useMemo(() => {
    const map: Record<string, number> = {};
    spend.forEach(s => { map[s.vendor_name] = (map[s.vendor_name] || 0) + (s.total_spend || 0); });
    return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 8);
  }, [spend]);
  const maxSpend = topVendors[0]?.[1] || 1;

  // Monthly trend aggregated
  const monthlyData = useMemo(() => {
    const map: Record<string, number> = {};
    trend.forEach(t => { map[t.month] = (map[t.month] || 0) + t.total; });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0])).slice(-12);
  }, [trend]);
  const maxMonth = Math.max(...monthlyData.map(m => m[1]), 1);

  const filtered = vendors.filter(v =>
    v.name.toLowerCase().includes(search.toLowerCase()) || v.category?.toLowerCase().includes(search.toLowerCase())
  );

  // Selected vendor stats
  const selectedStats = useMemo(() => {
    if (!selectedVendor) return null;
    const matching = spend.filter(s => s.vendor_name.toLowerCase() === selectedVendor.toLowerCase());
    return {
      total: matching.reduce((a, s) => a + (s.total_spend || 0), 0),
      txns: matching.reduce((a, s) => a + s.transaction_count, 0),
      avg: matching.length ? matching.reduce((a, s) => a + s.avg_transaction, 0) / matching.length : 0,
      category: matching[0]?.category || "Uncategorized",
    };
  }, [selectedVendor, spend]);

  if (selectedVendor) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <button onClick={() => setSelectedVendor(null)} className="flex items-center gap-2 text-sm transition-colors hover:opacity-80" style={{ color: "var(--accent)" }}>
          <ArrowLeft size={16} /> Back to Vendors
        </button>
        <div className="animate-fade-up">
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>{selectedVendor}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{selectedStats?.category}</p>
        </div>

        {/* Vendor KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-up delay-1">
          {[
            { label: "Total Spent", value: fmt(selectedStats?.total || 0), icon: DollarSign },
            { label: "Transactions", value: String(selectedStats?.txns || 0), icon: BarChart3 },
            { label: "Avg Transaction", value: fmt(selectedStats?.avg || 0), icon: TrendingUp },
            { label: "Category", value: selectedStats?.category || "—", icon: Store },
          ].map((k, i) => (
            <div key={i} className="glass p-5">
              <div className="flex items-center gap-2 mb-2">
                <k.icon size={14} style={{ color: "var(--accent)" }} />
                <span className="text-xs uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>{k.label}</span>
              </div>
              <p className="text-xl font-bold" style={{ color: "var(--text)" }}>{k.value}</p>
            </div>
          ))}
        </div>

        {/* Transaction History */}
        <div className="glass animate-fade-up delay-2">
          <div className="p-5 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2">
              <Calendar size={16} style={{ color: "var(--accent)" }} />
              <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Transaction History</h3>
            </div>
            {txnTotal > 0 && <span className="text-xs px-2 py-1 rounded-full" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>{txnTotal} total</span>}
          </div>
          {txnLoading ? (
            <div className="p-8 text-center"><div className="spinner mx-auto" /></div>
          ) : vendorTxns.length === 0 ? (
            <div className="p-12 text-center"><p className="text-sm" style={{ color: "var(--text-dim)" }}>No transactions found.</p></div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      {["Date", "Description", "Category", "Amount"].map(h => (
                        <th key={h} className={`p-4 text-xs uppercase tracking-wider ${h === "Amount" ? "text-right" : "text-left"}`} style={{ color: "var(--text-dim)" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {vendorTxns.map(t => (
                      <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }} className="transition-colors hover:bg-[var(--surface-hover)]">
                        <td className="p-4" style={{ color: "var(--text-muted)" }}>{new Date(t.date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}</td>
                        <td className="p-4 font-medium" style={{ color: "var(--text)" }}>{t.description || "—"}</td>
                        <td className="p-4"><span className="badge" style={{ background: "var(--surface-hover)", color: "var(--text-dim)", fontSize: 10 }}>{t.category || "—"}</span></td>
                        <td className="p-4 text-right font-bold" style={{ color: t.type === "income" ? "var(--success)" : "var(--accent)" }}>{fmt(t.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Pagination */}
              {txnTotal > TXN_PER_PAGE && (
                <div className="p-4 flex items-center justify-between" style={{ borderTop: "1px solid var(--border)" }}>
                  <span className="text-xs" style={{ color: "var(--text-dim)" }}>
                    Showing {txnPage * TXN_PER_PAGE + 1}–{Math.min((txnPage + 1) * TXN_PER_PAGE, txnTotal)} of {txnTotal}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={txnPage === 0}
                      onClick={() => selectedVendor && loadVendorTxns(selectedVendor, txnPage - 1)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-30"
                      style={{ background: "var(--surface-hover)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
                    >← Prev</button>
                    <button
                      disabled={(txnPage + 1) * TXN_PER_PAGE >= txnTotal}
                      onClick={() => selectedVendor && loadVendorTxns(selectedVendor, txnPage + 1)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-30"
                      style={{ background: "var(--surface-hover)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
                    >Next →</button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Vendor Intelligence</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Spend analytics, vendor performance & transaction history</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          {showForm ? <X size={16} /> : <Plus size={16} />}
          {showForm ? "Cancel" : "Add Vendor"}
        </button>
      </div>

      {showForm && <CreateVendorForm onSuccess={() => { setShowForm(false); load(); }} />}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-up delay-1">
        {[
          { label: "Total Vendors", value: String(totalVendors), icon: Users, accent: "#d4a853" },
          { label: "Total Spent", value: fmt(totalSpent), icon: DollarSign, accent: "#e07a5f" },
          { label: "Transactions", value: totalTxns.toLocaleString(), icon: BarChart3, accent: "#7ec8e3" },
          { label: "Top Category", value: topCategory, icon: Store, accent: "#81b29a" },
        ].map((k, i) => (
          <div key={i} className="glass glass-hover p-5 transition-all">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 rounded-lg" style={{ background: `${k.accent}15` }}>
                <k.icon size={16} style={{ color: k.accent }} />
              </div>
            </div>
            <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-dim)" }}>{k.label}</p>
            <p className="text-xl font-bold" style={{ color: "var(--text)" }}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 animate-fade-up delay-2">
        {(["overview", "list"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className="px-4 py-2 rounded-lg text-sm font-medium transition-all" style={{
            background: tab === t ? "var(--accent-soft)" : "var(--surface)",
            color: tab === t ? "var(--accent)" : "var(--text-muted)",
            border: `1px solid ${tab === t ? "var(--accent)" : "var(--border)"}`,
          }}>
            {t === "overview" ? "Spend Analysis" : "All Vendors"}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Vendors Bar Chart */}
          <div className="glass p-6 animate-fade-up delay-3">
            <h3 className="text-sm font-semibold mb-5 flex items-center gap-2" style={{ color: "var(--text)" }}>
              <BarChart3 size={16} style={{ color: "var(--accent)" }} /> Top Vendors by Spend
            </h3>
            <div className="space-y-3">
              {topVendors.map(([name, amount], i) => (
                <button key={name} onClick={() => loadVendorTxns(name)} className="w-full text-left group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium truncate max-w-[60%] group-hover:underline" style={{ color: "var(--text)" }}>{name}</span>
                    <span className="text-xs font-bold" style={{ color: "var(--accent)" }}>{fmt(amount)}</span>
                  </div>
                  <div className="w-full h-3 rounded-full overflow-hidden" style={{ background: "var(--surface-hover)" }}>
                    <div className="h-full rounded-full transition-all duration-700" style={{
                      width: `${(amount / maxSpend) * 100}%`, background: COLORS[i % COLORS.length],
                      animation: `grow-bar 0.8s ease-out ${i * 0.1}s both`,
                    }} />
                  </div>
                </button>
              ))}
              {topVendors.length === 0 && <p className="text-sm text-center py-8" style={{ color: "var(--text-dim)" }}>No spend data</p>}
            </div>
          </div>

          {/* Monthly Trend */}
          <div className="glass p-6 animate-fade-up delay-4">
            <h3 className="text-sm font-semibold mb-5 flex items-center gap-2" style={{ color: "var(--text)" }}>
              <TrendingUp size={16} style={{ color: "var(--accent)" }} /> Monthly Spend Trend
            </h3>
            {monthlyData.length === 0 ? (
              <p className="text-sm text-center py-8" style={{ color: "var(--text-dim)" }}>No trend data</p>
            ) : (
              <div className="flex items-end gap-2 h-48">
                {monthlyData.map(([month, total], i) => (
                  <div key={month} className="flex-1 flex flex-col items-center gap-1 h-full justify-end group relative">
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-xs font-bold px-2 py-1 rounded whitespace-nowrap" style={{ background: "var(--surface)", color: "var(--accent)", border: "1px solid var(--border)" }}>
                      {fmt(total)}
                    </div>
                    <div className="w-full rounded-t-md transition-all duration-500 hover:opacity-80 cursor-default" style={{
                      height: `${(total / maxMonth) * 100}%`,
                      minHeight: 4,
                      background: `linear-gradient(to top, ${COLORS[i % COLORS.length]}cc, ${COLORS[i % COLORS.length]}44)`,
                      animation: `grow-bar 0.6s ease-out ${i * 0.05}s both`,
                    }} />
                    <span className="text-[9px] whitespace-nowrap" style={{ color: "var(--text-dim)" }}>
                      {month.slice(5)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Spend Table */}
          <div className="glass lg:col-span-2 animate-fade-up delay-5">
            <div className="p-5 flex items-center gap-2" style={{ borderBottom: "1px solid var(--border)" }}>
              <DollarSign size={16} style={{ color: "var(--accent)" }} />
              <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Spend Breakdown</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Vendor", "Category", "Total Spent", "Transactions", "Avg Txn", "Last Date"].map(h => (
                      <th key={h} className={`p-4 text-xs uppercase tracking-wider ${["Total Spent","Transactions","Avg Txn"].includes(h) ? "text-right" : "text-left"}`} style={{ color: "var(--text-dim)" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {spend.map((s, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }} className="transition-colors hover:bg-[var(--surface-hover)] cursor-pointer" onClick={() => loadVendorTxns(s.vendor_name)}>
                      <td className="p-4 font-medium flex items-center gap-2" style={{ color: "var(--text)" }}>
                        <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                        {s.vendor_name}
                        <ChevronRight size={12} style={{ color: "var(--text-dim)" }} />
                      </td>
                      <td className="p-4"><span className="badge" style={{ background: "var(--surface-hover)", color: "var(--text-dim)", fontSize: 10 }}>{s.category || "—"}</span></td>
                      <td className="p-4 text-right font-bold" style={{ color: "var(--accent)" }}>{fmt(s.total_spend)}</td>
                      <td className="p-4 text-right" style={{ color: "var(--text-muted)" }}>{s.transaction_count}</td>
                      <td className="p-4 text-right" style={{ color: "var(--text-muted)" }}>{fmt(s.avg_transaction)}</td>
                      <td className="p-4 text-left" style={{ color: "var(--text-dim)" }}>{s.last_transaction_date ? new Date(s.last_transaction_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" }) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {spend.length === 0 && <div className="p-12 text-center"><p className="text-sm" style={{ color: "var(--text-dim)" }}>No spend data yet.</p></div>}
            </div>
          </div>
        </div>
      )}

      {tab === "list" && (
        <>
          <div className="glass p-3 flex items-center gap-2 animate-fade-up delay-3">
            <Search size={16} style={{ color: "var(--text-dim)" }} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search vendors…" className="bg-transparent border-none outline-none text-sm flex-1" style={{ color: "var(--text)" }} />
          </div>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 160 }} />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="glass p-12 text-center">
              <Store size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
              <p className="text-sm" style={{ color: "var(--text-dim)" }}>No vendors found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((v, i) => (
                <div key={v.id} onClick={() => loadVendorTxns(v.name)} className={`glass glass-hover p-5 cursor-pointer animate-fade-up delay-${(i % 6) + 1} transition-all hover:scale-[1.02]`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>{v.name}</span>
                    <span className={`badge ${v.is_active ? "badge-income" : "badge-critical"}`}>{v.is_active ? "Active" : "Inactive"}</span>
                  </div>
                  {v.category && <span className="inline-block text-[10px] px-2 py-0.5 rounded-full mb-2" style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>{v.category}</span>}
                  <div className="flex items-baseline gap-2 mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                    <span className="text-lg font-bold" style={{ color: "var(--accent)" }}>{fmt(v.total_spent || 0)}</span>
                    <span className="text-xs" style={{ color: "var(--text-dim)" }}>{v.transaction_count || 0} txns</span>
                    <ChevronRight size={14} className="ml-auto" style={{ color: "var(--text-dim)" }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <style jsx>{`
        @keyframes grow-bar { from { transform: scaleY(0); transform-origin: bottom; } to { transform: scaleY(1); transform-origin: bottom; } }
      `}</style>
    </div>
  );
}

function CreateVendorForm({ onSuccess }: { onSuccess: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setError(""); setSubmitting(true);
    const fd = new FormData(e.currentTarget);
    try {
      await vendorsApi.create({ name: fd.get("name") as string, category: fd.get("category") as string || undefined, payment_terms: fd.get("payment_terms") as string || undefined });
      onSuccess();
    } catch (err: unknown) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setSubmitting(false); }
  };
  return (
    <div className="glass p-6 animate-fade-up">
      <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text)" }}>New Vendor</h3>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <input name="name" placeholder="Vendor Name" required />
        <input name="category" placeholder="Category (optional)" />
        <input name="payment_terms" placeholder="Payment Terms (e.g. Net 30)" />
        <button type="submit" disabled={submitting} className="btn-primary">{submitting ? "Creating…" : "Add Vendor"}</button>
        {error && <div className="sm:col-span-4 text-xs px-3 py-2 rounded-lg" style={{ background: "var(--danger-soft)", color: "var(--danger)" }}>{error}</div>}
      </form>
    </div>
  );
}
