"use client";
import { useState, useMemo } from "react";
import { invoicesApi } from "@/lib/api";
import { Plus, Trash2, Calculator, FileText, User, Mail, Phone, MapPin, Calendar, Hash, Percent } from "lucide-react";

interface LineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  discount_pct: number;
}

const newLine = (): LineItem => ({
  id: crypto.randomUUID(),
  description: "",
  quantity: 1,
  unit_price: 0,
  discount_pct: 0,
});

const today = () => new Date().toISOString().slice(0, 10);
const plus30 = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
};

const PAYMENT_TERMS = [
  { label: "Due on Receipt", days: 0 },
  { label: "Net 15", days: 15 },
  { label: "Net 30", days: 30 },
  { label: "Net 45", days: 45 },
  { label: "Net 60", days: 60 },
  { label: "Net 90", days: 90 },
  { label: "Custom", days: -1 },
];

const CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "CAD", "AUD", "JPY"];

const fmtMoney = (n: number, cur: string) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: cur, maximumFractionDigits: 2 }).format(n);

/* ─── Styles ─── */
const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--surface)",
  color: "var(--text)",
  fontSize: 13,
  outline: "none",
  transition: "border-color .2s",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 600,
  color: "var(--text-dim)",
  marginBottom: 4,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const sectionTitle = (icon: React.ReactNode, title: string) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
    <span style={{ color: "var(--accent)" }}>{icon}</span>
    <h4 style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{title}</h4>
    <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
  </div>
);

