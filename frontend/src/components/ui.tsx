import clsx from "clsx";
import { AlertTriangle, Info } from "lucide-react";
import type { ReactNode } from "react";

export function Card({ title, subtitle, actions, children, className, bodyClassName }: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={clsx("card flex flex-col", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-4 pt-4 sm:px-5">
          <div className="min-w-0">
            {title && <h3 className="text-[15px] font-semibold leading-tight text-ink">{title}</h3>}
            {subtitle && <p className="mt-1 text-[13px] leading-snug text-ink-3">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={clsx("flex-1 px-4 pb-4 pt-3 sm:px-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function StatTile({ label, value, hint, accent, loading }: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  accent?: boolean;
  loading?: boolean;
}) {
  return (
    <div className={clsx("card card-pad", accent && "ring-1 ring-accent/30")}>
      <p className="text-[13px] font-medium text-ink-3">{label}</p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded-md bg-raised" />
      ) : (
        <p className={clsx("mt-1.5 text-[28px] font-semibold leading-none tracking-tight", accent ? "text-accent-ink" : "text-ink")}>
          {value}
        </p>
      )}
      {hint && <p className="mt-2 text-xs text-ink-3">{hint}</p>}
    </div>
  );
}

export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div className="flex items-end gap-3 px-2" style={{ height }} aria-label="Loading chart">
      {[55, 80, 65, 90, 45, 70, 35].map((h, i) => (
        <div key={i} className="flex-1 animate-pulse rounded-t-md bg-raised" style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-bad/30 bg-bad/5 p-3 text-sm text-ink-2">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-bad" />
      <span>{message}</span>
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-1.5 text-xs leading-relaxed text-ink-3">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

export function Empty({ children = "No data for the current filters." }: { children?: ReactNode }) {
  return <div className="grid h-40 place-items-center text-sm text-ink-3">{children}</div>;
}

export function Segmented<T extends string>({ value, options, onChange, ariaLabel }: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="inline-flex rounded-lg border border-line bg-raised/60 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "rounded-md px-2.5 py-1 text-xs font-medium transition",
            value === o.value ? "bg-surface text-ink shadow-card" : "text-ink-3 hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Select({ label, value, options, onChange, className }: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <label className={clsx("flex flex-col gap-1", className)}>
      <span className="text-xs font-medium text-ink-3">{label}</span>
      <select className="input cursor-pointer" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Tooltip card shared by every chart. */
export function TooltipCard({ title, rows }: { title: ReactNode; rows: [ReactNode, ReactNode][] }) {
  return (
    <div className="min-w-[160px] rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-pop">
      <p className="mb-1 font-semibold text-ink">{title}</p>
      {rows.map(([k, v], i) => (
        <div key={i} className="flex justify-between gap-4 py-0.5">
          <span className="text-ink-3">{k}</span>
          <span className="num font-medium text-ink">{v}</span>
        </div>
      ))}
    </div>
  );
}

export function PageHeader({ title, description, children }: { title: string; description: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <h1 className="text-[22px] font-semibold tracking-tight text-ink sm:text-[26px]">{title}</h1>
        <p className="mt-1.5 text-[14px] leading-relaxed text-ink-2">{description}</p>
      </div>
      {children}
    </div>
  );
}
