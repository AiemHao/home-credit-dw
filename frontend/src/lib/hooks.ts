import { apiUrl, useApi, type DimRow, type Kpis } from "./api";
import { useFilters, type Filters } from "./filters";
import { useMeta } from "./meta";

/** Click-to-filter: bars of a sidebar dimension become filter toggles (cross-filtering). */
export function useCrossFilter(dim: string) {
  const meta = useMeta();
  const { filters, toggle } = useFilters();
  if (!meta.filter_dims.includes(dim)) return { selected: [] as string[], onSelect: undefined };
  return { selected: filters[dim] ?? [], onSelect: (m: string) => toggle(dim, m) };
}

export function useKpis() {
  const { filters } = useFilters();
  return useApi<Kpis>(apiUrl("kpis", filters));
}

/**
 * Measures per member of `dim`. With excludeSelf the chart ignores the filter on its own dimension,
 * so a chart used to pick members keeps showing all of them (selected ones highlighted).
 */
export function useByDim(dim: string, extra: Filters = {}, excludeSelf = false) {
  const { filters } = useFilters();
  const f: Filters = { ...filters, ...extra };
  if (excludeSelf) delete f[dim];
  return useApi<DimRow[]>(apiUrl(`by/${dim}`, f));
}
