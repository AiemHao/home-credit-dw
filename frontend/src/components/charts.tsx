import { useMemo, type ReactNode } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from "recharts";
import type { DimRow } from "../lib/api";
import { compact, label, num, pct } from "../lib/format";
import { seqColor, useTheme } from "../lib/theme";
import { TooltipCard } from "./ui";

/** Groups below this many labelled loans are drawn faded: their rate is mostly noise. */
export const MIN_RELIABLE = 300;
/** Groups below this are not drawn at all (a rate over a handful of loans is meaningless); see tooltip/table. */
export const MIN_SHOWN = 30;

const axisTick = (fill: string) => ({ fill, fontSize: 12 });

/** Clean rate ticks (0 / 5% / 10% ...) covering max, plus the matching domain. */
export function rateTicks(max: number): { ticks: number[]; domain: [number, number] } {
  const target = Math.max(max, 0.001) / 4;
  const steps = [0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25];
  const step = steps.find((s) => s >= target) ?? 0.25;
  const top = Math.ceil((max * 1.05) / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(Number(v.toFixed(4)));
  return { ticks, domain: [0, top] };
}

const tickPct = (v: number) => pct(v, v !== 0 && v < 0.1 && Math.round(v * 1000) % 10 !== 0 ? 1 : 0);

/**
 * Default rate per member of one dimension, single hue (one series -> slot 1), portfolio average as
 * a reference line. Columns for short ordered labels, horizontal bars for long nominal ones.
 */
export function RateBars({ data, avg, layout = "columns", height = 300, onSelect, selected = [] }: {
  data: DimRow[];
  avg?: number | null;
  layout?: "columns" | "bars";
  height?: number;
  onSelect?: (member: string) => void;
  selected?: string[];
}) {
  const { palette } = useTheme();
  const rows = useMemo(() => data.filter((d) => d.default_rate !== null && d.n_labelled >= MIN_SHOWN), [data]);
  const hidden = data.length - rows.length;
  const scale = rateTicks(Math.max(avg ?? 0, ...rows.map((d) => d.default_rate ?? 0)));
  const fill = (d: DimRow) =>
    selected.length && !selected.includes(d.member) ? palette.grid : palette.series[0];
  const opacity = (d: DimRow) => (d.n_labelled < MIN_RELIABLE ? 0.35 : 1);

  const tooltip = (
    <Tooltip
      cursor={{ fill: palette.grid, opacity: 0.45 }}
      content={({ active, payload }) => {
        if (!active || !payload?.length) return null;
        const d = payload[0].payload as DimRow;
        return (
          <TooltipCard
            title={label(d.member)}
            rows={[
              ["Default rate", pct(d.default_rate, 2)],
              ["Labelled loans", num(d.n_labelled)],
              ["Applications", num(d.n_applications)],
              ...(d.n_labelled < MIN_RELIABLE ? [["Note", "small sample"] as [string, string]] : []),
            ]}
          />
        );
      }}
    />
  );

  const common = {
    data: rows,
    onClick: onSelect
      ? (e: { activePayload?: { payload: DimRow }[] }) => {
          const m = e?.activePayload?.[0]?.payload?.member;
          if (m) onSelect(m);
        }
      : undefined,
    style: { cursor: onSelect ? "pointer" : "default" },
  };

  if (layout === "bars") {
    const h = Math.max(height, rows.length * 34 + 40);
    return (
      <>
      <ResponsiveContainer width="100%" height={h}>
        <BarChart {...common} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke={palette.grid} />
          <XAxis type="number" ticks={scale.ticks} domain={scale.domain} tickFormatter={tickPct}
            tick={axisTick(palette.muted)} axisLine={{ stroke: palette.axis }} tickLine={false} />
          <YAxis type="category" dataKey="member" width={150} tickFormatter={label}
            tick={axisTick(palette.ink2)} axisLine={false} tickLine={false} interval={0} />
          {tooltip}
          {avg != null && <ReferenceLine x={avg} stroke={palette.ink2} strokeWidth={1}
            label={{ value: `avg ${pct(avg)}`, position: "top", fill: palette.ink2, fontSize: 11 }} />}
          <Bar dataKey="default_rate" maxBarSize={20} radius={[0, 4, 4, 0]} isAnimationActive={false}
            label={{ position: "right", formatter: (v: number) => pct(v), fill: palette.ink2, fontSize: 11 }}>
            {rows.map((d) => <Cell key={d.member} fill={fill(d)} fillOpacity={opacity(d)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {hidden > 0 && <HiddenNote n={hidden} />}
      </>
    );
  }

  return (
    <>
    <ResponsiveContainer width="100%" height={height}>
      <BarChart {...common} margin={{ top: 20, right: avg != null ? 64 : 8, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} stroke={palette.grid} />
        <XAxis dataKey="member" tickFormatter={label} tick={axisTick(palette.ink2)}
          axisLine={{ stroke: palette.axis }} tickLine={false} interval={0} />
        <YAxis ticks={scale.ticks} domain={scale.domain} tickFormatter={tickPct} tick={axisTick(palette.muted)}
          axisLine={false} tickLine={false} width={44} />
        {tooltip}
        {avg != null && <ReferenceLine y={avg} stroke={palette.ink2} strokeWidth={1} ifOverflow="extendDomain"
          label={{ value: `avg ${pct(avg)}`, position: "right", fill: palette.ink2, fontSize: 11 }} />}
        <Bar dataKey="default_rate" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false}
          label={{ position: "top", formatter: (v: number) => pct(v), fill: palette.ink2, fontSize: 11 }}>
          {rows.map((d) => <Cell key={d.member} fill={fill(d)} fillOpacity={opacity(d)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
    {hidden > 0 && <HiddenNote n={hidden} />}
    </>
  );
}

function HiddenNote({ n }: { n: number }) {
  return (
    <p className="mt-1 text-[11px] text-ink-3">
      {n} group{n > 1 ? "s" : ""} with fewer than {MIN_SHOWN} labelled loans not drawn.
    </p>
  );
}

/** Default rate along the external-score axis: one line + 10% area wash. */
export function ScoreCurve({ data, avg, height = 280 }: {
  data: { score_mid: number; default_rate: number; n_labelled: number }[];
  avg?: number | null;
  height?: number;
}) {
  const { palette } = useTheme();
  const scale = rateTicks(Math.max(avg ?? 0, ...data.map((d) => d.default_rate)));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 12, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} stroke={palette.grid} />
        <XAxis dataKey="score_mid" type="number" domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={(v) => v.toFixed(1)} tick={axisTick(palette.muted)} axisLine={{ stroke: palette.axis }}
          tickLine={false} />
        <YAxis ticks={scale.ticks} domain={scale.domain} tickFormatter={tickPct} tick={axisTick(palette.muted)}
          axisLine={false} tickLine={false} width={44} />
        {avg != null && <ReferenceLine y={avg} stroke={palette.ink2} strokeWidth={1}
          label={{ value: `avg ${pct(avg)}`, position: "insideTopRight", fill: palette.ink2, fontSize: 11 }} />}
        <Tooltip
          cursor={{ stroke: palette.axis }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <TooltipCard
                title={`Score ${(d.score_mid - 0.025).toFixed(2)}–${(d.score_mid + 0.025).toFixed(2)}`}
                rows={[["Default rate", pct(d.default_rate, 2)], ["Labelled loans", num(d.n_labelled)]]}
              />
            );
          }}
        />
        <Area type="monotone" dataKey="default_rate" stroke={palette.series[0]} strokeWidth={2}
          fill={palette.series[0]} fillOpacity={0.1} isAnimationActive={false}
          dot={false} activeDot={{ r: 4, stroke: palette.surface, strokeWidth: 2 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Stacked columns/bars with categorical slots in a FIXED order per key (colour follows the entity). */
export function StackedBars({ data, xKey, keys, layout = "columns", height = 300, valueFormat = compact }: {
  data: Record<string, string | number>[];
  xKey: string;
  keys: string[];
  layout?: "columns" | "bars";
  height?: number;
  valueFormat?: (v: number) => string;
}) {
  const { palette } = useTheme();
  const horizontal = layout === "bars";
  const tooltip = (
    <Tooltip
      cursor={{ fill: palette.grid, opacity: 0.45 }}
      content={({ active, payload, label: l }) => {
        if (!active || !payload?.length) return null;
        const total = payload.reduce((s, p) => s + (Number(p.value) || 0), 0);
        return (
          <TooltipCard
            title={String(l)}
            rows={[
              ...payload.slice().reverse().map((p) => [
                <span className="inline-flex items-center gap-1.5" key={String(p.dataKey)}>
                  <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
                  {String(p.dataKey)}
                </span>,
                valueFormat(Number(p.value)),
              ] as [ReactNode, string]),
              ["Total", valueFormat(total)],
            ]}
          />
        );
      }}
    />
  );
  const bars = keys.map((k, i) => (
    <Bar key={k} dataKey={k} stackId="s" fill={palette.series[i % palette.series.length]}
      stroke={palette.surface} strokeWidth={1} isAnimationActive={false}
      maxBarSize={horizontal ? 20 : 28}
      radius={i === keys.length - 1 ? (horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]) : 0} />
  ));
  const legend = (
    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: palette.ink2, paddingTop: 8 }} />
  );
  if (horizontal) {
    return (
      <ResponsiveContainer width="100%" height={Math.max(height, data.length * 36 + 60)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke={palette.grid} />
          <XAxis type="number" tickFormatter={(v) => compact(v)} tick={axisTick(palette.muted)}
            axisLine={{ stroke: palette.axis }} tickLine={false} />
          <YAxis type="category" dataKey={xKey} width={140} tick={axisTick(palette.ink2)} axisLine={false} tickLine={false} interval={0} />
          {tooltip}
          {legend}
          {bars}
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} stroke={palette.grid} />
        <XAxis dataKey={xKey} tick={axisTick(palette.muted)} axisLine={{ stroke: palette.axis }} tickLine={false}
          minTickGap={16} />
        <YAxis tickFormatter={(v) => compact(v)} tick={axisTick(palette.muted)} axisLine={false} tickLine={false} width={48} />
        {tooltip}
        {legend}
        {bars}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Matrix of rates on the sequential blue ramp; cells with too few loans are left blank. */
export function Heatmap({ rows, cols, cell, rowLabel, colLabel, minN = 50 }: {
  rows: string[];
  cols: string[];
  cell: (r: string, c: string) => { value: number | null; n: number } | undefined;
  rowLabel: string;
  colLabel: string;
  minN?: number;
}) {
  const { palette } = useTheme();
  const values = rows.flatMap((r) => cols.map((c) => cell(r, c))).filter((v) => v && v.value != null && v.n >= minN)
    .map((v) => v!.value as number);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate" style={{ borderSpacing: 2 }}>
        <caption className="sr-only">{`${rowLabel} by ${colLabel}`}</caption>
        <thead>
          <tr>
            <th className="px-2 pb-1 text-left text-[11px] font-medium text-ink-3">{rowLabel} ↓ / {colLabel} →</th>
            {cols.map((c) => (
              <th key={c} className="px-1 pb-1 text-center text-xs font-medium text-ink-2">{label(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th className="whitespace-nowrap px-2 text-left text-xs font-medium text-ink-2">{label(r)}</th>
              {cols.map((c) => {
                const v = cell(r, c);
                const ok = v && v.value != null && v.n >= minN;
                const t = ok && hi > lo ? ((v!.value as number) - lo) / (hi - lo) : 0.5;
                const color = seqColor(palette, 0.08 + t * 0.8);
                return (
                  <td
                    key={c}
                    title={v ? `${label(r)} × ${label(c)}: ${pct(v.value, 2)} of ${num(v.n)} loans` : "no loans"}
                    className="num h-10 min-w-[64px] rounded-md text-center text-xs font-medium"
                    style={ok ? { background: color.fill, color: color.text } : { background: "transparent" }}
                  >
                    {ok ? pct(v!.value, 1) : <span className="text-ink-3">·</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-2 text-[11px] text-ink-3">
        <span>{pct(lo)}</span>
        <div className="h-2 w-40 rounded-full" style={{ background: `linear-gradient(90deg, ${palette.seq[1]}, ${palette.seq[11]})` }} />
        <span>{pct(hi)}</span>
        <span className="ml-2">· blank = fewer than {minN} labelled loans</span>
      </div>
    </div>
  );
}

/** Two-row box summary (p05-p95 whisker, p25-p75 box, median tick) - exact quantiles from SQL. */
export function BoxSummary({ data, format = (v: number) => v.toFixed(2) }: {
  data: { outcome: string; n: number; p05: number; p25: number; p50: number; p75: number; p95: number }[];
  format?: (v: number) => string;
}) {
  const { palette } = useTheme();
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.p95)) * 1.08;
  const x = (v: number) => `${(v / max) * 100}%`;
  const colors: Record<string, string> = { Repaid: palette.series[0], Default: palette.series[1] };
  return (
    <div className="space-y-5 pt-2">
      {data.map((d) => (
        <div key={d.outcome}>
          <div className="mb-1.5 flex items-baseline justify-between text-xs">
            <span className="inline-flex items-center gap-1.5 font-medium text-ink">
              <span className="h-2 w-2 rounded-sm" style={{ background: colors[d.outcome] }} />
              {d.outcome}
            </span>
            <span className="num text-ink-3">median {format(d.p50)} · n = {num(d.n)}</span>
          </div>
          <div className="relative h-7" role="img"
            aria-label={`${d.outcome}: 5th ${format(d.p05)}, 25th ${format(d.p25)}, median ${format(d.p50)}, 75th ${format(d.p75)}, 95th ${format(d.p95)}`}>
            <div className="absolute top-1/2 h-px -translate-y-1/2" style={{ left: x(d.p05), width: `calc(${x(d.p95)} - ${x(d.p05)})`, background: palette.axis }} />
            <div className="absolute top-1 bottom-1 rounded" style={{ left: x(d.p25), width: `calc(${x(d.p75)} - ${x(d.p25)})`, background: colors[d.outcome], opacity: 0.85 }} />
            <div className="absolute top-0 bottom-0 w-0.5 rounded" style={{ left: x(d.p50), background: palette.ink }} />
            {[d.p05, d.p95].map((v, i) => (
              <div key={i} className="absolute top-2 bottom-2 w-px" style={{ left: x(v), background: palette.axis }} />
            ))}
          </div>
        </div>
      ))}
      <div className="relative h-4 text-[11px] text-ink-3">
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <span key={f} className="num absolute -translate-x-1/2" style={{ left: `${f * 100}%` }}>{format(f * max)}</span>
        ))}
      </div>
    </div>
  );
}
