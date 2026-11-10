import clsx from "clsx";
import { Check, ChevronDown, Filter, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { label } from "../lib/format";
import { useFilters } from "../lib/filters";
import { useDimLabel, useMeta } from "../lib/meta";

/** One dropdown per filter dimension + removable chips. Filters apply to every page. */
export function FilterBar() {
  const meta = useMeta();
  const { filters, active, clear, toggle } = useFilters();
  const dimLabel = useDimLabel();

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink-3">
          <Filter className="h-3.5 w-3.5" /> Filters
        </span>
        {meta.filter_dims.map((dim) => (
          <DimDropdown key={dim} dim={dim} />
        ))}
        {active > 0 && (
          <button onClick={clear} className="ml-1 text-xs font-medium text-accent-ink hover:underline">
            Clear all
          </button>
        )}
      </div>
      {active > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(filters).flatMap(([dim, values]) =>
            values.map((v) => (
              <span key={`${dim}:${v}`}
                className="inline-flex items-center gap-1 rounded-full border border-accent/25 bg-accent-soft py-0.5 pl-2.5 pr-1 text-xs text-accent-ink">
                <span className="text-ink-3">{dimLabel(dim)}:</span> {label(v)}
                <button aria-label={`Remove ${dimLabel(dim)} ${v}`} onClick={() => toggle(dim, v)}
                  className="rounded-full p-0.5 hover:bg-accent/15">
                  <X className="h-3 w-3" />
                </button>
              </span>
            )),
          )}
        </div>
      )}
    </div>
  );
}

function DimDropdown({ dim }: { dim: string }) {
  const meta = useMeta();
  const dimLabel = useDimLabel();
  const { filters, toggle, set } = useFilters();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const chosen = filters[dim] ?? [];
  const members = meta.members[dim] ?? [];

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[13px] transition",
          chosen.length ? "border-accent/40 bg-accent-soft text-accent-ink" : "border-line bg-surface text-ink-2 hover:bg-raised",
        )}
      >
        {dimLabel(dim)}
        {chosen.length > 0 && (
          <span className="num rounded-full bg-accent px-1.5 text-[10px] font-semibold leading-4 text-white">{chosen.length}</span>
        )}
        <ChevronDown className={clsx("h-3.5 w-3.5 transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-1.5 w-60 rounded-xl border border-line bg-surface p-1.5 shadow-pop">
          <div className="max-h-72 overflow-y-auto">
            {members.map((m) => {
              const on = chosen.includes(m);
              return (
                <button key={m} onClick={() => toggle(dim, m)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[13px] text-ink-2 hover:bg-raised hover:text-ink">
                  <span className={clsx("grid h-4 w-4 place-items-center rounded border",
                    on ? "border-accent bg-accent text-white" : "border-line")}>
                    {on && <Check className="h-3 w-3" strokeWidth={3} />}
                  </span>
                  {label(m)}
                </button>
              );
            })}
          </div>
          {chosen.length > 0 && (
            <div className="mt-1 border-t border-line pt-1">
              <button onClick={() => set(dim, [])} className="w-full rounded-lg px-2 py-1.5 text-left text-xs font-medium text-accent-ink hover:bg-raised">
                Clear {dimLabel(dim).toLowerCase()}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
