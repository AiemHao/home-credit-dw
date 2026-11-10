import clsx from "clsx";
import { Check, Code2, Copy, Download, Play, Table2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Card, ChartSkeleton, ErrorBox, Note, PageHeader, Segmented, Select } from "../components/ui";
import { apiUrl, useApi } from "../lib/api";
import { useFilters } from "../lib/filters";
import { byKind, label, num } from "../lib/format";
import { useDimLabel, useMeta } from "../lib/meta";
import { seqColor, useTheme } from "../lib/theme";

interface PivotResp {
  sql: string;
  params: string[];
  rows: string[];
  cols: string[];
  cells: { row_member: string; col_member: string; value: number | null; n_applications: number }[];
}
interface OlapItem { name: string; sql: string }
interface OlapResult { name: string; sql: string; columns: string[]; rows: Record<string, unknown>[] }

export default function OlapExplorer() {
  const [tab, setTab] = useState<"pivot" | "saved">("pivot");
  return (
    <div className="space-y-6">
      <PageHeader title="OLAP explorer"
        description="The query interface of the warehouse: build any two-dimensional pivot (GROUP BY CUBE with subtotals), or run the saved OLAP examples - roll-up, cube, drill-down, slice/dice + pivot, time roll-up, ranking.">
        <Segmented ariaLabel="Mode" value={tab} onChange={setTab}
          options={[{ value: "pivot", label: "Pivot builder" }, { value: "saved", label: "Saved queries" }]} />
      </PageHeader>
      {tab === "pivot" ? <PivotBuilder /> : <SavedQueries />}
    </div>
  );
}

