import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

/** Global slice/dice state shared by every page: {dimension: [members]}. */
export type Filters = Record<string, string[]>;

interface FiltersCtx {
  filters: Filters;
  active: number;
  toggle: (dim: string, member: string) => void;
  set: (dim: string, members: string[]) => void;
  clear: () => void;
}

const Ctx = createContext<FiltersCtx | null>(null);
const KEY = "hcdw-filters";

function load(): Filters {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Filters) : {};
  } catch {
    return {};
  }
}

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<Filters>(load);

  useEffect(() => {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(filters));
    } catch {
      /* not critical */
    }
  }, [filters]);

  const set = useCallback((dim: string, members: string[]) => {
    setFilters((f) => {
      const next = { ...f };
      if (members.length) next[dim] = [...members].sort();
      else delete next[dim];
      return next;
    });
  }, []);

  const toggle = useCallback((dim: string, member: string) => {
    setFilters((f) => {
      const cur = f[dim] ?? [];
      const members = cur.includes(member) ? cur.filter((m) => m !== member) : [...cur, member];
      const next = { ...f };
      if (members.length) next[dim] = members.sort();
      else delete next[dim];
      return next;
    });
  }, []);

  const clear = useCallback(() => setFilters({}), []);
  const active = useMemo(() => Object.values(filters).reduce((n, v) => n + v.length, 0), [filters]);
  const value = useMemo(() => ({ filters, active, toggle, set, clear }), [filters, active, toggle, set, clear]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFilters(): FiltersCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useFilters outside FiltersProvider");
  return ctx;
}
