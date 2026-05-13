"use client";
import { useEffect, useState, useCallback } from "react";
import { approvalsApi } from "@/lib/api";
import type { ExpenseApproval, ApprovalPolicy } from "@/lib/types";
import { CheckSquare, Plus, X, Check, XCircle } from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";

export default function ApprovalsPage() {
  const { formatAmount: fmt } = useCurrency();
  const [approvals, setApprovals] = useState<ExpenseApproval[]>([]);
  const [policies, setPolicies] = useState<ApprovalPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"queue"|"all"|"policies">("queue");
  const [showPolicy, setShowPolicy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, p] = await Promise.all([approvalsApi.pending(), approvalsApi.listPolicies()]);
      setApprovals(a); setPolicies(p);
    } catch {} finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const handleApprove = async (id: string) => { await approvalsApi.approve(id, { notes: "Approved" }); load(); };
  const handleReject = async (id: string) => { await approvalsApi.reject(id, { rejection_reason: "Rejected" }); load(); };

  const handleCreatePolicy = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await approvalsApi.createPolicy({
      name: fd.get("name") as string,
      min_amount: Number(fd.get("min_amount")),
      max_amount: Number(fd.get("max_amount")) || undefined,
    });
    setShowPolicy(false); load();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Expense Approvals</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Review & approve pending expenses</p>
        </div>
        <button onClick={() => setShowPolicy(!showPolicy)} className="btn-primary flex items-center gap-2">
          {showPolicy ? <X size={16}/> : <Plus size={16}/>} {showPolicy ? "Cancel" : "Add Policy"}
        </button>
      </div>

      {showPolicy && (
        <div className="glass p-6 animate-fade-up">
          <form onSubmit={handleCreatePolicy} className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <input name="name" placeholder="Policy Name" required />
            <input name="min_amount" type="number" step="0.01" placeholder="Min Amount" required />
            <input name="max_amount" type="number" step="0.01" placeholder="Max Amount (optional)" />
            <button type="submit" className="btn-primary">Create Policy</button>
          </form>
        </div>
      )}

      <div className="flex gap-2 animate-fade-up delay-1">
        {(["queue","all","policies"] as const).map(t => (
          <button key={t} onClick={async () => {
            setTab(t);
            if (t === "all") { const all = await approvalsApi.list(); setApprovals(all); }
            else if (t === "queue") { const pend = await approvalsApi.pending(); setApprovals(pend); }
          }} className="px-4 py-2 rounded-lg text-sm font-medium capitalize" style={{
            background: tab===t ? "var(--accent-soft)" : "var(--surface)",
            color: tab===t ? "var(--accent)" : "var(--text-muted)",
            border: `1px solid ${tab===t ? "var(--accent)" : "var(--border)"}`,
          }}>{t === "queue" ? "Pending Queue" : t === "all" ? "All Approvals" : "Policies"}</button>
        ))}
      </div>

      {loading ? <div className="skeleton" style={{ height: 200 }}/> : (
        <>
          {(tab === "queue" || tab === "all") && (
            approvals.length === 0 ? (
              <div className="glass p-12 text-center">
                <CheckSquare size={40} className="mx-auto mb-3" style={{ color:"var(--text-dim)" }}/>
                <p className="text-sm" style={{ color:"var(--text-dim)" }}>{tab === "queue" ? "No pending approvals." : "No approvals yet."}</p>
              </div>
            ) : (
              <div className="glass overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr style={{ borderBottom:"1px solid var(--border)" }}>
                    <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Transaction</th>
                    <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Requested By</th>
                    <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Date</th>
                    <th className="text-center p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Status</th>
                    {tab === "queue" && <th className="text-center p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Actions</th>}
                  </tr></thead>
                  <tbody>{approvals.map(a => (
                    <tr key={a.id} style={{ borderBottom:"1px solid var(--border)" }}>
                      <td className="p-4 font-mono text-xs" style={{ color:"var(--text)" }}>{a.transaction_id.slice(0,8)}…</td>
                      <td className="p-4" style={{ color:"var(--text-muted)" }}>{a.requested_by.slice(0,8)}…</td>
                      <td className="p-4" style={{ color:"var(--text-muted)" }}>{a.requested_at?.slice(0,10)}</td>
                      <td className="p-4 text-center"><span className="badge" style={{
                        background: a.status === "approved" ? "var(--success-soft)" : a.status === "rejected" ? "var(--danger-soft)" : "var(--warning-soft)",
                        color: a.status === "approved" ? "var(--success)" : a.status === "rejected" ? "var(--danger)" : "var(--warning)",
                      }}>{a.status}</span></td>
                      {tab === "queue" && (
                        <td className="p-4 text-center flex gap-1 justify-center">
                          <button onClick={() => handleApprove(a.id)} className="p-1.5 rounded-md hover:bg-[var(--success-soft)]" title="Approve"><Check size={14} style={{ color:"var(--success)" }}/></button>
                          <button onClick={() => handleReject(a.id)} className="p-1.5 rounded-md hover:bg-[var(--danger-soft)]" title="Reject"><XCircle size={14} style={{ color:"var(--danger)" }}/></button>
                        </td>
                      )}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )
          )}

          {tab === "policies" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {policies.length === 0 ? (
                <div className="glass p-12 text-center sm:col-span-2"><p className="text-sm" style={{ color:"var(--text-dim)" }}>No policies configured.</p></div>
              ) : policies.map((p,i) => (
                <div key={p.id} className={`glass p-5 animate-fade-up delay-${(i%4)+1}`}>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-semibold" style={{ color:"var(--text)" }}>{p.name}</span>
                    <span className={`badge ${p.is_active ? "badge-income" : "badge-critical"}`}>{p.is_active ? "Active" : "Inactive"}</span>
                  </div>
                  <p className="text-xs" style={{ color:"var(--text-muted)" }}>
                    Range: {fmt(p.min_amount)}
                    {p.max_amount ? ` — ${fmt(p.max_amount)}` : "+"}
                  </p>
                  {p.categories.length > 0 && <div className="flex gap-1 mt-2 flex-wrap">{p.categories.map(c => <span key={c} className="badge" style={{ background:"var(--surface-hover)", color:"var(--text-dim)", fontSize:10 }}>{c}</span>)}</div>}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
