"use client";
import { useEffect, useState, useCallback } from "react";
import { invoicesApi } from "@/lib/api";
import type { Invoice, AgingReport } from "@/lib/types";
import { FileCheck, Plus, X, Send } from "lucide-react";
import InvoiceForm from "@/components/InvoiceForm";

const fmt = (n: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  draft: { bg: "var(--surface-hover)", fg: "var(--text-dim)" },
  sent: { bg: "var(--accent-soft)", fg: "var(--accent)" },
  paid: { bg: "var(--success-soft)", fg: "var(--success)" },
  partially_paid: { bg: "var(--warning-soft)", fg: "var(--warning)" },
  overdue: { bg: "var(--danger-soft)", fg: "var(--danger)" },
  cancelled: { bg: "var(--surface-hover)", fg: "var(--text-dim)" },
};

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [aging, setAging] = useState<AgingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"list" | "aging">("list");
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    try {
      const [inv, ag] = await Promise.all([invoicesApi.list(), invoicesApi.aging().catch(() => null)]);
      setInvoices(inv); setAging(ag);
    } catch {} finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = filter ? invoices.filter(i => i.status === filter) : invoices;

  const handleSend = async (id: string) => { await invoicesApi.send(id); load(); };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Invoices</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Generate, track & collect payments</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          {showForm ? <X size={16}/> : <Plus size={16}/>} {showForm ? "Cancel" : "New Invoice"}
        </button>
      </div>

      {showForm && <InvoiceForm onSuccess={() => { setShowForm(false); load(); }} onCancel={() => setShowForm(false)} />}

      {!showForm && (
        <>
          <div className="flex gap-2 animate-fade-up delay-1">
            {(["list","aging"] as const).map(t => (
              <button key={t} onClick={() => setTab(t)} className="px-4 py-2 rounded-lg text-sm font-medium capitalize" style={{
                background: tab===t ? "var(--accent-soft)" : "var(--surface)",
                color: tab===t ? "var(--accent)" : "var(--text-muted)",
                border: `1px solid ${tab===t ? "var(--accent)" : "var(--border)"}`,
              }}>{t === "aging" ? "Aging Report" : "All Invoices"}</button>
            ))}
          </div>

          {tab === "list" && (
            <>
              <div className="flex gap-2 flex-wrap animate-fade-up delay-2">
                {["","draft","sent","paid","partially_paid","overdue"].map(s => (
                  <button key={s} onClick={() => setFilter(s)} className="px-3 py-1.5 rounded-md text-xs font-medium capitalize" style={{
                    background: filter===s ? "var(--accent-soft)" : "var(--surface)",
                    color: filter===s ? "var(--accent)" : "var(--text-dim)",
                  }}>{s || "All"}</button>
                ))}
              </div>

              {loading ? <div className="skeleton" style={{ height: 300 }}/> : filtered.length === 0 ? (
                <div className="glass p-12 text-center"><FileCheck size={40} className="mx-auto mb-3" style={{ color:"var(--text-dim)" }}/><p className="text-sm" style={{ color:"var(--text-dim)" }}>No invoices found.</p></div>
              ) : (
                <div className="glass overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr style={{ borderBottom:"1px solid var(--border)" }}>
                      <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>#</th>
                      <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Client</th>
                      <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Date</th>
                      <th className="text-right p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Total</th>
                      <th className="text-right p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Due</th>
                      <th className="text-center p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Status</th>
                      <th className="text-center p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Actions</th>
                    </tr></thead>
                    <tbody>{filtered.map(inv => {
                      const sc = STATUS_COLORS[inv.status] || STATUS_COLORS.draft;
                      return (
                        <tr key={inv.id} style={{ borderBottom:"1px solid var(--border)" }} className="transition-colors hover:bg-[var(--surface-hover)]">
                          <td className="p-4 font-mono font-bold" style={{ color:"var(--accent)" }}>{inv.invoice_number}</td>
                          <td className="p-4" style={{ color:"var(--text)" }}>{inv.client_name}</td>
                          <td className="p-4" style={{ color:"var(--text-muted)" }}>{inv.issue_date}</td>
                          <td className="p-4 text-right font-bold" style={{ color:"var(--text)" }}>{fmt(inv.total)}</td>
                          <td className="p-4 text-right" style={{ color: inv.amount_due > 0 ? "var(--warning)" : "var(--success)" }}>{fmt(inv.amount_due)}</td>
                          <td className="p-4 text-center"><span className="badge" style={{ background: sc.bg, color: sc.fg }}>{inv.status.replace(/_/g," ")}</span></td>
                          <td className="p-4 text-center flex gap-1 justify-center">
                            {inv.status === "draft" && <button onClick={() => handleSend(inv.id)} className="p-1.5 rounded-md transition-colors hover:bg-[var(--accent-soft)]" title="Send"><Send size={14} style={{ color:"var(--accent)" }}/></button>}
                          </td>
                        </tr>
                      );
                    })}</tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {tab === "aging" && aging && (
            <div className="space-y-4 animate-fade-up delay-2">
              <div className="glass p-5">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold" style={{ color:"var(--text)" }}>Total Outstanding</span>
                  <span className="text-xl font-bold" style={{ color:"var(--warning)" }}>{fmt(aging.total_outstanding)}</span>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {aging.buckets.map(b => (
                  <div key={b.bucket} className="glass p-5">
                    <div className="flex justify-between mb-2">
                      <span className="text-sm font-semibold" style={{ color:"var(--text)" }}>{b.bucket}</span>
                      <span className="text-xs" style={{ color:"var(--text-dim)" }}>{b.count} invoices</span>
                    </div>
                    <p className="text-lg font-bold" style={{ color:"var(--accent)" }}>{fmt(b.total)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
