import clsx from "clsx";
import { ChevronRight, Home, X } from "lucide-react";
import { useEffect, useState } from "react";
import { RateBars } from "../components/charts";
import { Card, ChartSkeleton, Note, PageHeader } from "../components/ui";
import { useKpis, useByDim } from "../lib/hooks";
import { label, num, pct } from "../lib/format";
import { useDimLabel } from "../lib/meta";

const CANDIDATES = ["age_bucket", "income_bracket", "income_type", "occupation_type", "education_type",
  "family_status", "gender", "housing_type", "contract_type"];
const DEFAULT_PATH = ["age_bucket", "income_bracket", "income_type", "occupation_type"];

/** OLAP drill-down / roll-up along a user-defined hierarchy; click a bar to go one level deeper. */
export default function Drilldown() {
  const dimLabel = useDimLabel();
  const [path, setPath] = useState<string[]>(DEFAULT_PATH);
  const [members, setMembers] = useState<string[]>([]);
  const avg = useKpis().data?.default_rate;

  useEffect(() => setMembers([]), [path]);

  const level = members.length;
  const dim = path[level];
  const drill = Object.fromEntries(members.map((m, i) => [path[i], [m]]));
  const { data } = useByDim(dim ?? path[0], drill);

  return (
    <div className="space-y-6">
      <PageHeader title="Drill-down"
        description="Walk a customer hierarchy one level at a time (OLAP drill-down); use the breadcrumb to roll back up. The hierarchy is yours to define." />

      <Card title="Hierarchy" subtitle="Order of the levels to drill through (2–5 levels).">
        <div className="flex flex-wrap items-center gap-2">
          {path.map((d, i) => (
            <span key={d} className="inline-flex items-center gap-1.5">
              {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-ink-3" />}
              <span className="inline-flex items-center gap-1 rounded-lg border border-line bg-raised/60 py-1 pl-2.5 pr-1 text-[13px] text-ink">
                <span className="num text-[11px] text-ink-3">{i + 1}</span> {dimLabel(d)}
                {path.length > 2 && (
                  <button aria-label={`Remove ${dimLabel(d)}`} className="rounded p-0.5 text-ink-3 hover:bg-surface hover:text-ink"
                    onClick={() => setPath(path.filter((x) => x !== d))}>
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            </span>
          ))}
          {path.length < 5 && (
            <select className="input w-auto py-1 text-[13px]" value=""
              onChange={(e) => e.target.value && setPath([...path, e.target.value])} aria-label="Add level">
              <option value="">+ Add level</option>
              {CANDIDATES.filter((c) => !path.includes(c)).map((c) => <option key={c} value={c}>{dimLabel(c)}</option>)}
            </select>
          )}
        </div>
      </Card>

      <Card
        title={dim ? `Level ${level + 1} of ${path.length}: ${dimLabel(dim)}` : "Lowest level reached"}
        subtitle={dim ? "Click a bar to drill into that member." : "Use the breadcrumb to roll up."}
      >
        <nav className="mb-4 flex flex-wrap items-center gap-1 text-[13px]" aria-label="Drill path">
          <button onClick={() => setMembers([])}
            className={clsx("inline-flex items-center gap-1 rounded-md px-2 py-1", level === 0 ? "bg-accent-soft text-accent-ink" : "text-ink-2 hover:bg-raised")}>
            <Home className="h-3.5 w-3.5" /> All
          </button>
          {members.map((m, i) => (
            <span key={i} className="inline-flex items-center gap-1">
              <ChevronRight className="h-3.5 w-3.5 text-ink-3" />
              <button onClick={() => setMembers(members.slice(0, i + 1))}
                className={clsx("rounded-md px-2 py-1", i === level - 1 ? "bg-accent-soft text-accent-ink" : "text-ink-2 hover:bg-raised")}>
                <span className="text-ink-3">{dimLabel(path[i])}:</span> {label(m)}
              </button>
            </span>
          ))}
        </nav>

        {dim ? (
          data ? (
            <div className="grid gap-6 xl:grid-cols-5">
              <div className="xl:col-span-3">
                <RateBars data={data} avg={avg} layout={data.length > 7 ? "bars" : "columns"} height={320}
                  onSelect={(m) => setMembers([...members, m])} />
              </div>
              <div className="xl:col-span-2">
                <table className="num w-full text-[13px]">
                  <thead className="text-xs text-ink-3 [&_th]:border-b [&_th]:border-line [&_th]:px-2 [&_th]:py-1.5">
                    <tr><th className="text-left">{dimLabel(dim)}</th><th className="text-right">Loans</th><th className="text-right">Default</th></tr>
                  </thead>
                  <tbody className="[&_td]:border-b [&_td]:border-line/60 [&_td]:px-2 [&_td]:py-1.5">
                    {data.map((r) => (
                      <tr key={r.member} className="cursor-pointer hover:bg-raised/50" onClick={() => setMembers([...members, r.member])}>
                        <td className="text-ink">{label(r.member)}</td>
                        <td className="text-right text-ink-2">{num(r.n_labelled)}</td>
                        <td className="text-right text-ink">{pct(r.default_rate, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : <ChartSkeleton height={320} />
        ) : (
          <div className="rounded-lg bg-raised/60 p-6 text-center text-sm text-ink-2">
            You are at the most detailed level of this hierarchy. Click a breadcrumb to roll up.
          </div>
        )}
        <div className="mt-4"><Note>Each level is one SQL GROUP BY over mart.v_application_wide with the drill path as a WHERE slice; sidebar filters apply on top.</Note></div>
      </Card>
    </div>
  );
}
