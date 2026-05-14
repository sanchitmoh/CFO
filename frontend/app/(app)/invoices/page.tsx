"use client";

import { useCallback, useEffect, useState } from "react";
import { invoicesApi } from "@/lib/api";
import type { AgingReport, Invoice } from "@/lib/types";
import {
  ArrowRight,
  CalendarDays,
  CircleAlert,
  Clock3,
  FileCheck,
  Mail,
  Plus,
  Receipt,
  Send,
  Sparkles,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import InvoiceForm from "@/components/InvoiceForm";
import { useCurrency } from "@/components/CurrencyContext";

const STATUS_META: Record<Invoice["status"], { label: string; bg: string; fg: string; border: string }> = {
  draft: { label: "Draft", bg: "rgba(92, 87, 80, 0.12)", fg: "var(--text-dim)", border: "rgba(92, 87, 80, 0.24)" },
  sent: { label: "Sent", bg: "rgba(201, 169, 98, 0.12)", fg: "var(--accent)", border: "rgba(201, 169, 98, 0.28)" },
  paid: { label: "Paid", bg: "rgba(94, 158, 126, 0.12)", fg: "var(--success)", border: "rgba(94, 158, 126, 0.28)" },
  partially_paid: { label: "Partially Paid", bg: "rgba(212, 150, 90, 0.12)", fg: "var(--warning)", border: "rgba(212, 150, 90, 0.28)" },
  overdue: { label: "Overdue", bg: "rgba(199, 80, 80, 0.12)", fg: "var(--danger)", border: "rgba(199, 80, 80, 0.28)" },
  cancelled: { label: "Cancelled", bg: "rgba(92, 87, 80, 0.12)", fg: "var(--text-dim)", border: "rgba(92, 87, 80, 0.24)" },
};

const AGING_BUCKET_META: Record<string, { title: string; note: string; tone: string; surface: string; border: string }> = {
  current: {
    title: "Current",
    note: "Due today or still ahead of schedule",
    tone: "var(--info)",
    surface: "rgba(107, 142, 194, 0.08)",
    border: "rgba(107, 142, 194, 0.22)",
  },
  "1-30": {
    title: "1-30 Days",
    note: "Warm follow-ups and gentle nudges",
    tone: "var(--warning)",
    surface: "rgba(212, 150, 90, 0.08)",
    border: "rgba(212, 150, 90, 0.22)",
  },
  "31-60": {
    title: "31-60 Days",
    note: "Collection risk is building",
    tone: "var(--accent)",
    surface: "rgba(201, 169, 98, 0.08)",
    border: "rgba(201, 169, 98, 0.22)",
  },
  "61-90": {
    title: "61-90 Days",
    note: "Escalation and payment plans",
    tone: "var(--danger)",
    surface: "rgba(199, 80, 80, 0.08)",
    border: "rgba(199, 80, 80, 0.22)",
  },
  "90+": {
    title: "90+ Days",
    note: "Critical receivables exposure",
    tone: "var(--danger)",
    surface: "rgba(199, 80, 80, 0.12)",
    border: "rgba(199, 80, 80, 0.3)",
  },
};

const DAY_MS = 24 * 60 * 60 * 1000;

const parseCalendarDate = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00`);

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parseCalendarDate(value));

const formatMoney = (value: number, currencyCode: string) => {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currencyCode,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return value.toFixed(2);
  }
};

const summarizeLineItems = (invoice: Invoice) => {
  if (!invoice.line_items.length) return "No line items";
  const [first, ...rest] = invoice.line_items;
  return rest.length ? `${first.description} +${rest.length} more` : first.description;
};

const dueCopy = (invoice: Invoice) => {
  const today = new Date(new Date().toDateString()).getTime();
  const due = parseCalendarDate(invoice.due_date).getTime();
  const diff = Math.round((due - today) / DAY_MS);

  if (diff > 1) return `Due in ${diff} days`;
  if (diff === 1) return "Due tomorrow";
  if (diff === 0) return "Due today";
  if (diff === -1) return "1 day overdue";
  return `${Math.abs(diff)} days overdue`;
};

export default function InvoicesPage() {
  const { formatAmount: fmt } = useCurrency();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [aging, setAging] = useState<AgingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"list" | "aging">("list");
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState("");
  const [selectedBucket, setSelectedBucket] = useState("current");
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [invoiceList, agingReport] = await Promise.all([
        invoicesApi.list(),
        invoicesApi.aging().catch(() => null),
      ]);
      setInvoices(invoiceList);
      setAging(agingReport);
    } catch {
      setActionError("Unable to load invoices right now. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!aging?.buckets?.length) return;
    const hasSelection = aging.buckets.some((bucket) => bucket.bucket === selectedBucket);
    if (hasSelection) return;
    const firstNonEmpty = aging.buckets.find((bucket) => bucket.count > 0)?.bucket ?? aging.buckets[0].bucket;
    setSelectedBucket(firstNonEmpty);
  }, [aging, selectedBucket]);

  const filtered = filter ? invoices.filter((invoice) => invoice.status === filter) : invoices;
  const selectedAgingBucket = aging?.buckets.find((bucket) => bucket.bucket === selectedBucket) ?? aging?.buckets[0] ?? null;
  const totalBilled = invoices.reduce((sum, invoice) => sum + invoice.total, 0);
  const totalCollected = invoices.reduce((sum, invoice) => sum + invoice.amount_paid, 0);
  const activeExposure = invoices
    .filter((invoice) => invoice.status !== "paid" && invoice.status !== "cancelled")
    .reduce((sum, invoice) => sum + invoice.amount_due, 0);
  const collectionRate = totalBilled > 0 ? Math.round((totalCollected / totalBilled) * 100) : 0;
  const sentCount = invoices.filter((invoice) => invoice.status === "sent").length;
  const draftCount = invoices.filter((invoice) => invoice.status === "draft").length;
  const overdueCount = invoices.filter((invoice) => invoice.days_overdue > 0 && invoice.amount_due > 0).length;
  const upcoming = [...invoices]
    .filter((invoice) => invoice.amount_due > 0 && invoice.status !== "cancelled" && invoice.status !== "paid")
    .sort((left, right) => parseCalendarDate(left.due_date).getTime() - parseCalendarDate(right.due_date).getTime())
    .slice(0, 3);

  const handleSend = async (invoice: Invoice) => {
    setActionError("");
    setActionMessage("");
    setSendingId(invoice.id);
    try {
      const updated = await invoicesApi.send(invoice.id);
      setActionMessage(`Invoice ${updated.invoice_number} emailed to ${updated.client_email ?? invoice.client_email}.`);
      await load();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Invoice delivery failed.");
    } finally {
      setSendingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <section
        className="glass animate-fade-up overflow-hidden"
        style={{
          background:
            "radial-gradient(circle at top right, rgba(201, 169, 98, 0.14), transparent 36%), linear-gradient(135deg, rgba(17, 17, 17, 0.98) 0%, rgba(8, 8, 8, 0.98) 100%)",
        }}
      >
        <div className="grid gap-6 px-6 py-7 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)]">
          <div className="space-y-5">
            <div
              className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.2em]"
              style={{ borderColor: "rgba(201, 169, 98, 0.24)", color: "var(--accent)", background: "rgba(201, 169, 98, 0.08)" }}
            >
              <Sparkles size={12} />
              Collections Desk
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold sm:text-4xl" style={{ color: "var(--text)" }}>
                Invoices that feel operational, not ornamental.
              </h1>
              <p className="max-w-2xl text-sm leading-7 sm:text-base" style={{ color: "var(--text-muted)" }}>
                Generate polished invoices, see receivables pressure at a glance, and push draft bills into the client
                inbox without leaving the workspace.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border p-4" style={{ borderColor: "rgba(201, 169, 98, 0.16)", background: "rgba(255,255,255,0.02)" }}>
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                  <Wallet size={13} />
                  Receivables
                </div>
                <div className="mt-3 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                  {fmt(aging?.total_outstanding ?? activeExposure)}
                </div>
                <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {overdueCount} invoice{overdueCount === 1 ? "" : "s"} need collection attention.
                </p>
              </div>
              <div className="rounded-2xl border p-4" style={{ borderColor: "rgba(94, 158, 126, 0.16)", background: "rgba(255,255,255,0.02)" }}>
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                  <TrendingUp size={13} />
                  Collection Rate
                </div>
                <div className="mt-3 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                  {collectionRate}%
                </div>
                <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {fmt(totalCollected)} collected out of {fmt(totalBilled)} billed.
                </p>
              </div>
              <div className="rounded-2xl border p-4" style={{ borderColor: "rgba(107, 142, 194, 0.16)", background: "rgba(255,255,255,0.02)" }}>
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                  <Receipt size={13} />
                  Pipeline
                </div>
                <div className="mt-3 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                  {invoices.length}
                </div>
                <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                  {draftCount} draft / {sentCount} sent / {overdueCount} overdue by date.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-[24px] border p-5" style={{ borderColor: "rgba(201, 169, 98, 0.16)", background: "linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)" }}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                  Next to Collect
                </p>
                <h2 className="mt-2 text-lg font-semibold" style={{ color: "var(--text)" }}>
                  Upcoming invoices
                </h2>
              </div>
              <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2" style={{ minHeight: 44 }}>
                {showForm ? <X size={16} /> : <Plus size={16} />}
                {showForm ? "Close form" : "New invoice"}
              </button>
            </div>

            <div className="mt-5 space-y-3">
              {upcoming.length === 0 ? (
                <div className="rounded-2xl border px-4 py-5 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)", background: "rgba(255,255,255,0.02)" }}>
                  No open invoices yet. Create one to seed the receivables pipeline.
                </div>
              ) : (
                upcoming.map((invoice) => (
                  <div key={invoice.id} className="rounded-2xl border px-4 py-4" style={{ borderColor: "rgba(201, 169, 98, 0.14)", background: "rgba(0,0,0,0.18)" }}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold" style={{ color: "var(--text)" }}>
                          {invoice.client_name}
                        </p>
                        <p className="mt-1 text-xs uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
                          {invoice.invoice_number}
                        </p>
                      </div>
                      <span
                        className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]"
                        style={{ background: STATUS_META[invoice.status].bg, color: STATUS_META[invoice.status].fg, border: `1px solid ${STATUS_META[invoice.status].border}` }}
                      >
                        {STATUS_META[invoice.status].label}
                      </span>
                    </div>
                    <div className="mt-4 flex items-center justify-between text-sm">
                      <span style={{ color: "var(--text-muted)" }}>{dueCopy(invoice)}</span>
                      <span className="font-semibold" style={{ color: "var(--text)" }}>
                        {formatMoney(invoice.amount_due, invoice.currency_code)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      {showForm && <InvoiceForm onSuccess={() => { setShowForm(false); load(); }} onCancel={() => setShowForm(false)} />}

      {(actionMessage || actionError) && (
        <div
          className="glass animate-fade-up flex items-start gap-3 px-4 py-4"
          style={{
            borderColor: actionError ? "rgba(199, 80, 80, 0.24)" : "rgba(94, 158, 126, 0.24)",
            background: actionError ? "rgba(199, 80, 80, 0.08)" : "rgba(94, 158, 126, 0.08)",
          }}
        >
          <CircleAlert size={18} style={{ color: actionError ? "var(--danger)" : "var(--success)", marginTop: 2 }} />
          <div className="text-sm" style={{ color: actionError ? "var(--danger)" : "var(--text)" }}>
            {actionError || actionMessage}
          </div>
        </div>
      )}

      {!showForm && (
        <>
          <div className="flex flex-wrap gap-2 animate-fade-up delay-1">
            {(["list", "aging"] as const).map((currentTab) => (
              <button
                key={currentTab}
                onClick={() => setTab(currentTab)}
                className="rounded-full px-4 py-2 text-sm font-medium"
                style={{
                  minHeight: 44,
                  background: tab === currentTab ? "var(--accent-soft)" : "var(--surface)",
                  color: tab === currentTab ? "var(--accent)" : "var(--text-muted)",
                  border: `1px solid ${tab === currentTab ? "var(--accent)" : "var(--border)"}`,
                }}
              >
                {currentTab === "aging" ? "Aging Report" : "Invoice Ledger"}
              </button>
            ))}
          </div>

          {tab === "list" && (
            <>
              <div className="flex flex-wrap gap-2 animate-fade-up delay-2">
                {["", "draft", "sent", "paid", "partially_paid", "overdue"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilter(status)}
                    className="rounded-full px-3 py-1.5 text-xs font-medium capitalize"
                    style={{
                      minHeight: 40,
                      background: filter === status ? "var(--accent-soft)" : "var(--surface)",
                      color: filter === status ? "var(--accent)" : "var(--text-dim)",
                      border: `1px solid ${filter === status ? "rgba(201, 169, 98, 0.28)" : "var(--border)"}`,
                    }}
                  >
                    {status || "All"}
                  </button>
                ))}
              </div>

              {loading ? (
                <div className="skeleton" style={{ height: 320 }} />
              ) : filtered.length === 0 ? (
                <div className="glass p-12 text-center">
                  <FileCheck size={40} className="mx-auto mb-3" style={{ color: "var(--text-dim)" }} />
                  <p className="text-sm" style={{ color: "var(--text-dim)" }}>
                    No invoices found.
                  </p>
                </div>
              ) : (
                <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(300px,0.86fr)]">
                  <div className="space-y-4">
                    {filtered.map((invoice, index) => {
                      const statusMeta = STATUS_META[invoice.status];
                      const paidRatio = invoice.total > 0 ? Math.min(invoice.amount_paid / invoice.total, 1) : 0;
                      const canSend = invoice.status === "draft" && Boolean(invoice.client_email);

                      return (
                        <article
                          key={invoice.id}
                          className="glass glass-hover animate-fade-up overflow-hidden"
                          style={{ animationDelay: `${index * 40}ms` }}
                        >
                          <div className="flex flex-col gap-5 p-5 lg:flex-row lg:items-start lg:justify-between">
                            <div className="space-y-4">
                              <div className="flex flex-wrap items-center gap-3">
                                <span
                                  className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]"
                                  style={{ background: statusMeta.bg, color: statusMeta.fg, border: `1px solid ${statusMeta.border}` }}
                                >
                                  {statusMeta.label}
                                </span>
                                <span className="font-mono text-sm font-semibold" style={{ color: "var(--accent)" }}>
                                  {invoice.invoice_number}
                                </span>
                              </div>

                              <div>
                                <h3 className="text-xl font-semibold" style={{ color: "var(--text)" }}>
                                  {invoice.client_name}
                                </h3>
                                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
                                  <span className="flex items-center gap-2">
                                    <Mail size={14} />
                                    {invoice.client_email ?? "No client email on file"}
                                  </span>
                                  <span className="flex items-center gap-2">
                                    <Receipt size={14} />
                                    {summarizeLineItems(invoice)}
                                  </span>
                                </div>
                              </div>

                              <div className="grid gap-3 sm:grid-cols-3">
                                <div className="rounded-2xl border p-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
                                    <CalendarDays size={12} />
                                    Issued
                                  </div>
                                  <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                                    {formatDate(invoice.issue_date)}
                                  </p>
                                </div>
                                <div className="rounded-2xl border p-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
                                    <Clock3 size={12} />
                                    Due
                                  </div>
                                  <p className="mt-2 text-sm font-medium" style={{ color: "var(--text)" }}>
                                    {formatDate(invoice.due_date)}
                                  </p>
                                  <p className="mt-1 text-xs" style={{ color: invoice.days_overdue > 0 ? "var(--warning)" : "var(--text-muted)" }}>
                                    {dueCopy(invoice)}
                                  </p>
                                </div>
                                <div className="rounded-2xl border p-3" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
                                    <Wallet size={12} />
                                    Outstanding
                                  </div>
                                  <p className="mt-2 text-sm font-medium" style={{ color: invoice.amount_due > 0 ? "var(--warning)" : "var(--success)" }}>
                                    {formatMoney(invoice.amount_due, invoice.currency_code)}
                                  </p>
                                </div>
                              </div>
                            </div>

                            <div className="min-w-[220px] rounded-[22px] border p-4" style={{ borderColor: "rgba(201, 169, 98, 0.16)", background: "linear-gradient(180deg, rgba(201, 169, 98, 0.08), rgba(255,255,255,0.02))" }}>
                              <p className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                                Collection Snapshot
                              </p>
                              <p className="mt-3 text-3xl font-semibold" style={{ color: "var(--text)" }}>
                                {formatMoney(invoice.total, invoice.currency_code)}
                              </p>
                              <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                                Total bill / {formatMoney(invoice.amount_paid, invoice.currency_code)} paid so far
                              </p>
                              <div className="mt-4 h-2 overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${Math.max(paidRatio * 100, invoice.amount_paid > 0 ? 8 : 0)}%`,
                                    background: "linear-gradient(90deg, var(--success), var(--accent))",
                                  }}
                                />
                              </div>
                              <div className="mt-4 space-y-3">
                                <div className="flex items-center justify-between text-sm">
                                  <span style={{ color: "var(--text-muted)" }}>Tax</span>
                                  <span style={{ color: "var(--text)" }}>{(invoice.tax_rate * 100).toFixed(0)}%</span>
                                </div>
                                <div className="flex items-center justify-between text-sm">
                                  <span style={{ color: "var(--text-muted)" }}>Amount due</span>
                                  <span className="font-semibold" style={{ color: "var(--text)" }}>
                                    {formatMoney(invoice.amount_due, invoice.currency_code)}
                                  </span>
                                </div>
                              </div>
                              <div className="mt-5 flex flex-wrap gap-2">
                                <button
                                  onClick={() => handleSend(invoice)}
                                  disabled={!canSend || sendingId === invoice.id}
                                  className="btn-primary flex items-center gap-2"
                                  style={{ minHeight: 44, opacity: !canSend || sendingId === invoice.id ? 0.55 : 1 }}
                                  title={invoice.client_email ? "Send invoice email" : "Add a client email before sending"}
                                >
                                  <Send size={15} />
                                  {sendingId === invoice.id ? "Sending..." : invoice.status === "draft" ? "Send invoice" : "Resend"}
                                </button>
                                <div className="flex items-center gap-2 rounded-full border px-3 py-2 text-xs" style={{ minHeight: 44, borderColor: "var(--border)", color: "var(--text-muted)" }}>
                                  <ArrowRight size={12} />
                                  {invoice.client_email ?? "Missing recipient"}
                                </div>
                              </div>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>

                  <aside className="glass p-5 animate-fade-up delay-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                          Collections Pulse
                        </p>
                        <h3 className="mt-2 text-lg font-semibold" style={{ color: "var(--text)" }}>
                          Where attention should go next
                        </h3>
                      </div>
                      <Sparkles size={16} style={{ color: "var(--accent)" }} />
                    </div>

                    <div className="mt-5 grid gap-3">
                      {[
                        { label: "Drafts ready to send", value: draftCount, tone: "var(--accent)" },
                        { label: "Sent and awaiting payment", value: sentCount, tone: "var(--warning)" },
                        { label: "Past due by calendar", value: overdueCount, tone: "var(--danger)" },
                      ].map((row) => (
                        <div key={row.label} className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                          <div className="flex items-center justify-between">
                            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                              {row.label}
                            </span>
                            <span className="text-xl font-semibold" style={{ color: row.tone }}>
                              {row.value}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="mt-6 rounded-[22px] border p-4" style={{ borderColor: "rgba(201, 169, 98, 0.16)", background: "rgba(201, 169, 98, 0.06)" }}>
                      <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                        Operator Notes
                      </p>
                      <p className="mt-3 text-sm leading-7" style={{ color: "var(--text-muted)" }}>
                        Sending now uses the shared email service and targets the email stored on the invoice. Drafts
                        without a recipient stay blocked until a client email is added.
                      </p>
                    </div>
                  </aside>
                </div>
              )}
            </>
          )}

          {tab === "aging" && aging && (
            <div className="space-y-4 animate-fade-up delay-2">
              <div className="glass p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                      Total Outstanding
                    </span>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                      Date-based buckets stay aligned with each invoice&apos;s overdue count.
                    </p>
                  </div>
                  <span className="text-2xl font-bold" style={{ color: "var(--warning)" }}>
                    {fmt(aging.total_outstanding)}
                  </span>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-5">
                {aging.buckets.map((bucket) => {
                  const bucketMeta = AGING_BUCKET_META[bucket.bucket] ?? AGING_BUCKET_META.current;
                  const isActive = selectedBucket === bucket.bucket;
                  return (
                    <button
                      key={bucket.bucket}
                      onClick={() => setSelectedBucket(bucket.bucket)}
                      className="glass text-left transition-all hover:-translate-y-0.5"
                      style={{
                        minHeight: 176,
                        padding: 20,
                        borderColor: isActive ? bucketMeta.border : "var(--border)",
                        background: isActive ? bucketMeta.surface : "var(--surface)",
                        boxShadow: isActive ? `0 0 0 1px ${bucketMeta.border}` : "none",
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                          {bucketMeta.title}
                        </span>
                        <span className="text-xs uppercase tracking-[0.16em]" style={{ color: bucketMeta.tone }}>
                          {bucket.count} inv
                        </span>
                      </div>
                      <p className="mt-4 text-2xl font-semibold" style={{ color: bucketMeta.tone }}>
                        {fmt(bucket.total)}
                      </p>
                      <p className="mt-3 text-sm leading-6" style={{ color: "var(--text-muted)" }}>
                        {bucketMeta.note}
                      </p>
                    </button>
                  );
                })}
              </div>

              {selectedAgingBucket && (
                <section className="grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_minmax(320px,0.82fr)]">
                  <div className="glass p-5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                          Selected bucket
                        </p>
                        <h3 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                          {AGING_BUCKET_META[selectedAgingBucket.bucket]?.title ?? selectedAgingBucket.bucket}
                        </h3>
                        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                          {AGING_BUCKET_META[selectedAgingBucket.bucket]?.note}
                        </p>
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                          Exposure
                        </p>
                        <p className="mt-2 text-2xl font-semibold" style={{ color: "var(--text)" }}>
                          {fmt(selectedAgingBucket.total)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {selectedAgingBucket.invoices.length === 0 ? (
                        <div className="rounded-2xl border px-4 py-6 text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)", background: "rgba(255,255,255,0.02)" }}>
                          No invoices in this bucket right now.
                        </div>
                      ) : (
                        selectedAgingBucket.invoices.map((invoice) => (
                          <div key={invoice.id} className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-mono text-sm font-semibold" style={{ color: "var(--accent)" }}>
                                    {invoice.invoice_number}
                                  </span>
                                  <span
                                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]"
                                    style={{ background: STATUS_META[invoice.status].bg, color: STATUS_META[invoice.status].fg, border: `1px solid ${STATUS_META[invoice.status].border}` }}
                                  >
                                    {STATUS_META[invoice.status].label}
                                  </span>
                                </div>
                                <h4 className="mt-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
                                  {invoice.client_name}
                                </h4>
                                <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                                  {summarizeLineItems(invoice)}
                                </p>
                              </div>
                              <div className="text-left sm:text-right">
                                <p className="text-xs uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
                                  Amount due
                                </p>
                                <p className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                                  {formatMoney(invoice.amount_due, invoice.currency_code)}
                                </p>
                                <p className="mt-1 text-sm" style={{ color: invoice.days_overdue > 0 ? "var(--warning)" : "var(--text-muted)" }}>
                                  {dueCopy(invoice)}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <aside className="glass p-5">
                    <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-dim)" }}>
                      Collection Guidance
                    </p>
                    <div className="mt-4 space-y-3">
                      {[
                        "Current: keep the relationship warm and confirm receipt early.",
                        "1-30: send a crisp reminder with the original invoice context.",
                        "31-60: escalate the tone, ask for payment timing, and surface blockers.",
                        "61+: move from reminders into a collection workflow with clear owners.",
                      ].map((tip) => (
                        <div key={tip} className="rounded-2xl border px-4 py-4 text-sm leading-7" style={{ borderColor: "var(--border)", color: "var(--text-muted)", background: "rgba(255,255,255,0.02)" }}>
                          {tip}
                        </div>
                      ))}
                    </div>
                  </aside>
                </section>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
