import clsx from "clsx";
import { AlertOctagon, CheckCircle2, CircleAlert, Info, Loader2 } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Card, ErrorBox, Note, PageHeader } from "../components/ui";
import { postJson, useApi } from "../lib/api";
import { compact, label, pct } from "../lib/format";

interface Options { model_available: boolean; income_type: string[]; contract_type: string[] }
interface Inputs {
  amt_income: number; amt_credit: number; amt_annuity: number; age_years: number; years_employed: number;
  ext_source_mean: number; max_dpd_days: number; cnt_bureau_active: number; has_current_overdue: boolean;
  income_type: string; contract_type: string;
}
interface Result {
  flag: "GREEN" | "YELLOW" | "RED"; reasons: string[]; p_default: number | null; model_available: boolean;
  model_error: string | null; ratios: { debt_to_income: number; credit_to_income: number };
  thresholds: { p_green_max: number; p_red_min: number };
}

const DEFAULTS: Inputs = {
  amt_income: 180_000, amt_credit: 600_000, amt_annuity: 27_000, age_years: 38, years_employed: 5,
  ext_source_mean: 0.5, max_dpd_days: 0, cnt_bureau_active: 1, has_current_overdue: false,
  income_type: "Working", contract_type: "Cash loans",
};

/** Status palette (reserved for decisions), always shown with an icon + a word - never colour alone. */
const FLAG = {
  GREEN: { word: "Approve", icon: CheckCircle2, cls: "border-good/40 bg-good/10 text-good" },
  YELLOW: { word: "Manual review", icon: CircleAlert, cls: "border-warn/50 bg-warn/15 text-[#9a6700] dark:text-warn" },
  RED: { word: "Reject", icon: AlertOctagon, cls: "border-bad/40 bg-bad/10 text-bad" },
};

