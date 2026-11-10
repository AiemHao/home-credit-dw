import clsx from "clsx";
import {
  Boxes, Briefcase, Database, Gauge, History, Layers, LayoutDashboard, Menu, Moon, Network, Sun, X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { compact } from "../lib/format";
import { useMeta } from "../lib/meta";
import { useTheme } from "../lib/theme";
import { FilterBar } from "./FilterBar";

export const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, filters: true },
  { to: "/portfolio", label: "Portfolio", icon: Briefcase, filters: true },
  { to: "/drilldown", label: "Drill-down", icon: Layers, filters: true },
  { to: "/credit-history", label: "Credit history", icon: History, filters: true },
  { to: "/olap", label: "OLAP explorer", icon: Boxes, filters: true },
  { to: "/simulator", label: "Risk simulator", icon: Gauge, filters: false },
  { to: "/architecture", label: "Architecture", icon: Network, filters: false },
];

export function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const page = NAV.find((n) => n.to === pathname) ?? NAV[0];

  useEffect(() => setOpen(false), [pathname]);

  return (
    <div className="flex min-h-full">
      {/* Sidebar: fixed on desktop, drawer on mobile */}
      <div
        className={clsx("fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] lg:hidden", open ? "block" : "hidden")}
        onClick={() => setOpen(false)}
      />
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-surface transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <Sidebar onClose={() => setOpen(false)} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-line bg-page/85 backdrop-blur">
          <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <button className="btn px-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <Menu className="h-4 w-4" />
            </button>
            <div className="min-w-0 flex-1">
              {page.filters ? <FilterBar /> : <p className="text-sm font-medium text-ink-2">{page.label}</p>}
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        <footer className="mx-auto w-full max-w-[1400px] px-4 pb-6 text-xs text-ink-3 sm:px-6 lg:px-8">
          CO4031 · Data Warehouse &amp; Decision Support Systems · Home Credit Default Risk (Kaggle)
        </footer>
      </div>
    </div>
  );
}

function Sidebar({ onClose }: { onClose: () => void }) {
  const meta = useMeta();
  const { theme, toggle } = useTheme();
  const factRows = meta.warehouse.tables
    .filter((t) => t.table_name.startsWith("fact_"))
    .reduce((s, t) => s + t.n_rows, 0);

  return (
    <>
      <div className="flex items-center justify-between px-5 pb-4 pt-5">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-white shadow-card">
            <svg viewBox="0 0 32 32" className="h-5 w-5" aria-hidden>
              <rect x="5" y="17" width="5" height="10" rx="1.5" fill="currentColor" />
              <rect x="13.5" y="11" width="5" height="16" rx="1.5" fill="currentColor" />
              <rect x="22" y="5" width="5" height="22" rx="1.5" fill="currentColor" />
            </svg>
          </div>
          <div>
            <p className="text-[15px] font-semibold leading-tight text-ink">Home Credit DW</p>
            <p className="text-[11px] text-ink-3">Credit-risk warehouse &amp; DSS</p>
          </div>
        </div>
        <button className="rounded-md p-1 text-ink-3 hover:bg-raised lg:hidden" onClick={onClose} aria-label="Close menu">
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 px-3" aria-label="Pages">
        <p className="eyebrow px-2 pb-1.5 pt-2">Analytics</p>
        {NAV.slice(0, 5).map((n) => <NavItem key={n.to} {...n} />)}
        <p className="eyebrow px-2 pb-1.5 pt-4">Decision &amp; design</p>
        {NAV.slice(5).map((n) => <NavItem key={n.to} {...n} />)}
      </nav>

      <div className="m-3 rounded-xl border border-line bg-raised/50 p-3">
        <div className="flex items-center gap-2 text-xs font-medium text-ink-2">
          <Database className="h-3.5 w-3.5 text-accent" />
          <span className="truncate">{meta.warehouse.name}</span>
          <span className="ml-auto rounded bg-surface px-1.5 py-0.5 text-[10px] uppercase text-ink-3">{meta.warehouse.target}</span>
        </div>
        <p className="num mt-1.5 text-[11px] text-ink-3">
          {compact(factRows)} fact rows · snapshot {meta.warehouse.anchor_date}
        </p>
      </div>

      <div className="flex items-center justify-between border-t border-line px-5 py-3">
        <span className="text-xs text-ink-3">Theme</span>
        <button onClick={toggle} className="btn px-2 py-1" aria-label="Toggle dark mode">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          <span className="text-xs">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </div>
    </>
  );
}

function NavItem({ to, label, icon: Icon }: { to: string; label: string; icon: typeof LayoutDashboard }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        clsx(
          "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] font-medium transition",
          isActive ? "bg-accent-soft text-accent-ink" : "text-ink-2 hover:bg-raised hover:text-ink",
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={clsx("h-4 w-4", isActive ? "text-accent" : "text-ink-3 group-hover:text-ink-2")} />
          {label}
        </>
      )}
    </NavLink>
  );
}