export default function InvoiceForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  /* ── State ── */
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientAddress, setClientAddress] = useState("");
  const [clientGST, setClientGST] = useState("");
  const [invoicePrefix, setInvoicePrefix] = useState("INV");
  const [poNumber, setPONumber] = useState("");
  const [issueDate, setIssueDate] = useState(today());
  const [dueDate, setDueDate] = useState(plus30());
  const [paymentTerms, setPaymentTerms] = useState("Net 30");
  const [currency, setCurrency] = useState("INR");
  const [taxRate, setTaxRate] = useState(18);
  const [taxLabel, setTaxLabel] = useState("GST");
  const [discountType, setDiscountType] = useState<"none" | "pct" | "flat">("none");
  const [discountValue, setDiscountValue] = useState(0);
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("Payment is due within the specified period.\nLate payments may incur a 2% monthly interest charge.");
  const [lineItems, setLineItems] = useState<LineItem[]>([newLine()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  /* ── Line item helpers ── */
  const addLine = () => setLineItems(p => [...p, newLine()]);
  const removeLine = (id: string) => setLineItems(p => p.length > 1 ? p.filter(l => l.id !== id) : p);
  const updateLine = (id: string, field: keyof LineItem, value: string | number) =>
    setLineItems(p => p.map(l => l.id === id ? { ...l, [field]: value } : l));

  /* ── Calculations ── */
  const calcs = useMemo(() => {
    const lineSubtotals = lineItems.map(l => {
      const base = l.quantity * l.unit_price;
      return base - (base * l.discount_pct / 100);
    });
    const subtotal = lineSubtotals.reduce((s, v) => s + v, 0);
    const discount = discountType === "pct" ? subtotal * discountValue / 100
      : discountType === "flat" ? discountValue : 0;
    const afterDiscount = subtotal - discount;
    const tax = afterDiscount * taxRate / 100;
    const total = afterDiscount + tax;
    return { lineSubtotals, subtotal, discount, afterDiscount, tax, total };
  }, [lineItems, discountType, discountValue, taxRate]);

  /* ── Payment terms handler ── */
  const handleTermsChange = (label: string) => {
    setPaymentTerms(label);
    const term = PAYMENT_TERMS.find(t => t.label === label);
    if (term && term.days >= 0) {
      const d = new Date(issueDate);
      d.setDate(d.getDate() + term.days);
      setDueDate(d.toISOString().slice(0, 10));
    }
  };

  /* ── Submit ── */
  const handleSubmit = async () => {
    if (!clientName.trim()) { setError("Client name is required"); return; }
    if (lineItems.some(l => !l.description.trim())) { setError("All line items need a description"); return; }
    if (lineItems.some(l => l.quantity <= 0 || l.unit_price <= 0)) { setError("Quantity & price must be > 0"); return; }
    setError(""); setSubmitting(true);
    try {
      await invoicesApi.create({
        client_name: clientName,
        client_email: clientEmail || undefined,
        issue_date: issueDate,
        due_date: dueDate,
        items: lineItems.map(l => ({
          description: l.description,
          quantity: l.quantity,
          unit_price: l.unit_price,
          amount: Number((l.quantity * l.unit_price * (1 - l.discount_pct / 100)).toFixed(2)),
        })),
        tax_rate: taxRate / 100,
        currency_code: currency,
        notes: [
          clientPhone ? `Phone: ${clientPhone}` : "",
          clientAddress ? `Address: ${clientAddress}` : "",
          clientGST ? `GSTIN: ${clientGST}` : "",
          poNumber ? `PO#: ${poNumber}` : "",
          notes,
          terms ? `\n---\nTerms:\n${terms}` : "",
        ].filter(Boolean).join("\n"),
      });
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create invoice");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="glass animate-fade-up" style={{ overflow: "hidden" }}>
      {/* ── Header ── */}
      <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--accent-soft)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <FileText size={18} style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}>Create Invoice</h3>
            <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Fill in details to generate a professional invoice</p>
          </div>
        </div>
        <button onClick={onCancel} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--text-dim)", fontSize: 12, cursor: "pointer" }}>Cancel</button>
      </div>

      <div style={{ padding: 24, display: "grid", gap: 24 }}>
        {/* ═══ Row 1: Client + Invoice Details ═══ */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* ── Client Details ── */}
          <div>
            {sectionTitle(<User size={14} />, "Client Details")}
            <div style={{ display: "grid", gap: 12 }}>
              <div>
                <label style={labelStyle}>Client / Company Name *</label>
                <input style={inputStyle} value={clientName} onChange={e => setClientName(e.target.value)} placeholder="Acme Corp Pvt Ltd" />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={labelStyle}><Mail size={10} style={{ display: "inline", marginRight: 4 }} />Email</label>
                  <input style={inputStyle} type="email" value={clientEmail} onChange={e => setClientEmail(e.target.value)} placeholder="billing@acme.com" />
                </div>
                <div>
                  <label style={labelStyle}><Phone size={10} style={{ display: "inline", marginRight: 4 }} />Phone</label>
                  <input style={inputStyle} value={clientPhone} onChange={e => setClientPhone(e.target.value)} placeholder="+91 98765 43210" />
                </div>
              </div>
              <div>
                <label style={labelStyle}><MapPin size={10} style={{ display: "inline", marginRight: 4 }} />Billing Address</label>
                <textarea style={{ ...inputStyle, minHeight: 56, resize: "vertical" }} value={clientAddress} onChange={e => setClientAddress(e.target.value)} placeholder="123 Business Park, Mumbai 400001" />
              </div>
              <div>
                <label style={labelStyle}>GSTIN / Tax ID</label>
                <input style={inputStyle} value={clientGST} onChange={e => setClientGST(e.target.value)} placeholder="27AABCU9603R1ZM" />
              </div>
            </div>
          </div>

          {/* ── Invoice Meta ── */}
          <div>
            {sectionTitle(<Hash size={14} />, "Invoice Details")}
            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={labelStyle}>Invoice Prefix</label>
                  <input style={inputStyle} value={invoicePrefix} onChange={e => setInvoicePrefix(e.target.value)} placeholder="INV" />
                </div>
                <div>
                  <label style={labelStyle}>PO / Reference #</label>
                  <input style={inputStyle} value={poNumber} onChange={e => setPONumber(e.target.value)} placeholder="PO-2026-001" />
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={labelStyle}><Calendar size={10} style={{ display: "inline", marginRight: 4 }} />Issue Date *</label>
                  <input style={inputStyle} type="date" value={issueDate} onChange={e => { setIssueDate(e.target.value); handleTermsChange(paymentTerms); }} />
                </div>
                <div>
                  <label style={labelStyle}><Calendar size={10} style={{ display: "inline", marginRight: 4 }} />Due Date *</label>
                  <input style={inputStyle} type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={labelStyle}>Payment Terms</label>
                  <select style={inputStyle} value={paymentTerms} onChange={e => handleTermsChange(e.target.value)}>
                    {PAYMENT_TERMS.map(t => <option key={t.label} value={t.label}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Currency</label>
                  <select style={inputStyle} value={currency} onChange={e => setCurrency(e.target.value)}>
                    {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={labelStyle}><Percent size={10} style={{ display: "inline", marginRight: 4 }} />Tax Rate (%)</label>
                  <input style={inputStyle} type="number" step="0.01" min="0" max="100" value={taxRate} onChange={e => setTaxRate(Number(e.target.value))} />
                </div>
                <div>
                  <label style={labelStyle}>Tax Label</label>
                  <select style={inputStyle} value={taxLabel} onChange={e => setTaxLabel(e.target.value)}>
                    {["GST", "IGST", "CGST+SGST", "VAT", "Sales Tax", "None"].map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ Line Items ═══ */}
        <div>
          {sectionTitle(<Calculator size={14} />, "Line Items")}
          <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
            {/* Table Header */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 80px 120px 80px 120px 36px", gap: 0, padding: "10px 12px", background: "var(--surface-hover)", borderBottom: "1px solid var(--border)" }}>
              {["Description", "Qty", "Unit Price", "Disc %", "Amount", ""].map(h => (
                <span key={h} style={{ fontSize: 10, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</span>
              ))}
            </div>
            {/* Rows */}
            {lineItems.map((item, idx) => (
              <div key={item.id} style={{ display: "grid", gridTemplateColumns: "2fr 80px 120px 80px 120px 36px", gap: 0, padding: "8px 12px", borderBottom: "1px solid var(--border)", alignItems: "center", background: idx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                <input style={{ ...inputStyle, border: "none", background: "transparent", padding: "6px 4px" }} value={item.description} onChange={e => updateLine(item.id, "description", e.target.value)} placeholder="Service / Product description" />
                <input style={{ ...inputStyle, border: "none", background: "transparent", padding: "6px 4px", textAlign: "center" }} type="number" min="1" value={item.quantity} onChange={e => updateLine(item.id, "quantity", Number(e.target.value))} />
                <input style={{ ...inputStyle, border: "none", background: "transparent", padding: "6px 4px", textAlign: "right" }} type="number" step="0.01" min="0" value={item.unit_price} onChange={e => updateLine(item.id, "unit_price", Number(e.target.value))} />
                <input style={{ ...inputStyle, border: "none", background: "transparent", padding: "6px 4px", textAlign: "center" }} type="number" step="0.1" min="0" max="100" value={item.discount_pct} onChange={e => updateLine(item.id, "discount_pct", Number(e.target.value))} />
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", textAlign: "right", paddingRight: 8 }}>
                  {fmtMoney(calcs.lineSubtotals[idx] || 0, currency)}
                </span>
                <button onClick={() => removeLine(item.id)} style={{ background: "transparent", border: "none", cursor: "pointer", padding: 4, borderRadius: 4, opacity: lineItems.length === 1 ? 0.2 : 1 }} disabled={lineItems.length === 1}>
                  <Trash2 size={14} style={{ color: "var(--danger)" }} />
                </button>
              </div>
            ))}
            {/* Add Row */}
            <button onClick={addLine} style={{ width: "100%", padding: "10px", background: "transparent", border: "none", color: "var(--accent)", fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
              <Plus size={14} /> Add Line Item
            </button>
          </div>
        </div>

        {/* ═══ Bottom: Notes + Summary ═══ */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* ── Notes & Terms ── */}
          <div style={{ display: "grid", gap: 12 }}>
            <div>
              <label style={labelStyle}>Notes / Memo</label>
              <textarea style={{ ...inputStyle, minHeight: 60, resize: "vertical" }} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Thank you for your business!" />
            </div>
            <div>
              <label style={labelStyle}>Terms & Conditions</label>
              <textarea style={{ ...inputStyle, minHeight: 60, resize: "vertical", fontSize: 11 }} value={terms} onChange={e => setTerms(e.target.value)} />
            </div>
            <div>
              <label style={labelStyle}>Discount</label>
              <div style={{ display: "flex", gap: 8 }}>
                <select style={{ ...inputStyle, width: 120 }} value={discountType} onChange={e => setDiscountType(e.target.value as "none" | "pct" | "flat")}>
                  <option value="none">None</option>
                  <option value="pct">Percentage</option>
                  <option value="flat">Flat Amount</option>
                </select>
                {discountType !== "none" && (
                  <input style={{ ...inputStyle, width: 120 }} type="number" step="0.01" min="0" value={discountValue} onChange={e => setDiscountValue(Number(e.target.value))} placeholder={discountType === "pct" ? "%" : currency} />
                )}
              </div>
            </div>
          </div>

          {/* ── Totals ── */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
            <h4 style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 16 }}>Summary</h4>
            <div style={{ display: "grid", gap: 10 }}>
              {[
                { label: "Subtotal", value: calcs.subtotal },
                ...(calcs.discount > 0 ? [{ label: `Discount${discountType === "pct" ? ` (${discountValue}%)` : ""}`, value: -calcs.discount }] : []),
                { label: `${taxLabel} (${taxRate}%)`, value: calcs.tax },
              ].map(row => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "var(--text-muted)" }}>
                  <span>{row.label}</span>
                  <span style={{ fontWeight: 500, color: row.value < 0 ? "var(--success)" : "var(--text)" }}>{fmtMoney(row.value, currency)}</span>
                </div>
              ))}
              <div style={{ borderTop: "2px solid var(--border)", paddingTop: 12, marginTop: 4, display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 15, fontWeight: 800, color: "var(--text)" }}>Total Due</span>
                <span style={{ fontSize: 20, fontWeight: 800, color: "var(--accent)" }}>{fmtMoney(calcs.total, currency)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* ═══ Error + Actions ═══ */}
        {error && (
          <div style={{ padding: "10px 14px", borderRadius: 8, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 12, fontWeight: 500 }}>{error}</div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button onClick={onCancel} style={{ padding: "10px 20px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-dim)", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
            Discard
          </button>
          <button onClick={handleSubmit} disabled={submitting} className="btn-primary" style={{ padding: "10px 28px", fontSize: 13, fontWeight: 600, opacity: submitting ? 0.6 : 1 }}>
            {submitting ? "Creating…" : "Create Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}
