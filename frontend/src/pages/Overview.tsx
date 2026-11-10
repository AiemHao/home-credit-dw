import { ArrowRight, MousePointerClick, TrendingDown, TrendingUp, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { MIN_RELIABLE, RateBars, ScoreCurve } from "../components/charts";
import { Card, ChartSkeleton, ErrorBox, Note, PageHeader, StatTile } from "../components/ui";
import { apiUrl, useApi, type DimRow } from "../lib/api";
import { useFilters } from "../lib/filters";
import { compact, label, num, pct } from "../lib/format";
import { useByDim, useCrossFilter, useKpis } from "../lib/hooks";
import { useMeta } from "../lib/meta";

interface CurvePoint { score_mid: number; default_rate: number; n_labelled: number }

export default function Overview() {
  const { filters } = useFilters();
  const k = useKpis();
  const age = useByDim("age_bucket", {}, true);
  const emp = useByDim("income_type", {}, true);
  const curve = useApi<CurvePoint[]>(apiUrl("score-curve", filters));
  const ageX = useCrossFilter("age_bucket");
  const empX = useCrossFilter("income_type");
  const avg = k.data?.default_rate;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio at a glance"
        description={<>Who defaults on a Home Credit loan? Headline indicators from <code className="text-[13px]">fact_loan_application</code>; default rate is measured on the labelled (train) applications only.</>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatTile label="Default rate" accent loading={k.loading && !k.data} value={pct(k.data?.default_rate, 2)}
          hint={`${num(k.data?.n_labelled)} labelled loans`} />
        <StatTile label="Applications" loading={k.loading && !k.data} value={compact(k.data?.n_applications)}
          hint="train + test" />
        <StatTile label="Overdue share" loading={k.loading && !k.data} value={pct(k.data?.overdue_share)}
          hint="overdue now or > 30 DPD ever" />
        <StatTile label="Median debt-to-income" loading={k.loading && !k.data} value={k.data?.median_dti?.toFixed(3) ?? "–"}
          hint="annuity / income" />
        <StatTile label="Average credit" loading={k.loading && !k.data} value={compact(k.data?.avg_credit)}
          hint={`total ${compact(k.data?.total_credit)}`} />
      </div>
      {k.error && <ErrorBox message={k.error} />}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Default rate by age" subtitle="Younger applicants default far more often. Click a column to filter every page."
          actions={<MousePointerClick className="h-4 w-4 text-ink-3" aria-label="clickable" />}>
          {age.data ? <RateBars data={age.data} avg={avg} {...ageX} /> : age.error ? <ErrorBox message={age.error} /> : <ChartSkeleton />}
        </Card>
        <Card title="Default rate by employment type" subtitle={`Faded bars: fewer than ${MIN_RELIABLE} labelled loans, read with care.`}
          actions={<MousePointerClick className="h-4 w-4 text-ink-3" aria-label="clickable" />}>
          {emp.data ? <RateBars data={emp.data} avg={avg} layout="bars" {...empX} /> : emp.error ? <ErrorBox message={emp.error} /> : <ChartSkeleton />}
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Risk falls steeply with the external credit score"
          subtitle="Default rate per 0.05-wide bin of EXT_SOURCE mean (labelled loans).">
          {curve.data ? <ScoreCurve data={curve.data} avg={avg} /> : <ChartSkeleton />}
        </Card>
        <Insights age={age.data} emp={emp.data} curve={curve.data} />
      </div>

      <WarehouseCard />
    </div>
  );
}

function Insights({ age, emp, curve }: { age?: DimRow[]; emp?: DimRow[]; curve?: CurvePoint[] }) {
  const reliable = (rows?: DimRow[]) => (rows ?? []).filter((r) => r.default_rate != null && r.n_labelled >= MIN_RELIABLE);
  const ages = reliable(age);
  const emps = reliable(emp);
  const top = (rows: DimRow[], dir: 1 | -1) =>
    rows.length ? rows.reduce((a, b) => ((b.default_rate! - a.default_rate!) * dir > 0 ? b : a)) : undefined;
  const riskyAge = top(ages, 1);
  const safeAge = top(ages, -1);
  const safeEmp = top(emps, -1);
  const pts = (curve ?? []).filter((p) => p.n_labelled >= MIN_RELIABLE);
  const lowScore = pts[0];
  const highScore = pts[pts.length - 1];

  const items = [
    riskyAge && safeAge && riskyAge !== safeAge && {
      icon: TrendingUp,
      text: <>Age <b>{riskyAge.member}</b> defaults at <b>{pct(riskyAge.default_rate)}</b>, {(riskyAge.default_rate! / safeAge.default_rate!).toFixed(1)}× the <b>{safeAge.member}</b> group ({pct(safeAge.default_rate)}).</>,
    },
    safeEmp && {
      icon: Users,
      text: <>Safest employment type with enough history: <b>{label(safeEmp.member)}</b> at <b>{pct(safeEmp.default_rate)}</b>.</>,
    },
    lowScore && highScore && {
      icon: TrendingDown,
      text: <>External score near <b>{lowScore.score_mid.toFixed(2)}</b> → <b>{pct(lowScore.default_rate)}</b> default; near <b>{highScore.score_mid.toFixed(2)}</b> → only <b>{pct(highScore.default_rate)}</b>.</>,
    },
  ].filter(Boolean) as { icon: typeof Users; text: JSX.Element }[];

  return (
    <Card title="What the warehouse says" subtitle="Computed live for the current filters.">
      <ul className="space-y-3">
        {items.length === 0 && <li className="text-sm text-ink-3">Not enough labelled loans for the current filters.</li>}
        {items.map(({ icon: Icon, text }, i) => (
          <li key={i} className="flex gap-3 rounded-lg bg-raised/60 p-3 text-[13px] leading-relaxed text-ink-2">
            <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span>{text}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to="/drilldown" className="btn text-xs">Drill down <ArrowRight className="h-3.5 w-3.5" /></Link>
        <Link to="/simulator" className="btn text-xs">Score an applicant <ArrowRight className="h-3.5 w-3.5" /></Link>
      </div>
    </Card>
  );
}

function WarehouseCard() {
  const meta = useMeta();
  const tables = meta.warehouse.tables;
  return (
    <Card title="Inside the warehouse" subtitle={<>Star schema (fact constellation) in DuckDB, schema <code>dw</code>. Snapshot date {meta.warehouse.anchor_date} (assumed: the dataset only has relative days).</>}
      actions={<Link to="/architecture" className="btn text-xs">See the design <ArrowRight className="h-3.5 w-3.5" /></Link>}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {tables.map((t) => (
          <div key={t.table_name} className="rounded-lg border border-line px-3 py-2.5">
            <p className={t.table_name.startsWith("fact_") ? "text-[11px] font-semibold uppercase tracking-wider text-accent-ink" : "eyebrow"}>
              {t.table_name.startsWith("fact_") ? "fact" : "dimension"}
            </p>
            <p className="mt-0.5 truncate font-mono text-[12.5px] text-ink">{t.table_name}</p>
            <p className="num text-xs text-ink-3">{num(t.n_rows)} rows</p>
          </div>
        ))}
      </div>
      <div className="mt-3"><Note>Row counts come from DuckDB's catalog (estimated sizes, exact for a freshly loaded file).</Note></div>
    </Card>
  );
}
