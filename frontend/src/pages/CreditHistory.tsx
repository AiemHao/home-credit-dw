import { useMemo, useState } from "react";
import { Heatmap, RateBars, StackedBars } from "../components/charts";
import { Card, ChartSkeleton, Empty, Note, PageHeader, Segmented, StatTile } from "../components/ui";
import { apiUrl, useApi } from "../lib/api";
import { useFilters } from "../lib/filters";
import { compact, num, pct } from "../lib/format";
import { useByDim, useKpis } from "../lib/hooks";
import { useMeta } from "../lib/meta";

interface Cross { x: string; y: string; n_labelled: number; default_rate: number | null }
interface BureauKpis { n_credits: number; n_customers: number; active_share: number; active_debt: number; overdue_share: number; median_duration_days: number | null }
interface TrendRow { period: string; credit_active: string; credits_opened: number }
interface TypeRow { credit_type: string; credit_active: string; n_credits: number }

/** Fixed status order = fixed colour slot per status (colour follows the entity, never its rank). */
const STATUS_ORDER = ["Closed", "Active", "Sold", "Bad debt"];

function pivotLong<T extends Record<string, string | number>>(rows: T[], xKey: keyof T, sKey: keyof T, vKey: keyof T) {
  const keys = STATUS_ORDER.filter((s) => rows.some((r) => r[sKey] === s));
  const extra = [...new Set(rows.map((r) => String(r[sKey])))].filter((s) => !keys.includes(s));
  const allKeys = [...keys, ...extra];
  const byX = new Map<string, Record<string, string | number>>();
  for (const r of rows) {
    const x = String(r[xKey]);
    if (!byX.has(x)) byX.set(x, { [xKey as string]: x });
    byX.get(x)![String(r[sKey])] = Number(r[vKey]);
  }
  return { data: [...byX.values()], keys: allKeys };
}

export default function CreditHistory() {
  const meta = useMeta();
  const { filters } = useFilters();
  const avg = useKpis().data?.default_rate;
  const dpd = useByDim("max_dpd_bucket");
  const bureau = useByDim("bureau_active_bucket");
  const prev = useByDim("prev_approval_bucket");
  const cross = useApi<Cross[]>(apiUrl("cross", filters, { x: "bureau_active_bucket", y: "max_dpd_bucket" }));
  const bk = useApi<BureauKpis>(apiUrl("bureau/kpis", filters));
  const [grain, setGrain] = useState<"year" | "quarter" | "month">("quarter");
  const trend = useApi<TrendRow[]>(apiUrl("bureau/trend", filters, { grain }));
  const types = useApi<TypeRow[]>(apiUrl("bureau/by-type", filters));

  const trendData = useMemo(() => trend.data && pivotLong(trend.data as unknown as Record<string, string | number>[], "period", "credit_active", "credits_opened"), [trend.data]);
  const typeData = useMemo(() => {
    if (!types.data) return undefined;
    const p = pivotLong(types.data as unknown as Record<string, string | number>[], "credit_type", "credit_active", "n_credits");
    const total = (r: Record<string, string | number>) => p.keys.reduce((s, k) => s + (Number(r[k]) || 0), 0);
    return { ...p, data: p.data.sort((a, b) => total(b) - total(a)) };
  }, [types.data]);

  const cell = useMemo(() => {
    const m = new Map((cross.data ?? []).map((c) => [`${c.y}|${c.x}`, { value: c.default_rate, n: c.n_labelled }]));
    return (r: string, c: string) => m.get(`${r}|${c}`);
  }, [cross.data]);

  return (
    <div className="space-y-6">
      <PageHeader title="Credit history"
        description="How an applicant's past behaviour - days past due, other credits in the Credit Bureau, previous Home Credit applications - relates to default." />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Worst days past due" subtitle="Max DPD across bureau, installments, POS and cards.">
          {dpd.data ? <RateBars data={dpd.data} avg={avg} height={260} /> : <ChartSkeleton height={260} />}
        </Card>
        <Card title="Active bureau credits" subtitle="Open credits at other lenders.">
          {bureau.data ? <RateBars data={bureau.data} avg={avg} height={260} /> : <ChartSkeleton height={260} />}
        </Card>
        <Card title="Previous approval rate" subtitle="Approved ÷ decided earlier Home Credit applications.">
          {prev.data ? <RateBars data={prev.data} avg={avg} height={260} /> : <ChartSkeleton height={260} />}
        </Card>
      </div>

      <Card title="Default rate: active bureau credits × worst days past due"
        subtitle="Both effects add up - many open credits and a late-payment history is the riskiest corner.">
        {cross.data ? (
          <Heatmap rows={meta.members.max_dpd_bucket} cols={meta.members.bureau_active_bucket} cell={cell}
            rowLabel="Max DPD" colLabel="Active bureau credits" />
        ) : <ChartSkeleton height={240} />}
      </Card>

      <section className="space-y-4">
        <div>
          <h2 className="text-[17px] font-semibold text-ink">Credits reported by the Credit Bureau</h2>
          <p className="mt-1 text-[13px] text-ink-3">From <code>fact_bureau_credit</code> (one row per bureau credit), restricted to the filtered applicants through the shared customer dimension (drill-across).</p>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatTile label="Bureau credits" loading={!bk.data} value={compact(bk.data?.n_credits)} />
          <StatTile label="Applicants with a record" loading={!bk.data} value={compact(bk.data?.n_customers)} />
          <StatTile label="Still active" loading={!bk.data} value={pct(bk.data?.active_share)} />
          <StatTile label="Outstanding active debt" loading={!bk.data} value={compact(bk.data?.active_debt)} />
          <StatTile label="Median credit length" loading={!bk.data}
            value={bk.data?.median_duration_days != null ? `${num(bk.data.median_duration_days)} d` : "–"} hint="closed credits" />
        </div>

        <Card title="Credits opened over time, by current status"
          subtitle="Open date = assumed snapshot date + DAYS_CREDIT (dim_time, role: open date)."
          actions={<Segmented ariaLabel="Time grain" value={grain} onChange={setGrain}
            options={[{ value: "year", label: "Year" }, { value: "quarter", label: "Quarter" }, { value: "month", label: "Month" }]} />}>
          {trendData ? (trendData.data.length ? <StackedBars data={trendData.data} xKey="period" keys={trendData.keys} height={320} />
            : <Empty />) : <ChartSkeleton height={320} />}
        </Card>

        <Card title="Bureau credits by type and status" subtitle="Top credit types; the rest folded into “Other”.">
          {typeData ? <StackedBars data={typeData.data} xKey="credit_type" keys={typeData.keys} layout="bars" height={260} />
            : <ChartSkeleton height={260} />}
          <div className="mt-2"><Note>Status colours are fixed per status across both charts, so a colour always means the same thing.</Note></div>
        </Card>
      </section>
    </div>
  );
}
