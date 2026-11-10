import { ArrowDownUp } from "lucide-react";
import { useMemo, useState } from "react";
import { BoxSummary, RateBars } from "../components/charts";
import { Card, ChartSkeleton, ErrorBox, PageHeader, Select } from "../components/ui";
import { apiUrl, useApi, type DimRow } from "../lib/api";
import { useFilters } from "../lib/filters";
import { compact, label, num, pct } from "../lib/format";
import { useByDim, useCrossFilter, useKpis } from "../lib/hooks";
import { useDimLabel, useMeta } from "../lib/meta";

interface Box { outcome: string; n: number; p05: number; p25: number; p50: number; p75: number; p95: number }

export default function Portfolio() {
  const { filters } = useFilters();
  const avg = useKpis().data?.default_rate;
  const contract = useByDim("contract_type", {}, true);
  const edu = useByDim("education_type", {}, true);
  const family = useByDim("family_status");
  const housing = useByDim("housing_type");
  const dti = useApi<Box[]>(apiUrl("dti-by-outcome", filters));
  const contractX = useCrossFilter("contract_type");
  const eduX = useCrossFilter("education_type");

  return (
    <div className="space-y-6">
      <PageHeader title="Portfolio" description="Risk by product and customer segment, and how affordability differs between loans that were repaid and loans that defaulted." />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Contract type" subtitle="Cash vs revolving loans.">
          {contract.data ? <RateBars data={contract.data} avg={avg} height={260} {...contractX} /> : <ChartSkeleton height={260} />}
        </Card>
        <Card className="lg:col-span-2" title="Education" subtitle="Default rate falls with education level.">
          {edu.data ? <RateBars data={edu.data} avg={avg} layout="bars" height={240} {...eduX} /> : <ChartSkeleton height={240} />}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Family status">
          {family.data ? <RateBars data={family.data} avg={avg} layout="bars" height={240} /> : <ChartSkeleton height={240} />}
        </Card>
        <Card title="Housing">
          {housing.data ? <RateBars data={housing.data} avg={avg} layout="bars" height={240} /> : <ChartSkeleton height={240} />}
        </Card>
      </div>

      <Card title="Debt-to-income: repaid vs defaulted"
        subtitle="Annuity ÷ income. Box = middle 50% of loans, line = 5th–95th percentile, tick = median. Exact quantiles over every labelled loan.">
        {dti.data ? <BoxSummary data={dti.data} format={(v) => v.toFixed(2)} /> : dti.error ? <ErrorBox message={dti.error} /> : <ChartSkeleton height={140} />}
      </Card>

      <SegmentTable />
    </div>
  );
}

type SortKey = "member" | "n_applications" | "default_rate" | "overdue_share" | "avg_credit" | "median_dti";

function SegmentTable() {
  const meta = useMeta();
  const dimLabel = useDimLabel();
  const [dim, setDim] = useState("occupation_type");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "default_rate", dir: -1 });
  const { data, error } = useByDim(dim);

  const rows = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const x = a[sort.key] as number | string | null;
      const y = b[sort.key] as number | string | null;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
    });
  }, [data, sort]);

  const max = Math.max(0, ...(data ?? []).map((r: DimRow) => r.default_rate ?? 0));
  const head = (key: SortKey, text: string, right = true) => (
    <th className={right ? "text-right" : "text-left"}>
      <button className="inline-flex items-center gap-1 hover:text-ink"
        onClick={() => setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : -1 }))}>
        {text} <ArrowDownUp className={sort.key === key ? "h-3 w-3 text-accent" : "h-3 w-3 opacity-40"} />
      </button>
    </th>
  );

  return (
    <Card title="Segment table" subtitle="Every member of one dimension with its key measures. Click a header to sort."
      actions={
        <Select label="Group by" value={dim} className="w-52" onChange={setDim}
          options={meta.dimensions.map((d) => ({ value: d.key, label: d.label }))} />
      }>
      {error && <ErrorBox message={error} />}
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="text-xs font-medium text-ink-3 [&_th]:border-b [&_th]:border-line [&_th]:px-3 [&_th]:py-2">
            <tr>
              {head("member", dimLabel(dim), false)}
              {head("n_applications", "Applications")}
              {head("default_rate", "Default rate")}
              {head("overdue_share", "Overdue share")}
              {head("avg_credit", "Avg credit")}
              {head("median_dti", "Median DTI")}
            </tr>
          </thead>
          <tbody className="num [&_td]:border-b [&_td]:border-line/60 [&_td]:px-3 [&_td]:py-2">
            {rows.map((r) => (
              <tr key={r.member} className="hover:bg-raised/50">
                <td className="text-ink">{label(r.member)}</td>
                <td className="text-right text-ink-2">{num(r.n_applications)}</td>
                <td className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-raised sm:block">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${max ? ((r.default_rate ?? 0) / max) * 100 : 0}%` }} />
                    </div>
                    <span className="w-14 text-ink">{pct(r.default_rate, 2)}</span>
                  </div>
                </td>
                <td className="text-right text-ink-2">{pct(r.overdue_share)}</td>
                <td className="text-right text-ink-2">{compact(r.avg_credit)}</td>
                <td className="text-right text-ink-2">{r.median_dti?.toFixed(3) ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
