import { useEffect, useState } from "react";
import type { Filters } from "./filters";

/** Build "/api/x?dim=a&dim=b&key=v" from filters + extra params. */
export function apiUrl(path: string, filters: Filters = {}, extra: Record<string, string | number> = {}): string {
  const qs = new URLSearchParams();
  for (const [dim, values] of Object.entries(filters)) for (const v of values) qs.append(dim, v);
  for (const [k, v] of Object.entries(extra)) qs.set(k, String(v));
  const s = qs.toString();
  return `/api/${path}${s ? `?${s}` : ""}`;
}

const cache = new Map<string, unknown>();

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep the status line */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface ApiState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
}

/** GET with an in-memory cache (the warehouse is a static snapshot) and request cancellation. */
export function useApi<T>(url: string | null): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>(() =>
    url && cache.has(url) ? { data: cache.get(url) as T, error: undefined, loading: false }
      : { data: undefined, error: undefined, loading: !!url },
  );

  useEffect(() => {
    if (!url) return;
    if (cache.has(url)) {
      setState({ data: cache.get(url) as T, error: undefined, loading: false });
      return;
    }
    const ctrl = new AbortController();
    setState((s) => ({ data: s.data, error: undefined, loading: true }));
    getJson<T>(url, ctrl.signal)
      .then((data) => {
        cache.set(url, data);
        setState({ data, error: undefined, loading: false });
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") setState({ data: undefined, error: e.message, loading: false });
      });
    return () => ctrl.abort();
  }, [url]);

  return state;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}

// ---- response types -------------------------------------------------------------------------
export interface Meta {
  warehouse: { target: string; name: string; anchor_date: string; tables: { table_name: string; n_rows: number }[] };
  dimensions: { key: string; label: string }[];
  filter_dims: string[];
  measures: { key: string; label: string; kind: string }[];
  members: Record<string, string[]>;
}

export interface Kpis {
  n_applications: number;
  n_labelled: number;
  default_rate: number | null;
  median_dti: number | null;
  overdue_share: number | null;
  avg_credit: number | null;
  total_credit: number | null;
  avg_ext_source: number | null;
}

export interface DimRow {
  member: string;
  n_applications: number;
  n_labelled: number;
  default_rate: number | null;
  overdue_share: number | null;
  avg_credit: number | null;
  median_dti: number | null;
}
