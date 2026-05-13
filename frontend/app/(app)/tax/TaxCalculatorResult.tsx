import type { ReactNode } from "react";
import type {
  EffectiveHourlyRateResponse,
  ExternalTaxCalculationResponse,
  IndiaRegimeComparisonResponse,
} from "@/lib/types";

export type TaxCalcMode =
  | "india"
  | "india-hra"
  | "india-gratuity"
  | "us"
  | "global"
  | "compare"
  | "hourly";

type TaxCalcResult =
  | ExternalTaxCalculationResponse
  | IndiaRegimeComparisonResponse
  | EffectiveHourlyRateResponse;

type AnyRecord = Record<string, unknown>;

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as AnyRecord)
    : {};
}

function asRecordArray(value: unknown): AnyRecord[] {
  return Array.isArray(value) ? value.map((item) => asRecord(item)) : [];
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") {
    return value;
  }
  return null;
}

function humanize(key: string) {
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMoney(value: unknown, currency?: string | null) {
  const amount = asNumber(value);
  if (amount == null) {
    return "—";
  }

  if (!currency) {
    return amount.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }

  const locale = currency === "INR" ? "en-IN" : "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return amount.toLocaleString(locale, { maximumFractionDigits: 2 });
  }
}

function formatPercent(value: unknown, mode: "auto" | "decimal" | "whole" = "auto") {
  const numeric = asNumber(value);
  if (numeric == null) {
    return "—";
  }
  const pct = mode === "decimal" ? numeric * 100 : mode === "whole" ? numeric : numeric <= 1 ? numeric * 100 : numeric;
  return `${pct.toFixed(2)}%`;
}

