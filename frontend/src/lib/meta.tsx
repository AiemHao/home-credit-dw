import { createContext, useContext, type ReactNode } from "react";
import { useApi, type Meta } from "./api";

const Ctx = createContext<Meta | null>(null);

/** Loads /api/meta once (dimensions, members, warehouse info) and gates the app on it. */
export function MetaProvider({ children, fallback }: { children: ReactNode; fallback: (err?: string) => ReactNode }) {
  const { data, error } = useApi<Meta>("/api/meta");
  if (!data) return <>{fallback(error)}</>;
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}

export function useMeta(): Meta {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useMeta outside MetaProvider");
  return ctx;
}

export function useDimLabel(): (dim: string) => string {
  const meta = useMeta();
  return (dim) => meta.dimensions.find((d) => d.key === dim)?.label ?? dim;
}
