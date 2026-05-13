"use client";
import { useEffect, useState, useCallback } from "react";
import { taxApi } from "@/lib/api";
import type {
  TaxEstimate, TaxCategory, TaxJurisdiction,
  ExternalTaxCalculationResponse, IndiaRegimeComparisonResponse,
  EffectiveHourlyRateResponse,
} from "@/lib/types";
import { Receipt, Plus, X, Globe, Calculator, TrendingDown, Clock, IndianRupee, DollarSign, ChevronDown, Filter } from "lucide-react";
import { useCurrency } from "@/components/CurrencyContext";

type Tab = "overview" | "categories" | "jurisdictions" | "calculator";
type CalcMode = "india" | "india-hra" | "india-gratuity" | "us" | "global" | "compare" | "hourly";

export default function TaxPage() {
  const { formatAmount: fmt } = useCurrency();
  const [estimates, setEstimates] = useState<TaxEstimate[]>([]);
  const [categories, setCategories] = useState<TaxCategory[]>([]);
  const [jurisdictions, setJurisdictions] = useState<TaxJurisdiction[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [showGen, setShowGen] = useState(false);

  // Jurisdiction filters
  type JurSection = "all" | "slabs" | "deductions" | "deadlines" | "penalties" | "gst_fica" | "tds" | "capital_gains" | "alt_filing";
  const [jurCountry, setJurCountry] = useState<string>("all");
  const [jurSection, setJurSection] = useState<JurSection>("all");

  const sectionLabels: Record<JurSection, string> = {
    all: "All Sections", slabs: "Income Tax Slabs", deductions: "Key Deductions",
    deadlines: "Filing Deadlines", penalties: "Penalties", gst_fica: "GST / FICA",
    tds: "TDS Rates", capital_gains: "Capital Gains", alt_filing: "Alt. Filing Status",
  };

  // Calculator state
  const [calcMode, setCalcMode] = useState<CalcMode>("india");
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcResult, setCalcResult] = useState<ExternalTaxCalculationResponse | IndiaRegimeComparisonResponse | EffectiveHourlyRateResponse | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);

  const [quarters, setQuarters] = useState<string[]>([]);

  const load = useCallback(async () => {
    try {
      const [e, c, j, q] = await Promise.all([
        taxApi.listEstimates(), taxApi.listCategories(),
        taxApi.listJurisdictions(), taxApi.availableQuarters(),
      ]);
      setEstimates(e); setCategories(c); setJurisdictions(j); setQuarters(q);
    } catch {} finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const handleGen = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await taxApi.generateEstimate(fd.get("quarter") as string, fd.get("jurisdiction") as string);
      setShowGen(false);
      await load();
    } catch (err) {
      console.error("Failed to generate estimate", err);
    }
  };

  const handleCalc = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCalcLoading(true); setCalcError(null); setCalcResult(null);
    const fd = new FormData(e.currentTarget);
    try {
      let result;
      switch (calcMode) {
        case "india":
          result = await taxApi.calculateIndiaTax({
            gross_income: Number(fd.get("gross_income")),
            regime: fd.get("regime") as string || "new-2026-27",
            apply_standard_deduction: fd.get("std_ded") !== "off",
          }); break;
        case "india-hra":
          result = await taxApi.calculateIndiaHRA({
            basic_salary: Number(fd.get("basic_salary")),
            hra_received: Number(fd.get("hra_received")),
            rent_paid: Number(fd.get("rent_paid")),
            is_metro: fd.get("is_metro") === "on",
          }); break;
        case "india-gratuity":
          result = await taxApi.calculateIndiaGratuity({
            monthly_basic: Number(fd.get("monthly_basic")),
            years_of_service: Number(fd.get("years")),
            covered_by_act: fd.get("covered") !== "off",
          }); break;
        case "us":
          result = await taxApi.calculateUSTax({
            income: Number(fd.get("income")),
            filing_status: fd.get("filing_status") as string || "single",
            qbi_deduction: fd.get("qbi") !== "off",
          }); break;
        case "global":
          result = await taxApi.calculateGlobalTax({
            country_code: fd.get("country_code") as string,
            income: Number(fd.get("income")),
          }); break;
        case "compare":
          result = await taxApi.compareIndiaRegimes({
            gross_income: Number(fd.get("gross_income")),
          }); break;
        case "hourly":
          result = await taxApi.calculateHourlyRate({
            country_code: fd.get("country_code") as string,
            annual_income: Number(fd.get("annual_income")),
            weekly_hours: Number(fd.get("weekly_hours") || 40),
            paid_days_off: Number(fd.get("paid_days_off") || 20),
          }); break;
      }
      setCalcResult(result);
    } catch (err: unknown) {
      setCalcError(err instanceof Error ? err.message : "Calculation failed");
    } finally { setCalcLoading(false); }
  };

  const calcModes: { key: CalcMode; label: string; icon: React.ReactNode }[] = [
    { key: "india", label: "India Tax", icon: <IndianRupee size={14}/> },
    { key: "india-hra", label: "HRA", icon: <IndianRupee size={14}/> },
    { key: "india-gratuity", label: "Gratuity", icon: <IndianRupee size={14}/> },
    { key: "us", label: "US Tax", icon: <DollarSign size={14}/> },
    { key: "global", label: "Global", icon: <Globe size={14}/> },
    { key: "compare", label: "Regime Compare", icon: <TrendingDown size={14}/> },
    { key: "hourly", label: "Hourly Rate", icon: <Clock size={14}/> },
  ];

  const inputStyle: React.CSSProperties = {
    background: "var(--surface)", color: "var(--text)", border: "1px solid var(--border)",
    borderRadius: 8, padding: "10px 14px", fontSize: "0.875rem", width: "100%",
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between animate-fade-up">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Tax Management</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Quarterly estimates, deductions & live calculators</p>
        </div>
        <button onClick={() => setShowGen(!showGen)} className="btn-primary flex items-center gap-2">
          {showGen ? <X size={16}/> : <Plus size={16}/>} {showGen ? "Cancel" : "Generate Estimate"}
        </button>
      </div>

      {showGen && (
        <div className="glass p-6 animate-fade-up">
          <form onSubmit={handleGen} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <select name="quarter" required style={inputStyle}>
              <option value="">Select Quarter</option>
              {quarters.map(q => <option key={q} value={q}>{q}</option>)}
            </select>
            <select name="jurisdiction" required style={inputStyle}>
              <option value="">Jurisdiction</option>
              {jurisdictions.map(j => <option key={j.id} value={j.code}>{j.name}</option>)}
              <option value="IN">India</option><option value="US">United States</option>
            </select>
            <button type="submit" className="btn-primary">Generate</button>
          </form>
          {quarters.length === 0 && (
            <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>No transaction data found — import transactions first.</p>
          )}
        </div>
      )}

      <div className="flex gap-2 flex-wrap animate-fade-up delay-1">
        {(["overview","categories","jurisdictions","calculator"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className="px-4 py-2 rounded-lg text-sm font-medium capitalize flex items-center gap-2" style={{
            background: tab===t ? "var(--accent-soft)" : "var(--surface)",
            color: tab===t ? "var(--accent)" : "var(--text-muted)",
            border: `1px solid ${tab===t ? "var(--accent)" : "var(--border)"}`,
          }}>
            {t === "calculator" && <Calculator size={14}/>}
            {t}
          </button>
        ))}
      </div>

      {loading && tab !== "calculator" ? <div className="skeleton" style={{ height: 200 }}/> : (
        <>
          {/* ─── Overview Tab ─── */}
          {tab === "overview" && (estimates.length === 0 ? (
            <div className="glass p-12 text-center"><Receipt size={40} className="mx-auto mb-3" style={{ color:"var(--text-dim)" }}/><p className="text-sm" style={{ color:"var(--text-dim)" }}>No estimates yet.</p></div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {estimates.map((e,i) => (
                <div key={e.id} className={`glass p-5 animate-fade-up delay-${(i%4)+1}`}>
                  <div className="flex justify-between mb-3">
                    <span className="text-sm font-semibold" style={{ color:"var(--text)" }}>{e.quarter} — {e.jurisdiction_code}</span>
                    <span className="badge" style={{ background:"var(--warning-soft)", color:"var(--warning)" }}>{e.status}</span>
                  </div>
                  <div className="space-y-1 text-xs" style={{ color:"var(--text-muted)" }}>
                    <div className="flex justify-between"><span>Gross Income</span><span style={{ color:"var(--text)" }}>{fmt(e.gross_income || 0)}</span></div>
                    <div className="flex justify-between"><span>Deductions</span><span style={{ color:"var(--success)" }}>-{fmt(e.total_deductions || 0)}</span></div>
                    <div className="flex justify-between"><span>Taxable Income</span><span style={{ color:"var(--text)" }}>{fmt(e.taxable_income || 0)}</span></div>
                    <div className="flex justify-between"><span>Effective Rate</span><span style={{ color:"var(--text)" }}>{((e.effective_rate || 0) * 100).toFixed(1)}%</span></div>
                    {e.due_date && (
                      <div className="flex justify-between"><span>Due Date</span><span style={{ color:"var(--warning)" }}>{new Date(e.due_date).toLocaleDateString()}</span></div>
                    )}
                    <div className="flex justify-between pt-2 font-bold" style={{ borderTop:"1px solid var(--border)" }}>
                      <span style={{ color:"var(--text)" }}>Est. Tax</span>
                      <span style={{ color:"var(--accent)" }}>{fmt(e.estimated_tax || 0)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}

          {/* ─── Categories Tab ─── */}
          {tab === "categories" && (
            <div className="glass overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr style={{ borderBottom:"1px solid var(--border)" }}>
                  <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Category</th>
                  <th className="text-left p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>Deductibility</th>
                  <th className="text-right p-4 text-xs uppercase" style={{ color:"var(--text-dim)" }}>%</th>
                </tr></thead>
                <tbody>{categories.length === 0 ? (
                  <tr><td colSpan={3} className="p-8 text-center text-sm" style={{ color:"var(--text-dim)" }}>No categories configured yet.</td></tr>
                ) : categories.map(c => (
                  <tr key={c.id} style={{ borderBottom:"1px solid var(--border)" }}>
                    <td className="p-4 font-medium" style={{ color:"var(--text)" }}>{c.category}</td>
                    <td className="p-4"><span className="badge">{(c.tax_code || "non_deductible").replace(/_/g," ")}</span></td>
                    <td className="p-4 text-right" style={{ color:"var(--text-muted)" }}>{(c.deduction_rate ?? 0).toFixed(0)}%</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}

          {/* ─── Jurisdictions Tab ─── */}
          {tab === "jurisdictions" && (() => {
            const filtered = jurisdictions.filter(j => jurCountry === "all" || j.code === jurCountry);
            return (
            <div className="space-y-4 animate-fade-up">
              {/* Filter Bar */}
              <div className="glass p-4 flex flex-wrap items-center gap-3">
                <Filter size={16} style={{ color:"var(--text-dim)" }}/>
                {/* Country dropdown */}
                <div className="relative">
                  <select value={jurCountry} onChange={e => setJurCountry(e.target.value)}
                    className="appearance-none pl-3 pr-8 py-2 rounded-lg text-sm font-medium cursor-pointer"
                    style={{ background:"var(--surface)", color:"var(--text)", border:"1px solid var(--border)", outline:"none" }}>
                    <option value="all">All Countries</option>
                    {jurisdictions.map(j => <option key={j.id} value={j.code}>{j.code === "IN" ? "🇮🇳" : "🇺🇸"} {j.name}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color:"var(--text-dim)" }}/>
                </div>
                {/* Section dropdown */}
                <div className="relative">
                  <select value={jurSection} onChange={e => setJurSection(e.target.value as JurSection)}
                    className="appearance-none pl-3 pr-8 py-2 rounded-lg text-sm font-medium cursor-pointer"
                    style={{ background:"var(--surface)", color:"var(--text)", border:"1px solid var(--border)", outline:"none" }}>
                    {(Object.entries(sectionLabels) as [JurSection, string][]).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color:"var(--text-dim)" }}/>
                </div>
                {(jurCountry !== "all" || jurSection !== "all") && (
                  <button onClick={() => { setJurCountry("all"); setJurSection("all"); }}
                    className="text-xs px-2 py-1 rounded-md transition-colors"
                    style={{ color:"var(--accent)", border:"1px solid var(--accent)" }}>
                    Clear Filters
                  </button>
                )}
              </div>

              {filtered.length === 0 ? (
                <div className="glass p-8 text-center text-sm" style={{ color:"var(--text-dim)" }}>No jurisdictions configured yet.</div>
              ) : filtered.map(j => {
                const d: any = j.tax_rates_json || {};
                const slabs = d.slabs || d.slabs_single || [];
                const isIN = j.code === "IN";
                const show = (s: JurSection) => jurSection === "all" || jurSection === s;
                return (
                <div key={j.id} className="glass p-0 overflow-hidden">
                  {/* Header */}
                  <div className="flex items-center justify-between p-5" style={{ borderBottom:"1px solid var(--border)" }}>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{isIN ? "🇮🇳" : "🇺🇸"}</span>
                      <div>
                        <h3 className="text-lg font-bold" style={{ color:"var(--text)" }}>{j.name} <span className="font-mono text-xs px-2 py-0.5 rounded" style={{ background:"var(--accent)", color:"#000" }}>{j.code}</span></h3>
                        <p className="text-xs mt-0.5" style={{ color:"var(--text-dim)" }}>
                          {isIN ? `FY ${d.financial_year} • AY ${d.assessment_year} • ${(d.regime as string)?.replace("_"," ")}` : `Tax Year ${d.tax_year}`}
                          {" • "}{d.currency} • Filing: {j.filing_frequency}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-0">
                    {/* ── Income Tax Slabs ── */}
                    {show("slabs") && <div className="p-5" style={{ borderRight:"1px solid var(--border)", borderBottom:"1px solid var(--border)" }}>
                      <h4 className="text-xs font-bold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color:"var(--accent)" }}>
                        <Receipt size={14}/>Income Tax Slabs {!isIN && "(Single)"}
                      </h4>
                      <table className="w-full text-xs">
                        <thead><tr style={{ borderBottom:"1px solid var(--border)" }}>
                          <th className="text-left py-1.5 font-medium" style={{ color:"var(--text-dim)" }}>Range</th>
                          <th className="text-right py-1.5 font-medium" style={{ color:"var(--text-dim)" }}>Rate</th>
                        </tr></thead>
                        <tbody>{slabs.map((s: any, i: number) => (
                          <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                            <td className="py-1.5" style={{ color:"var(--text)" }}>
                              {isIN ? `₹${(s.min/100000).toFixed(1)}L` : `$${(s.min/1000).toFixed(1)}K`}
                              {" → "}
                              {s.max ? (isIN ? `₹${(s.max/100000).toFixed(1)}L` : `$${(s.max/1000).toFixed(1)}K`) : "∞"}
                            </td>
                            <td className="py-1.5 text-right font-mono font-bold" style={{ color: s.rate === 0 ? "var(--success)" : "var(--text)" }}>
                              {(s.rate * 100).toFixed(0)}%
                            </td>
                          </tr>
                        ))}</tbody>
                      </table>
                      {d.standard_deduction && (
                        <p className="text-xs mt-2 px-2 py-1 rounded" style={{ background:"var(--surface)", color:"var(--text-muted)" }}>
                          Std. Deduction: {typeof d.standard_deduction === "object"
                            ? Object.entries(d.standard_deduction).map(([k,v]) => `${k.replace(/_/g," ")}: $${Number(v).toLocaleString()}`).join(" • ")
                            : `₹${Number(d.standard_deduction).toLocaleString()}`}
                        </p>
                      )}
                    </div>}

                    {/* ── Surcharge / AMT / SE Tax ── */}
                    {show("slabs") && <div className="p-5" style={{ borderBottom:"1px solid var(--border)" }}>
                      {isIN && d.surcharge ? (
                        <>
                          <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>Surcharge & Cess</h4>
                          <table className="w-full text-xs">
                            <tbody>{d.surcharge.map((s: any, i: number) => (
                              <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                                <td className="py-1.5" style={{ color:"var(--text)" }}>{s.label}</td>
                                <td className="py-1.5 text-right font-mono" style={{ color:"var(--text-muted)" }}>
                                  {s.max ? `₹${(s.min/100000).toFixed(0)}L–₹${(s.max/100000).toFixed(0)}L` : `₹${(s.min/100000).toFixed(0)}L+`}
                                </td>
                              </tr>
                            ))}</tbody>
                          </table>
                          {d.cess && <p className="text-xs mt-2 px-2 py-1 rounded" style={{ background:"rgba(234,179,8,0.1)", color:"#eab308" }}>⚠ {d.cess.label}</p>}
                          {d.rebate_87a && <p className="text-xs mt-1 px-2 py-1 rounded" style={{ background:"rgba(34,197,94,0.1)", color:"#22c55e" }}>✓ {d.rebate_87a.note}</p>}
                        </>
                      ) : !isIN && d.self_employment_tax ? (
                        <>
                          <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>Self-Employment & FICA</h4>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between"><span style={{ color:"var(--text-dim)" }}>SS Rate</span><span className="font-mono" style={{ color:"var(--text)" }}>{(d.self_employment_tax.social_security_rate*100).toFixed(1)}%</span></div>
                            <div className="flex justify-between"><span style={{ color:"var(--text-dim)" }}>SS Wage Base</span><span className="font-mono" style={{ color:"var(--text)" }}>${d.self_employment_tax.social_security_wage_base?.toLocaleString()}</span></div>
                            <div className="flex justify-between"><span style={{ color:"var(--text-dim)" }}>Medicare</span><span className="font-mono" style={{ color:"var(--text)" }}>{(d.self_employment_tax.medicare_rate*100).toFixed(1)}%</span></div>
                            <div className="flex justify-between"><span style={{ color:"var(--text-dim)" }}>Addl. Medicare</span><span className="font-mono" style={{ color:"var(--text)" }}>{(d.self_employment_tax.additional_medicare_rate*100).toFixed(1)}% ({'>'}{`$${(d.self_employment_tax.additional_medicare_threshold_single/1000)}K`})</span></div>
                          </div>
                          {d.capital_gains && (
                            <>
                              <h4 className="text-xs font-bold uppercase tracking-wider mt-4 mb-2" style={{ color:"var(--accent)" }}>Capital Gains (Single)</h4>
                              <div className="space-y-1 text-xs">
                                {d.capital_gains.long_term_rates?.map((r: any, i: number) => (
                                  <div key={i} className="flex justify-between">
                                    <span style={{ color:"var(--text-dim)" }}>${(r.min/1000).toFixed(0)}K–{r.max ? `$${(r.max/1000).toFixed(0)}K` : "∞"}</span>
                                    <span className="font-mono" style={{ color: r.rate===0?"var(--success)":"var(--text)" }}>{(r.rate*100).toFixed(0)}%</span>
                                  </div>
                                ))}
                                {d.capital_gains.niit && <p className="text-xs mt-1 px-2 py-1 rounded" style={{ background:"rgba(234,179,8,0.1)", color:"#eab308" }}>⚠ NIIT: {(d.capital_gains.niit.rate*100).toFixed(1)}% on income {'>'}{`$${(d.capital_gains.niit.threshold_single/1000)}K`}</p>}
                              </div>
                            </>
                          )}
                        </>
                      ) : null}
                    </div>}

                    {/* ── Key Deductions ── */}
                    {show("deductions") && <div className="p-5" style={{ borderRight:"1px solid var(--border)", borderBottom:"1px solid var(--border)" }}>
                      <h4 className="text-xs font-bold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color:"var(--accent)" }}>
                        <TrendingDown size={14}/>Key Deductions
                      </h4>
                      {d.key_deductions && (
                        <div className="space-y-2 text-xs">
                          {Object.entries(d.key_deductions).filter(([k]) => k !== "note").map(([key, val]: [string, any]) => (
                            <div key={key} className="p-2 rounded" style={{ background:"var(--surface)" }}>
                              <div className="flex justify-between items-center">
                                <span className="font-bold" style={{ color:"var(--text)" }}>{key.replace(/_/g," ")}</span>
                                {val.limit != null && <span className="font-mono text-xs" style={{ color:"var(--accent)" }}>
                                  {isIN ? `₹${(val.limit/1000).toFixed(0)}K` : `$${Number(val.limit).toLocaleString()}`}
                                </span>}
                                {val.limit_pct && <span className="font-mono text-xs" style={{ color:"var(--accent)" }}>{(val.limit_pct*100)}% AGI</span>}
                              </div>
                              {val.items && <p className="mt-1" style={{ color:"var(--text-dim)" }}>{val.items.join(", ")}</p>}
                              {val.note && <p className="mt-1 italic" style={{ color:"var(--text-dim)" }}>{val.note}</p>}
                            </div>
                          ))}
                          {d.key_deductions.note && <p className="text-xs px-2 py-1 rounded italic" style={{ background:"rgba(234,179,8,0.1)", color:"#eab308" }}>ℹ {d.key_deductions.note}</p>}
                        </div>
                      )}
                    </div>}

                    {/* ── Filing & Deadlines ── */}
                    {show("deadlines") && <div className="p-5" style={{ borderBottom:"1px solid var(--border)" }}>
                      <h4 className="text-xs font-bold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color:"var(--accent)" }}>
                        <Clock size={14}/>Filing Deadlines & Schedule
                      </h4>
                      {d.filing_deadlines && (
                        <div className="space-y-1 text-xs mb-3">
                          {Object.entries(d.filing_deadlines).map(([k, v]) => (
                            <div key={k} className="flex justify-between">
                              <span style={{ color:"var(--text-dim)" }}>{k.replace(/_/g," ")}</span>
                              <span className="font-mono font-bold" style={{ color:"var(--text)" }}>{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {(d.advance_tax_schedule || d.estimated_tax_schedule) && (
                        <>
                          <h5 className="text-xs font-bold uppercase tracking-wider mt-3 mb-2" style={{ color:"var(--text-muted)" }}>
                            {isIN ? "Advance Tax" : "Estimated Tax"} Schedule
                          </h5>
                          <div className="space-y-1 text-xs">
                            {(d.advance_tax_schedule || d.estimated_tax_schedule)?.map((s: any, i: number) => (
                              <div key={i} className="flex justify-between items-center p-1.5 rounded" style={{ background: i%2===0 ? "var(--surface)" : "transparent" }}>
                                <span className="font-mono font-bold" style={{ color:"var(--accent)" }}>{s.due_date}</span>
                                <span style={{ color:"var(--text-dim)" }}>{s.label || s.payment}</span>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>}

                    {/* ── Penalties ── */}
                    {show("penalties") && d.penalties && (
                      <div className="p-5" style={{ borderRight:"1px solid var(--border)" }}>
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"#ef4444" }}>⚠ Penalties & Interest</h4>
                        <div className="space-y-1 text-xs">
                          {Object.entries(d.penalties).map(([k, v]) => (
                            <div key={k} className="p-2 rounded" style={{ background:"rgba(239,68,68,0.05)" }}>
                              <span className="font-bold" style={{ color:"var(--text)" }}>{k.replace(/_/g," ")}: </span>
                              <span style={{ color:"var(--text-dim)" }}>{typeof v === "object" && v ? Object.entries(v as any).map(([sk,sv])=>`${sk.replace(/_/g," ")}: ${typeof sv==="number" ? (isIN ? `₹${sv.toLocaleString()}` : sv) : sv}`).join(" • ") : String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ── GST Rates (India) / FICA (US) ── */}
                    {show("gst_fica") && isIN && d.gst_rates && (
                      <div className="p-5">
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>GST Rates</h4>
                        <div className="space-y-1 text-xs">
                          {d.gst_rates.map((g: any, i: number) => (
                            <div key={i} className="flex gap-3 p-1.5 rounded" style={{ background: i%2===0 ? "var(--surface)" : "transparent" }}>
                              <span className="font-mono font-bold w-10 shrink-0" style={{ color: g.rate===0?"var(--success)":"var(--text)" }}>{(g.rate*100).toFixed(0)}%</span>
                              <span style={{ color:"var(--text-dim)" }}>{g.items.join(", ")}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {show("gst_fica") && !isIN && d.fica && (
                      <div className="p-5">
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>FICA Breakdown</h4>
                        <div className="space-y-1 text-xs">
                          {Object.entries(d.fica).map(([k, v]) => (
                            <div key={k} className="flex justify-between">
                              <span style={{ color:"var(--text-dim)" }}>{k.replace(/_/g," ")}</span>
                              <span className="font-mono" style={{ color:"var(--text)" }}>{typeof v === "number" ? (v < 1 ? `${(v*100).toFixed(2)}%` : `$${v.toLocaleString()}`) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ── TDS Rates (India only) ── */}
                    {show("tds") && isIN && d.tds_rates && (
                      <div className="p-5 md:col-span-2" style={{ borderTop:"1px solid var(--border)" }}>
                        <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>TDS Rates</h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                          {Object.entries(d.tds_rates).map(([k, v]) => (
                            <div key={k} className="p-2 rounded" style={{ background:"var(--surface)" }}>
                              <span className="font-bold block" style={{ color:"var(--text)" }}>{k.replace(/_/g," ")}</span>
                              <span style={{ color:"var(--text-dim)" }}>
                                {typeof v === "string" ? v : typeof v === "object" ? Object.entries(v as any).map(([sk,sv])=>`${sk.replace(/_/g," ")}: ${typeof sv==="number" ? (sv<1?`${(sv*100)}%`:`₹${sv.toLocaleString()}`) : sv}`).join(" • ") : String(v)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* ── MFJ Slabs (US only) ── */}
                    {show("alt_filing") && !isIN && d.slabs_married_jointly && (
                      <div className="p-5 md:col-span-2" style={{ borderTop:"1px solid var(--border)" }}>
                        <div className="grid md:grid-cols-2 gap-6">
                          <div>
                            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>Married Filing Jointly</h4>
                            <table className="w-full text-xs">
                              <tbody>{d.slabs_married_jointly.map((s: any, i: number) => (
                                <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                                  <td className="py-1" style={{ color:"var(--text)" }}>${(s.min/1000).toFixed(1)}K → {s.max ? `$${(s.max/1000).toFixed(1)}K` : "∞"}</td>
                                  <td className="py-1 text-right font-mono font-bold" style={{ color: s.rate===0?"var(--success)":"var(--text)" }}>{(s.rate*100).toFixed(0)}%</td>
                                </tr>
                              ))}</tbody>
                            </table>
                          </div>
                          <div>
                            <h4 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color:"var(--accent)" }}>Head of Household</h4>
                            <table className="w-full text-xs">
                              <tbody>{d.slabs_head_of_household?.map((s: any, i: number) => (
                                <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                                  <td className="py-1" style={{ color:"var(--text)" }}>${(s.min/1000).toFixed(1)}K → {s.max ? `$${(s.max/1000).toFixed(1)}K` : "∞"}</td>
                                  <td className="py-1 text-right font-mono font-bold" style={{ color: s.rate===0?"var(--success)":"var(--text)" }}>{(s.rate*100).toFixed(0)}%</td>
                                </tr>
                              ))}</tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                );
              })}
            </div>
            );
          })()}

          {/* ─── Calculator Tab ─── */}
          {tab === "calculator" && (
            <div className="space-y-4 animate-fade-up">
              {/* Mode selector */}
              <div className="flex gap-2 flex-wrap">
                {calcModes.map(m => (
                  <button key={m.key} onClick={() => { setCalcMode(m.key); setCalcResult(null); setCalcError(null); }}
                    className="px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all"
                    style={{
                      background: calcMode===m.key ? "var(--accent)" : "var(--surface)",
                      color: calcMode===m.key ? "#000" : "var(--text-muted)",
                      border: `1px solid ${calcMode===m.key ? "var(--accent)" : "var(--border)"}`,
                    }}>
                    {m.icon} {m.label}
                  </button>
                ))}
              </div>

              {/* Calculator form */}
              <div className="glass p-6">
                <form onSubmit={handleCalc} className="space-y-4">
                  {calcMode === "india" && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <input name="gross_income" type="number" placeholder="Gross income (₹)" required style={inputStyle}/>
                      <select name="regime" style={inputStyle}>
                        <option value="new-2026-27">New Regime 2026-27</option>
                        <option value="new-2025-26">New Regime 2025-26</option>
                        <option value="new-2024-25">New Regime 2024-25</option>
                        <option value="old">Old Regime</option>
                      </select>
                      <label className="flex items-center gap-2 text-sm" style={{ color:"var(--text-muted)" }}>
                        <input type="checkbox" name="std_ded" defaultChecked/> Standard Deduction
                      </label>
                    </div>
                  )}
                  {calcMode === "india-hra" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <input name="basic_salary" type="number" placeholder="Basic + DA (₹/yr)" required style={inputStyle}/>
                      <input name="hra_received" type="number" placeholder="HRA received (₹/yr)" required style={inputStyle}/>
                      <input name="rent_paid" type="number" placeholder="Rent paid (₹/yr)" required style={inputStyle}/>
                      <label className="flex items-center gap-2 text-sm" style={{ color:"var(--text-muted)" }}>
                        <input type="checkbox" name="is_metro" defaultChecked/> Metro city
                      </label>
                    </div>
                  )}
                  {calcMode === "india-gratuity" && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <input name="monthly_basic" type="number" placeholder="Monthly basic (₹)" required style={inputStyle}/>
                      <input name="years" type="number" placeholder="Years of service" required style={inputStyle}/>
                      <label className="flex items-center gap-2 text-sm" style={{ color:"var(--text-muted)" }}>
                        <input type="checkbox" name="covered" defaultChecked/> Covered by Act
                      </label>
                    </div>
                  )}
                  {calcMode === "us" && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <input name="income" type="number" placeholder="Net SE income ($)" required style={inputStyle}/>
                      <select name="filing_status" style={inputStyle}>
                        <option value="single">Single</option>
                      </select>
                      <label className="flex items-center gap-2 text-sm" style={{ color:"var(--text-muted)" }}>
                        <input type="checkbox" name="qbi" defaultChecked/> QBI Deduction
                      </label>
                    </div>
                  )}
                  {calcMode === "global" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <input name="country_code" placeholder="Country code (e.g. DE, GB)" maxLength={2} required style={inputStyle}/>
                      <input name="income" type="number" placeholder="Annual income" required style={inputStyle}/>
                    </div>
                  )}
                  {calcMode === "compare" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <input name="gross_income" type="number" placeholder="Gross income (₹)" required style={inputStyle}/>
                      <p className="text-xs self-center" style={{ color:"var(--text-dim)" }}>Compares old vs new regime and recommends the best option.</p>
                    </div>
                  )}
                  {calcMode === "hourly" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <input name="country_code" placeholder="Country (e.g. US)" maxLength={2} required style={inputStyle}/>
                      <input name="annual_income" type="number" placeholder="Annual income" required style={inputStyle}/>
                      <input name="weekly_hours" type="number" placeholder="Weekly hours" defaultValue={40} style={inputStyle}/>
                      <input name="paid_days_off" type="number" placeholder="Paid days off" defaultValue={20} style={inputStyle}/>
                    </div>
                  )}
                  <button type="submit" className="btn-primary flex items-center gap-2" disabled={calcLoading}>
                    <Calculator size={16}/> {calcLoading ? "Calculating…" : "Calculate"}
                  </button>
                </form>
              </div>

              {/* Error */}
              {calcError && (
                <div className="glass p-4" style={{ borderLeft:"3px solid var(--danger)" }}>
                  <p className="text-sm" style={{ color:"var(--danger)" }}>{calcError}</p>
                </div>
              )}

              {/* Result */}
              {calcResult && (() => {
                const cr = calcResult as any;
                const d = cr.data || cr;
                const inp = d.input || {};
                const der = d.derived || {};
                const res = d.result || d;
                const isINR = (cr.country === "IN" || calcMode === "india" || calcMode === "india-hra" || calcMode === "india-gratuity" || calcMode === "compare");
                const sym = isINR ? "₹" : "$";
                const fmt = (v: number) => v != null ? `${sym}${v.toLocaleString("en-IN")}` : "—";
                const slabs: any[] = res.slabwiseBreakdown || res.slab_breakdown || [];

                return (
                <div className="glass p-6 animate-fade-up space-y-5">
                  {/* ── Hero: Total Tax ── */}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-wider font-medium" style={{ color:"var(--text-dim)" }}>Total Tax Payable</p>
                      <p className="text-3xl font-black tracking-tight mt-1" style={{ color: res.totalTax === 0 ? "var(--success)" : "var(--accent)" }}>
                        {fmt(res.totalTax ?? res.total_tax ?? 0)}
                      </p>
                      {res.totalTax === 0 && <p className="text-xs mt-1 font-medium" style={{ color:"var(--success)" }}>✓ No tax liability under this regime</p>}
                    </div>
                    {cr.source && (
                      <span className="text-[10px] px-2 py-1 rounded-full" style={{ background:"var(--surface)", color:"var(--text-dim)", border:"1px solid var(--border)" }}>
                        Source: {cr.source}
                      </span>
                    )}
                  </div>

                  {/* ── Input Summary ── */}
                  {Object.keys(inp).length > 0 && (
                    <div className="p-4 rounded-lg" style={{ background:"var(--surface)", border:"1px solid var(--border)" }}>
                      <p className="text-[10px] uppercase tracking-wider font-bold mb-2" style={{ color:"var(--text-dim)" }}>Input</p>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1 text-xs">
                        {Object.entries(inp).map(([k, v]) => (
                          <div key={k} className="flex justify-between gap-2">
                            <span style={{ color:"var(--text-dim)" }}>{k.replace(/([A-Z])/g, " $1").replace(/_/g, " ")}</span>
                            <span className="font-mono font-bold" style={{ color:"var(--text)" }}>
                              {typeof v === "number" ? (v >= 1000 ? fmt(v) : String(v)) : typeof v === "boolean" ? (v ? "Yes" : "No") : String(v)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ── Derived Values ── */}
                  {Object.keys(der).length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {Object.entries(der).map(([k, v]) => (
                        <div key={k} className="p-3 rounded-lg text-center" style={{ background:"var(--surface)", border:"1px solid var(--border)" }}>
                          <p className="text-[10px] uppercase tracking-wider" style={{ color:"var(--text-dim)" }}>{k.replace(/([A-Z])/g, " $1").replace(/_/g, " ")}</p>
                          <p className="text-lg font-bold mt-1" style={{ color:"var(--text)" }}>{typeof v === "number" ? fmt(v) : String(v)}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* ── Tax Breakdown Chips ── */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label:"Base Tax", val: res.baseTax ?? res.base_tax },
                      { label:"Surcharge", val: res.surcharge },
                      { label:"Surcharge Rate", val: res.surchargeRate ?? res.surcharge_rate, pct: true },
                      { label:"Cess", val: res.cess ?? res.health_cess },
                    ].filter(c => c.val != null).map(c => (
                      <div key={c.label} className="p-3 rounded-lg" style={{ background:"var(--bg)", border:"1px solid var(--border)" }}>
                        <p className="text-[10px] uppercase tracking-wider" style={{ color:"var(--text-dim)" }}>{c.label}</p>
                        <p className="text-sm font-bold font-mono mt-1" style={{ color: c.val === 0 ? "var(--success)" : "var(--text)" }}>
                          {c.pct ? `${((c.val as number) * 100).toFixed(1)}%` : fmt(c.val as number)}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* ── Slab-wise Breakdown ── */}
                  {slabs.length > 0 && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider font-bold mb-2" style={{ color:"var(--accent)" }}>Slab-wise Breakdown</p>
                      <table className="w-full text-xs">
                        <thead>
                          <tr style={{ borderBottom:"2px solid var(--border)" }}>
                            <th className="text-left py-2 font-medium" style={{ color:"var(--text-dim)" }}>Slab</th>
                            <th className="text-right py-2 font-medium" style={{ color:"var(--text-dim)" }}>Tax</th>
                          </tr>
                        </thead>
                        <tbody>
                          {slabs.map((s: any, i: number) => (
                            <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                              <td className="py-2" style={{ color:"var(--text)" }}>{s.slab || s.range || `Slab ${i + 1}`}</td>
                              <td className="py-2 text-right font-mono font-bold" style={{ color: s.tax === 0 ? "var(--success)" : "var(--accent)" }}>
                                {fmt(s.tax ?? s.amount ?? 0)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* ── Effective Rate (if total and income available) ── */}
                  {(res.totalTax ?? res.total_tax) != null && (inp.grossIncome || inp.gross_income || inp.income) && (
                    <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background:"rgba(168,162,158,0.08)", border:"1px solid var(--border)" }}>
                      <span className="text-xs" style={{ color:"var(--text-dim)" }}>Effective Tax Rate</span>
                      <span className="text-lg font-black font-mono" style={{ color:"var(--accent)" }}>
                        {(((res.totalTax ?? res.total_tax ?? 0) / (inp.grossIncome || inp.gross_income || inp.income)) * 100).toFixed(2)}%
                      </span>
                    </div>
                  )}
                </div>
                );
              })()}
            </div>
          )}
        </>
      )}
    </div>
  );
}