function formatPlain(value: unknown) {
  const numeric = asNumber(value);
  if (numeric != null) {
    return numeric.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return value == null ? "—" : String(value);
}

function pickCurrency(mode: TaxCalcMode, result: TaxCalcResult) {
  if (mode === "india" || mode === "india-hra" || mode === "india-gratuity" || mode === "compare") {
    return "INR";
  }
  if ("country" in result && typeof result.country === "string") {
    const countryCode = result.country.toUpperCase();
    if (countryCode === "US") {
      return "USD";
    }
    if (countryCode === "IN") {
      return "INR";
    }
  }
  if ("data" in result) {
    const data = asRecord(result.data);
    if (typeof data.currency === "string" && data.currency.length === 3) {
      return data.currency.toUpperCase();
    }
  }
  return mode === "us" || mode === "hourly" ? "USD" : null;
}

function MetricCard({
  label,
  value,
  note,
  tone = "default",
}: {
  label: string;
  value: string;
  note?: string;
  tone?: "default" | "positive" | "warning";
}) {
  const toneColor =
    tone === "positive"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : "var(--text)";

  return (
    <div
      className="rounded-2xl p-4"
      style={{
        background: "linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01))",
        border: "1px solid var(--border)",
      }}
    >
      <p className="text-[10px] uppercase tracking-[0.24em]" style={{ color: "var(--text-dim)" }}>
        {label}
      </p>
      <p className="mt-2 text-xl font-black tracking-tight" style={{ color: toneColor }}>
        {value}
      </p>
      {note && (
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          {note}
        </p>
      )}
    </div>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section
      className="rounded-[26px] p-5"
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid var(--border)",
      }}
    >
      <div className="mb-4">
        <p className="text-[10px] uppercase tracking-[0.24em]" style={{ color: "var(--text-dim)" }}>
          {title}
        </p>
        {subtitle && (
          <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
            {subtitle}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

function DetailRows({
  rows,
  currency,
}: {
  rows: { label: string; value: unknown; kind?: "money" | "percent" | "whole-percent" | "plain" }[];
  currency?: string | null;
}) {
  return (
    <div className="grid gap-2">
      {rows.map((row) => (
        <div
          key={row.label}
          className="flex items-center justify-between gap-3 rounded-xl px-3 py-2"
          style={{ background: "var(--surface)" }}
        >
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>
            {row.label}
          </span>
          <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            {row.kind === "money"
              ? formatMoney(row.value, currency)
              : row.kind === "percent"
                ? formatPercent(row.value, "decimal")
                : row.kind === "whole-percent"
                  ? formatPercent(row.value, "whole")
                  : formatPlain(row.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

function SlabBreakdown({
  rows,
  currency,
}: {
  rows: AnyRecord[];
  currency?: string | null;
}) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-2xl" style={{ border: "1px solid var(--border)" }}>
      <table className="w-full text-sm">
        <thead style={{ background: "rgba(255,255,255,0.03)" }}>
          <tr>
            <th className="px-4 py-3 text-left font-medium" style={{ color: "var(--text-dim)" }}>
              Slab
            </th>
            <th className="px-4 py-3 text-right font-medium" style={{ color: "var(--text-dim)" }}>
              Tax
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.slab ?? row.range ?? index}`} style={{ borderTop: "1px solid var(--border)" }}>
              <td className="px-4 py-3" style={{ color: "var(--text)" }}>
                {String(row.slab ?? row.range ?? `Slab ${index + 1}`)}
              </td>
              <td className="px-4 py-3 text-right font-semibold" style={{ color: "var(--text)" }}>
                {formatMoney(row.tax ?? row.amount, currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderWrappedInputSummary(data: AnyRecord, currency?: string | null) {
  const input = asRecord(data.input);
  const entries = Object.entries(input);
  if (entries.length === 0) {
    return null;
  }

  return (
    <Section title="Input Snapshot">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {entries.map(([key, value]) => {
          const numeric = asNumber(value);
          const boolValue = asBoolean(value);
          const display =
            boolValue != null
              ? boolValue ? "Yes" : "No"
              : numeric != null && numeric >= 1000
                ? formatMoney(numeric, currency)
                : formatPlain(value);
          return <MetricCard key={key} label={humanize(key)} value={display} />;
        })}
      </div>
    </Section>
  );
}

function IndiaTaxResult({ result }: { result: ExternalTaxCalculationResponse }) {
  const data = asRecord(result.data);
  const derived = asRecord(data.derived);
  const output = asRecord(data.result);
  const slabs = asRecordArray(output.slabwiseBreakdown ?? output.slab_breakdown);
  const totalTax = asNumber(output.totalTax ?? output.total_tax) ?? 0;
  const grossIncome = asNumber(asRecord(data.input).grossIncome ?? asRecord(data.input).gross_income);
  const effectiveRate =
    asNumber(output.totalTax ?? output.total_tax) != null && grossIncome
      ? totalTax / grossIncome
      : asNumber(output.effectiveRate ?? output.effective_rate);

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(20,184,166,0.18), rgba(245,158,11,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              India Income Tax
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(totalTax, "INR")}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Total annual tax including surcharge and cess.
            </p>
          </div>
          <MetricCard
            label="Effective Rate"
            value={formatPercent(effectiveRate, "decimal")}
            note={totalTax === 0 ? "No tax liability for this input." : undefined}
            tone={totalTax === 0 ? "positive" : "default"}
          />
        </div>
      </div>

      {renderWrappedInputSummary(data, "INR")}

      <Section title="Tax Bridge" subtitle="Derived values coming from the calculator response.">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {Object.entries(derived).map(([key, value]) => (
            <MetricCard key={key} label={humanize(key)} value={formatMoney(value, "INR")} />
          ))}
        </div>
      </Section>

      <Section title="Breakdown">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Base Tax" value={formatMoney(output.baseTax ?? output.base_tax, "INR")} />
          <MetricCard label="Surcharge" value={formatMoney(output.surcharge, "INR")} />
          <MetricCard label="Surcharge Rate" value={formatPercent(output.surchargeRate ?? output.surcharge_rate, "whole")} />
          <MetricCard label="Cess" value={formatMoney(output.cess ?? output.health_cess, "INR")} />
        </div>
      </Section>

      <Section title="Slab-Wise Breakdown" subtitle="Each slab is shown exactly as returned by the calculator.">
        <SlabBreakdown rows={slabs} currency="INR" />
      </Section>
    </div>
  );
}

function IndiaHraResult({ result }: { result: ExternalTaxCalculationResponse }) {
  const data = asRecord(result.data);
  const output = asRecord(data.result);
  const bounds = asRecord(output.bounds);
  const exempt = asNumber(output.exempt ?? output.exemptAmount) ?? 0;
  const taxable = asNumber(output.taxable ?? output.taxableAmount) ?? 0;
  const bound1 = output.bound1 ?? bounds.actualHRA;
  const bound2 = output.bound2 ?? bounds.metroPercent ?? bounds.nonMetroPercent;
  const bound3 = output.bound3 ?? bounds.rentMinus10Percent;

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(59,130,246,0.18), rgba(20,184,166,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              HRA Exemption
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(exempt, "INR")}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Exempt HRA under Section 10(13A). Inputs on this screen are annual values.
            </p>
          </div>
          <MetricCard
            label="Taxable HRA"
            value={formatMoney(taxable, "INR")}
            tone={taxable > 0 ? "warning" : "positive"}
          />
        </div>
      </div>

      {renderWrappedInputSummary(data, "INR")}

      <Section title="Statutory Bounds" subtitle="Exemption is the lowest of these three amounts.">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCard label="Actual HRA Received" value={formatMoney(bound1, "INR")} />
          <MetricCard label="50% / 40% Of Salary" value={formatMoney(bound2, "INR")} />
          <MetricCard label="Rent Minus 10% Salary" value={formatMoney(bound3, "INR")} />
        </div>
      </Section>
    </div>
  );
}

function IndiaGratuityResult({ result }: { result: ExternalTaxCalculationResponse }) {
  const data = asRecord(result.data);
  const input = asRecord(data.input);
  const output = asRecord(data.result);
  const formulaAmount = asNumber(output.formulaAmount ?? output.gratuity) ?? 0;
  const taxFree = asNumber(output.taxFree ?? output.taxFreeAmount) ?? 0;
  const taxable = asNumber(output.taxable ?? output.taxableAmount) ?? 0;
  const eligible = asBoolean(output.eligible) ?? false;

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(234,179,8,0.18), rgba(249,115,22,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              Gratuity Estimate
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(formulaAmount, "INR")}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Based on last drawn monthly basic + DA and years counted by the calculator.
            </p>
          </div>
          <MetricCard
            label="Eligibility"
            value={eligible ? "Eligible" : "Not Eligible"}
            tone={eligible ? "positive" : "warning"}
          />
        </div>
      </div>

      {renderWrappedInputSummary(data, "INR")}

      <Section title="Payout Structure">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Years Counted" value={formatPlain(output.yearsCounted ?? output.years ?? input.years)} />
          <MetricCard label="Formula Amount" value={formatMoney(formulaAmount, "INR")} />
          <MetricCard label="Tax-Free Portion" value={formatMoney(taxFree, "INR")} tone={taxFree > 0 ? "positive" : "default"} />
          <MetricCard label="Taxable Portion" value={formatMoney(taxable, "INR")} tone={taxable > 0 ? "warning" : "default"} />
        </div>
      </Section>
    </div>
  );
}

function CompareIndiaRegimesResult({ result }: { result: IndiaRegimeComparisonResponse }) {
  const oldData = asRecord(result.old_regime);
  const newData = asRecord(result.new_regime);
  const oldDerived = asRecord(oldData.derived);
  const newDerived = asRecord(newData.derived);
  const oldOutput = asRecord(oldData.result);
  const newOutput = asRecord(newData.result);
  const oldTotal = asNumber(oldOutput.totalTax ?? oldData.totalTax) ?? 0;
  const newTotal = asNumber(newOutput.totalTax ?? newData.totalTax) ?? 0;
  const savings = Math.abs(asNumber(result.savings) ?? oldTotal - newTotal);
  const winnerIsNew = result.recommendation === "new_regime";
  const oldSlabs = asRecordArray(oldOutput.slabwiseBreakdown ?? oldData.slabwiseBreakdown);
  const newSlabs = asRecordArray(newOutput.slabwiseBreakdown ?? newData.slabwiseBreakdown);

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: winnerIsNew
            ? "linear-gradient(135deg, rgba(16,185,129,0.18), rgba(59,130,246,0.12))"
            : "linear-gradient(135deg, rgba(245,158,11,0.18), rgba(249,115,22,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              Regime Recommendation
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {winnerIsNew ? "New Regime" : "Old Regime"}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Compared on gross income of {formatMoney(result.gross_income, "INR")}.
            </p>
          </div>
          <MetricCard
            label="Annual Tax Difference"
            value={formatMoney(savings, "INR")}
            note={winnerIsNew ? "Lower liability under the new regime." : "Lower liability under the old regime."}
            tone={winnerIsNew ? "positive" : "warning"}
          />
        </div>
      </div>

      <Section title="Side-By-Side Totals">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCard label="Old Regime Tax" value={formatMoney(oldTotal, "INR")} />
          <MetricCard label="New Regime Tax" value={formatMoney(newTotal, "INR")} />
          <MetricCard
            label="Winner"
            value={winnerIsNew ? "New Regime" : "Old Regime"}
            tone={winnerIsNew ? "positive" : "warning"}
          />
        </div>
      </Section>

      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Old Regime" subtitle="Taxable income and major tax components.">
          <DetailRows
            currency="INR"
            rows={[
              { label: "Standard Deduction", value: oldDerived.standardDeduction ?? oldData.standardDeduction, kind: "money" },
              { label: "Taxable Income", value: oldDerived.taxableIncome ?? oldData.taxableIncome, kind: "money" },
              { label: "Base Tax", value: oldOutput.baseTax ?? oldData.baseTax, kind: "money" },
              { label: "Surcharge", value: oldOutput.surcharge ?? oldData.surcharge, kind: "money" },
              { label: "Surcharge Rate", value: oldOutput.surchargeRate ?? oldData.surchargeRate, kind: "whole-percent" },
              { label: "Cess", value: oldOutput.cess ?? oldData.cess, kind: "money" },
            ]}
          />
          <div className="mt-4">
            <SlabBreakdown rows={oldSlabs} currency="INR" />
          </div>
        </Section>

        <Section title="New Regime" subtitle="Assessment year 2026-27 comparison path.">
          <DetailRows
            currency="INR"
            rows={[
              { label: "Standard Deduction", value: newDerived.standardDeduction ?? newData.standardDeduction, kind: "money" },
              { label: "Taxable Income", value: newDerived.taxableIncome ?? newData.taxableIncome, kind: "money" },
              { label: "Base Tax", value: newOutput.baseTax ?? newData.baseTax, kind: "money" },
              { label: "Surcharge", value: newOutput.surcharge ?? newData.surcharge, kind: "money" },
              { label: "Surcharge Rate", value: newOutput.surchargeRate ?? newData.surchargeRate, kind: "whole-percent" },
              { label: "Cess", value: newOutput.cess ?? newData.cess, kind: "money" },
            ]}
          />
          <div className="mt-4">
            <SlabBreakdown rows={newSlabs} currency="INR" />
          </div>
        </Section>
      </div>
    </div>
  );
}

function USTaxResult({ result }: { result: ExternalTaxCalculationResponse }) {
  const data = asRecord(result.data);
  const details = asRecord(data.details);
  const monthly = asRecord(data.monthly);
  const yearly = asRecord(data.yearly);
  const rates = asRecord(data.rates);
  const currency = typeof data.currency === "string" ? data.currency.toUpperCase() : "USD";

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(99,102,241,0.18), rgba(14,165,233,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              Federal + Self-Employment Tax
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(yearly.net, currency)}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Estimated annual take-home before any state or local taxes.
            </p>
          </div>
          <MetricCard label="Effective Rate" value={formatPercent(rates.effectiveTaxRate, "decimal")} />
        </div>
      </div>

      {renderWrappedInputSummary(data, currency)}

      <Section title="Annual View">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Gross Income" value={formatMoney(yearly.gross, currency)} />
          <MetricCard label="Self-Employment Tax" value={formatMoney(yearly.selfEmploymentTax ?? details.selfEmploymentTax, currency)} />
          <MetricCard label="Federal Income Tax" value={formatMoney(yearly.federalIncomeTax ?? details.federalIncomeTax, currency)} />
          <MetricCard label="Net Income" value={formatMoney(yearly.net, currency)} tone="positive" />
        </div>
      </Section>

      <div className="grid gap-4 xl:grid-cols-2">
        <Section title="Self-Employment Stack">
          <DetailRows
            currency={currency}
            rows={[
              { label: "SE Base", value: details.seBase, kind: "money" },
              { label: "Social Security", value: details.socialSecurity, kind: "money" },
              { label: "Medicare", value: details.medicare, kind: "money" },
              { label: "Additional Medicare", value: details.additionalMedicare, kind: "money" },
              { label: "SE Tax Total", value: details.selfEmploymentTax, kind: "money" },
              { label: "SE Deduction", value: details.seDeduction, kind: "money" },
            ]}
          />
        </Section>

        <Section title="Income Tax Bridge">
          <DetailRows
            currency={currency}
            rows={[
              { label: "AGI", value: details.agi, kind: "money" },
              { label: "Standard Deduction", value: details.standardDeduction, kind: "money" },
              { label: "Taxable Income", value: details.taxableIncome, kind: "money" },
              { label: "QBI Deduction", value: details.qbiDeduction, kind: "money" },
              { label: "Taxable After QBI", value: details.taxableAfterQbi, kind: "money" },
              { label: "Federal Income Tax", value: details.federalIncomeTax, kind: "money" },
            ]}
          />
        </Section>
      </div>

      <Section title="Monthly Cash View">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Monthly Gross" value={formatMoney(monthly.gross, currency)} />
          <MetricCard label="Monthly SE Tax" value={formatMoney(monthly.selfEmploymentTax, currency)} />
          <MetricCard label="Monthly Federal Tax" value={formatMoney(monthly.federalIncomeTax, currency)} />
          <MetricCard label="Monthly Net" value={formatMoney(monthly.net, currency)} tone="positive" />
        </div>
      </Section>
    </div>
  );
}

function GlobalTaxResult({ result }: { result: ExternalTaxCalculationResponse }) {
  const data = asRecord(result.data);
  const details = asRecord(data.details);
  const monthly = asRecord(data.monthly);
  const yearly = asRecord(data.yearly);
  const rates = asRecord(data.rates);
  const currency = typeof data.currency === "string" ? data.currency.toUpperCase() : null;

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(16,185,129,0.18), rgba(6,182,212,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              Multi-Country Tax Output
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(yearly.net ?? yearly.gross, currency)}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Country model response from rel.tax with the parameters supplied in the request.
            </p>
          </div>
          <MetricCard label="Effective Rate" value={formatPercent(rates.effectiveTaxRate, "decimal")} />
        </div>
      </div>

      {renderWrappedInputSummary(data, currency)}

      <Section title="Annual View">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Gross Income" value={formatMoney(yearly.gross, currency)} />
          <MetricCard label="Total Deductions" value={formatMoney(yearly.totalDeductions ?? yearly.incomeTax ?? yearly.socialInsurance, currency)} />
          <MetricCard label="Net Income" value={formatMoney(yearly.net, currency)} tone="positive" />
          <MetricCard label="Tax Year" value={formatPlain(data.taxYear)} />
        </div>
      </Section>

      {Object.keys(details).length > 0 && (
        <Section title="Calculation Details">
          <DetailRows
            currency={currency}
            rows={Object.entries(details).map(([key, value]) => ({
              label: humanize(key),
              value,
              kind: typeof value === "number" && key.toLowerCase().includes("rate") ? "percent" : typeof value === "number" ? "money" : "plain",
            }))}
          />
        </Section>
      )}

      {Object.keys(monthly).length > 0 && (
        <Section title="Monthly View">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Object.entries(monthly).map(([key, value]) => (
              <MetricCard key={key} label={humanize(key)} value={typeof value === "number" ? formatMoney(value, currency) : formatPlain(value)} />
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function HourlyRateResult({ result }: { result: EffectiveHourlyRateResponse }) {
  const countryCode = result.country.toUpperCase();
  const currency = countryCode === "IN" ? "INR" : "USD";

  return (
    <div className="space-y-4">
      <div
        className="overflow-hidden rounded-[30px] p-6"
        style={{
          background: "linear-gradient(135deg, rgba(244,114,182,0.18), rgba(249,115,22,0.12))",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="grid gap-4 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em]" style={{ color: "var(--text-dim)" }}>
              Post-Tax Hourly Rate
            </p>
            <h3 className="mt-2 text-3xl font-black tracking-tight" style={{ color: "var(--text)" }}>
              {formatMoney(result.hourly_rate, currency)}
            </h3>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Based on annual net income, weekly hours, and paid days off.
            </p>
          </div>
          <MetricCard label="Daily Rate" value={formatMoney(result.daily_rate, currency)} />
        </div>
      </div>

      <Section title="Rate Summary">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Gross Income" value={formatMoney(result.gross_income, currency)} />
          <MetricCard label="Net Income" value={formatMoney(result.net_income, currency)} tone="positive" />
          <MetricCard label="Working Days" value={formatPlain(result.working_days)} />
          <MetricCard label="Effective Rate" value={formatPercent(result.effective_tax_rate, "decimal")} />
        </div>
      </Section>
    </div>
  );
}

export function TaxCalculatorResult({
  mode,
  result,
}: {
  mode: TaxCalcMode;
  result: TaxCalcResult;
}) {
  if (mode === "compare") {
    return <CompareIndiaRegimesResult result={result as IndiaRegimeComparisonResponse} />;
  }

  if (mode === "hourly") {
    return <HourlyRateResult result={result as EffectiveHourlyRateResponse} />;
  }

  const wrappedResult = result as ExternalTaxCalculationResponse;
  const currency = pickCurrency(mode, result);

  return (
    <div className="animate-fade-up space-y-4">
      <div className="flex items-center justify-between gap-3 rounded-2xl px-4 py-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div>
          <p className="text-[10px] uppercase tracking-[0.24em]" style={{ color: "var(--text-dim)" }}>
            Source
          </p>
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            {wrappedResult.source}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-[0.24em]" style={{ color: "var(--text-dim)" }}>
            Country
          </p>
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            {wrappedResult.country}{currency ? ` • ${currency}` : ""}
          </p>
        </div>
      </div>

      {mode === "india" && <IndiaTaxResult result={wrappedResult} />}
      {mode === "india-hra" && <IndiaHraResult result={wrappedResult} />}
      {mode === "india-gratuity" && <IndiaGratuityResult result={wrappedResult} />}
      {mode === "us" && <USTaxResult result={wrappedResult} />}
      {mode === "global" && <GlobalTaxResult result={wrappedResult} />}
    </div>
  );
}