export default function RiskSimulator() {
  const opts = useApi<Options>("/api/simulator/options");
  const [inp, setInp] = useState<Inputs>(DEFAULTS);
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      setBusy(true);
      postJson<Result>("simulator/score", inp)
        .then((r) => { setRes(r); setErr(null); })
        .catch((e: Error) => setErr(e.message))
        .finally(() => setBusy(false));
    }, 180);
    return () => clearTimeout(t);
  }, [inp]);

  const set = <K extends keyof Inputs>(k: K, v: Inputs[K]) => setInp((s) => ({ ...s, [k]: v }));

  return (
    <div className="space-y-6">
      <PageHeader title="Risk simulator"
        description="What-if scoring for one applicant: the decision support component combines the model's probability of default with underwriting rules into Approve / Manual review / Reject." />

      {opts.data && !opts.data.model_available && (
        <div className="flex items-start gap-2 rounded-xl border border-accent/25 bg-accent-soft p-3 text-[13px] text-ink-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
          <span>No trained model yet (<code>models/model.pkl</code>), so decisions use the business rules only. Train one with <code>python -m dss.train</code>.</span>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Card title="Applicant" subtitle="Change any input - the decision updates instantly.">
          <div className="grid gap-x-8 gap-y-5 md:grid-cols-2">
            <Group title="Loan & income">
              <Slider label="Annual income" value={inp.amt_income} min={25_000} max={1_000_000} step={5_000} fmt={compact} onChange={(v) => set("amt_income", v)} />
              <Slider label="Credit amount" value={inp.amt_credit} min={45_000} max={4_000_000} step={5_000} fmt={compact} onChange={(v) => set("amt_credit", v)} />
              <Slider label="Annuity (yearly repayment)" value={inp.amt_annuity} min={2_000} max={250_000} step={500} fmt={compact} onChange={(v) => set("amt_annuity", v)} />
              <Choice label="Contract type" value={inp.contract_type} options={opts.data?.contract_type ?? [inp.contract_type]} onChange={(v) => set("contract_type", v)} />
            </Group>
            <Group title="Profile & history">
              <Slider label="Age" value={inp.age_years} min={21} max={69} step={1} fmt={(v) => `${v} y`} onChange={(v) => set("age_years", v)} />
              <Slider label="Years employed" value={inp.years_employed} min={0} max={45} step={1} fmt={(v) => `${v} y`} onChange={(v) => set("years_employed", v)} />
              <Slider label="External score (mean EXT_SOURCE)" value={inp.ext_source_mean} min={0} max={1} step={0.01} fmt={(v) => v.toFixed(2)} onChange={(v) => set("ext_source_mean", v)} />
              <Slider label="Worst days past due (history)" value={inp.max_dpd_days} min={0} max={365} step={1} fmt={(v) => `${v} d`} onChange={(v) => set("max_dpd_days", v)} />
              <Slider label="Active bureau credits" value={inp.cnt_bureau_active} min={0} max={15} step={1} fmt={String} onChange={(v) => set("cnt_bureau_active", v)} />
              <Choice label="Employment type" value={inp.income_type} options={opts.data?.income_type ?? [inp.income_type]} onChange={(v) => set("income_type", v)} />
              <label className="flex cursor-pointer items-center gap-2.5 text-[13px] text-ink-2">
                <input type="checkbox" className="h-4 w-4 accent-[rgb(var(--accent))]" checked={inp.has_current_overdue}
                  onChange={(e) => set("has_current_overdue", e.target.checked)} />
                Currently overdue in the Credit Bureau
              </label>
            </Group>
          </div>
          <div className="mt-5 flex justify-end">
            <button className="btn text-xs" onClick={() => setInp(DEFAULTS)}>Reset</button>
          </div>
        </Card>

        <div className="space-y-4 xl:sticky xl:top-20 xl:self-start">
          <Card title="Decision" actions={busy ? <Loader2 className="h-4 w-4 animate-spin text-ink-3" /> : null}>
            {err && <ErrorBox message={err} />}
            {res && <Decision res={res} />}
          </Card>
          <Card title="How the decision is made">
            <ol className="space-y-2 text-[13px] leading-relaxed text-ink-2">
              <li><b className="text-ink">1. Model</b> - LightGBM gives p(default); under {pct(res?.thresholds.p_green_max ?? 0.08, 0)} approve, from {pct(res?.thresholds.p_red_min ?? 0.2, 0)} reject.</li>
              <li><b className="text-ink">2. Rules</b> - debt-to-income over 0.40 or a current overdue → review; any history over 90 days past due → reject.</li>
              <li><b className="text-ink">3. Combine</b> - the strictest outcome wins, and every reason is listed.</li>
            </ol>
            <div className="mt-3"><Note>Thresholds live in <code>src/dss/rules.py</code>.</Note></div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Decision({ res }: { res: Result }) {
  const f = FLAG[res.flag];
  const Icon = f.icon;
  return (
    <div className="space-y-4">
      <div className={clsx("flex items-center gap-3 rounded-xl border p-4", f.cls)}>
        <Icon className="h-8 w-8 shrink-0" />
        <div>
          <p className="text-xl font-semibold leading-tight">{f.word}</p>
          <p className="text-xs font-medium opacity-80">{res.flag}</p>
        </div>
      </div>
      <dl className="grid grid-cols-3 gap-2 text-center">
        {[
          ["p(default)", res.p_default != null ? pct(res.p_default) : "–"],
          ["Debt-to-income", res.ratios.debt_to_income.toFixed(2)],
          ["Credit ÷ income", res.ratios.credit_to_income.toFixed(1)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-raised/60 px-2 py-2">
            <dt className="text-[11px] text-ink-3">{k}</dt>
            <dd className="num text-[15px] font-semibold text-ink">{v}</dd>
          </div>
        ))}
      </dl>
      <div>
        <p className="eyebrow mb-1.5">Reasons</p>
        <ul className="space-y-1.5">
          {res.reasons.map((r) => (
            <li key={r} className="flex items-start gap-2 text-[13px] text-ink-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ink-3" /> {r}
            </li>
          ))}
        </ul>
      </div>
      {res.model_error && <ErrorBox message={`Model scoring failed: ${res.model_error}`} />}
    </div>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-4">
      <legend className="eyebrow mb-3">{title}</legend>
      {children}
    </fieldset>
  );
}

function Slider({ label: text, value, min, max, step, fmt, onChange }: {
  label: string; value: number; min: number; max: number; step: number; fmt: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-[13px]">
        <span className="text-ink-2">{text}</span>
        <span className="num font-semibold text-ink">{fmt(value)}</span>
      </span>
      <input type="range" className="mt-1.5 w-full accent-[rgb(var(--accent))]" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

function Choice({ label: text, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[13px] text-ink-2">{text}</span>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o} value={o}>{label(o)}</option>)}
      </select>
    </label>
  );
}
