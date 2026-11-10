import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemeName = "light" | "dark";

/** Chart palette per theme (validated reference palette: fixed categorical order, one-hue ramps). */
export interface ChartPalette {
  surface: string;
  ink: string;
  ink2: string;
  muted: string;
  grid: string;
  axis: string;
  series: string[]; // categorical slots, fixed order - never cycled
  seq: string[]; // sequential blue ramp, light -> dark (100..700)
  status: { good: string; warning: string; serious: string; critical: string };
}

const SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
  "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];

const PALETTES: Record<ThemeName, ChartPalette> = {
  light: {
    surface: "#fcfcfb", ink: "#171716", ink2: "#52514e", muted: "#898781",
    grid: "#e1e0d9", axis: "#c3c2b7",
    series: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    seq: SEQ,
    status: { good: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" },
  },
  dark: {
    surface: "#1a1a19", ink: "#f0efec", ink2: "#c3c2b7", muted: "#898781",
    grid: "#2c2c2a", axis: "#383835",
    series: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
    seq: SEQ,
    status: { good: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" },
  },
};

interface ThemeCtx {
  theme: ThemeName;
  palette: ChartPalette;
  toggle: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function initialTheme(): ThemeName {
  const t = document.documentElement.dataset.theme;
  return t === "dark" ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeName>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("hcdw-theme", theme);
    } catch {
      /* storage may be unavailable (private window); the theme still works for this visit */
    }
  }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === "dark" ? "light" : "dark")), []);
  const value = useMemo(() => ({ theme, palette: PALETTES[theme], toggle }), [theme, toggle]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTheme outside ThemeProvider");
  return ctx;
}

/** Map t in [0,1] onto the sequential ramp; returns fill + readable text colour. */
export function seqColor(palette: ChartPalette, t: number): { fill: string; text: string } {
  const ramp = palette.seq;
  const i = Math.max(0, Math.min(ramp.length - 1, Math.round(t * (ramp.length - 1))));
  return { fill: ramp[i], text: i >= 6 ? "#ffffff" : "#0b0b0b" };
}