function PivotBuilder() {
  const meta = useMeta();
  const dimLabel = useDimLabel();
  const { palette } = useTheme();
  const { filters } = useFilters();
  const [row, setRow] = useState("age_bucket");
  const [col, setCol] = useState("income_bracket");
  const [measure, setMeasure] = useState("default_rate");
  const [minN, setMinN] = useState(30);
  const [showSql, setShowSql] = useState(false);
  const m = meta.measures.find((x) => x.key === measure)!;
  const { data, error, loading } = useApi<PivotResp>(row !== col ? apiUrl("pivot", filters, { row, col, measure }) : null);

  const grid = useMemo(() => {
    const map = new Map((data?.cells ?? []).map((c) => [`${c.row_member}|${c.col_member}`, c]));
    const body = (data?.cells ?? []).filter((c) => c.row_member !== "ALL" && c.col_member !== "ALL" && c.value != null && c.n_applications >= minN);
    const vals = body.map((c) => c.value as number);
    return { map, lo: Math.min(...vals), hi: Math.max(...vals) };
  }, [data, minN]);

  const dims = meta.dimensions.map((d) => ({ value: d.key, label: d.label }));

  const csv = () => {
    if (!data) return;
    const lines = [[dimLabel(row), ...data.cols].join(",")];
    for (const r of data.rows) lines.push([r, ...data.cols.map((c) => grid.map.get(`${r}|${c}`)?.value ?? "")].map((v) => `"${v}"`).join(","));
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `pivot_${row}_${col}_${measure}.csv` });
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card title="Pivot builder" subtitle="Sidebar filters act as a slice/dice. The ALL row and column are the CUBE subtotals (roll-up)."
      actions={
        <>
          <button className={clsx("btn text-xs", showSql && "bg-raised text-ink")} onClick={() => setShowSql((s) => !s)}>
            <Code2 className="h-3.5 w-3.5" /> SQL
          </button>
          <button className="btn text-xs" onClick={csv} disabled={!data}><Download className="h-3.5 w-3.5" /> CSV</button>
        </>
      }>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Select label="Rows" value={row} onChange={setRow} options={dims} />
        <Select label="Columns" value={col} onChange={setCol} options={dims.filter((d) => d.value !== row)} />
        <Select label="Measure" value={measure} onChange={setMeasure} options={meta.measures.map((x) => ({ value: x.key, label: x.label }))} />
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-3">Hide cells under (applications)</span>
          <input type="number" min={0} step={10} className="input num" value={minN} onChange={(e) => setMinN(Number(e.target.value) || 0)} />
        </label>
      </div>

      {showSql && data && <SqlBlock sql={data.sql} params={data.params} />}
      {row === col && <div className="mt-4"><ErrorBox message="Pick two different dimensions." /></div>}
      {error && <div className="mt-4"><ErrorBox message={error} /></div>}

      <div className="mt-5">
        {loading && !data ? <ChartSkeleton height={260} /> : data && (
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="num w-full border-collapse text-[13px]">
              <thead>
                <tr className="bg-raised/60 text-xs text-ink-3">
                  <th className="sticky left-0 bg-raised px-3 py-2 text-left font-medium">{dimLabel(row)} ↓ / {dimLabel(col)} →</th>
                  {data.cols.map((c) => (
                    <th key={c} className={clsx("px-3 py-2 text-right font-medium", c === "ALL" && "border-l border-line text-ink")}>{label(c)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r} className={clsx(r === "ALL" && "border-t-2 border-line font-semibold")}>
                    <th className="sticky left-0 whitespace-nowrap bg-surface px-3 py-2 text-left font-medium text-ink">{label(r)}</th>
                    {data.cols.map((c) => {
                      const cell = grid.map.get(`${r}|${c}`);
                      const total = r === "ALL" || c === "ALL";
                      const hidden = !cell || cell.value == null || cell.n_applications < minN;
                      const t = !hidden && grid.hi > grid.lo ? ((cell!.value as number) - grid.lo) / (grid.hi - grid.lo) : 0;
                      const color = seqColor(palette, 0.05 + t * 0.75);
                      return (
                        <td key={c}
                          title={cell ? `${label(r)} × ${label(c)} · ${num(cell.n_applications)} applications` : ""}
                          className={clsx("px-3 py-2 text-right", c === "ALL" && "border-l border-line", total ? "bg-raised/50 text-ink" : "")}
                          style={!total && !hidden ? { background: color.fill, color: color.text } : undefined}>
                          {hidden ? <span className="text-ink-3">·</span> : byKind(m.kind, cell!.value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="mt-3"><Note>Cell shading uses one blue ramp (light = low, dark = high) over the body cells; subtotals are not shaded.</Note></div>
    </Card>
  );
}

function SqlBlock({ sql, params = [] }: { sql: string; params?: string[] }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative mt-4 overflow-hidden rounded-lg border border-line bg-raised/50">
      <button className="absolute right-2 top-2 rounded-md p-1.5 text-ink-3 hover:bg-surface hover:text-ink" aria-label="Copy SQL"
        onClick={() => navigator.clipboard?.writeText(sql).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1200); })}>
        {copied ? <Check className="h-3.5 w-3.5 text-good" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      <pre className="max-h-80 overflow-auto p-4 pr-10 font-mono text-[12px] leading-relaxed text-ink-2">{sql.trim()}</pre>
      {params.length > 0 && <p className="border-t border-line px-4 py-2 font-mono text-[11px] text-ink-3">params: {JSON.stringify(params)}</p>}
    </div>
  );
}

const TITLES: Record<string, [string, string]> = {
  "01": ["Roll-up", "Age bucket → income bracket → all (GROUP BY ROLLUP)"],
  "02": ["Cube", "Contract type × gender with every subtotal (GROUP BY CUBE)"],
  "03": ["Drill-down", "Inside age 25–34: employment type → occupation"],
  "04": ["Slice, dice & pivot", "Cash loans with bureau history; DPD buckets as columns (PIVOT)"],
  "05": ["Time roll-up", "Bureau credits by quarter → year → all, via dim_time"],
  "06": ["Ranking", "Top-3 riskiest occupations per age bucket (RANK window)"],
};

function SavedQueries() {
  const list = useApi<OlapItem[]>("/api/olap");
  const [name, setName] = useState<string | null>(null);
  const current = name ?? list.data?.[0]?.name ?? null;
  const result = useApi<OlapResult>(current ? `/api/olap/${encodeURIComponent(current)}` : null);

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <Card title="Queries" bodyClassName="px-2 pb-2">
        <ul className="space-y-0.5">
          {(list.data ?? []).map((q) => {
            const [title, sub] = TITLES[q.name.slice(0, 2)] ?? [q.name, ""];
            return (
              <li key={q.name}>
                <button onClick={() => setName(q.name)}
                  className={clsx("w-full rounded-lg px-3 py-2 text-left transition", current === q.name ? "bg-accent-soft" : "hover:bg-raised")}>
                  <span className={clsx("flex items-center gap-2 text-[13px] font-medium", current === q.name ? "text-accent-ink" : "text-ink")}>
                    <Play className="h-3 w-3" /> {title}
                  </span>
                  <span className="mt-0.5 block text-xs leading-snug text-ink-3">{sub}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </Card>
      <Card title={current ? (TITLES[current.slice(0, 2)]?.[0] ?? current) : "…"} subtitle={current ? <code>src/sql/olap/{current}</code> : undefined}
        actions={<Table2 className="h-4 w-4 text-ink-3" />}>
        {result.data ? (
          <>
            <SqlBlock sql={result.data.sql} />
            <div className="mt-4 max-h-[460px] overflow-auto rounded-lg border border-line">
              {result.data.rows.length === 0 ? (
                <p className="p-6 text-center text-sm text-ink-3">No rows (every group is below the query's minimum size).</p>
              ) : (
                <table className="num w-full text-[13px]">
                  <thead className="sticky top-0 bg-raised text-xs text-ink-3">
                    <tr>{result.data.columns.map((c) => <th key={c} className="px-3 py-2 text-left font-medium">{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.data.rows.map((r, i) => {
                      const isTotal = Object.values(r).some((v) => v === "ALL");
                      return (
                        <tr key={i} className={clsx("border-t border-line/60", isTotal && "bg-raised/50 font-semibold")}>
                          {result.data!.columns.map((c) => (
                            <td key={c} className="px-3 py-1.5 text-ink-2">
                              {typeof r[c] === "number" ? num(r[c] as number, Number.isInteger(r[c]) ? 0 : 2) : String(r[c] ?? "–")}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
            <div className="mt-3"><Note>Saved queries run on the whole warehouse and ignore the sidebar filters.</Note></div>
          </>
        ) : result.error ? <ErrorBox message={result.error} /> : <ChartSkeleton height={260} />}
      </Card>
    </div>
  );
}
