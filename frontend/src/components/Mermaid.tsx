import { Download, Maximize2, X } from "lucide-react";
import mermaid from "mermaid";
import { useEffect, useId, useState } from "react";
import { useTheme, type ThemeName } from "../lib/theme";

const VARS: Record<ThemeName, Record<string, string>> = {
  light: {
    background: "#fcfcfb", primaryColor: "#eef4fd", primaryBorderColor: "#2a78d6", primaryTextColor: "#171716",
    secondaryColor: "#f0efec", tertiaryColor: "#f6f6f3", lineColor: "#898781", textColor: "#171716",
    clusterBkg: "#f6f6f3", clusterBorder: "#e1e0d9", edgeLabelBackground: "#fcfcfb", nodeBorder: "#2a78d6",
    actorBkg: "#eef4fd", actorBorder: "#2a78d6", signalColor: "#52514e", signalTextColor: "#171716",
    noteBkgColor: "#fff6df", noteBorderColor: "#eda100", labelBoxBkgColor: "#eef4fd", labelBoxBorderColor: "#2a78d6",
    attributeBackgroundColorOdd: "#fcfcfb", attributeBackgroundColorEven: "#f6f6f3",
  },
  dark: {
    background: "#1a1a19", primaryColor: "#16263b", primaryBorderColor: "#3987e5", primaryTextColor: "#f0efec",
    secondaryColor: "#252523", tertiaryColor: "#111110", lineColor: "#898781", textColor: "#f0efec",
    clusterBkg: "#141413", clusterBorder: "#33332f", edgeLabelBackground: "#1a1a19", nodeBorder: "#3987e5",
    actorBkg: "#16263b", actorBorder: "#3987e5", signalColor: "#c3c2b7", signalTextColor: "#f0efec",
    noteBkgColor: "#2b2414", noteBorderColor: "#c98500", labelBoxBkgColor: "#16263b", labelBoxBorderColor: "#3987e5",
    attributeBackgroundColorOdd: "#1a1a19", attributeBackgroundColorEven: "#222220",
  },
};

let queue: Promise<unknown> = Promise.resolve();

/** Renders Mermaid source to inline SVG, re-themed with the app's light/dark tokens. */
export function Mermaid({ code, name }: { code: string; name: string }) {
  const { theme } = useTheme();
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const [full, setFull] = useState(false);

  useEffect(() => {
    let alive = true;
    // mermaid.render is not re-entrant: serialise renders across all diagrams.
    queue = queue.then(async () => {
      mermaid.initialize({
        startOnLoad: false,
        theme: "base",
        securityLevel: "strict",
        fontFamily: '"Segoe UI", system-ui, sans-serif',
        themeVariables: { ...VARS[theme], fontSize: "14px" },
        flowchart: { curve: "basis", padding: 12, htmlLabels: true },
        er: { useMaxWidth: true },
        sequence: { useMaxWidth: true, mirrorActors: false },
      });
      try {
        const out = await mermaid.render(`m${id}${theme}`, code);
        if (alive) { setSvg(out.svg); setErr(null); }
      } catch (e) {
        if (alive) setErr(String(e));
      }
    });
    return () => { alive = false; };
  }, [code, theme, id]);

  const download = () => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${name}.svg` });
    a.click();
    URL.revokeObjectURL(url);
  };

  if (err) return <pre className="overflow-auto rounded-lg bg-raised p-3 text-xs text-bad">{err}</pre>;
  if (!svg) return <div className="h-64 animate-pulse rounded-lg bg-raised/60" />;

  return (
    <>
      <div className="group relative">
        <div className="mermaid-host overflow-x-auto rounded-lg [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
          dangerouslySetInnerHTML={{ __html: svg }} />
        <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
          <button className="btn px-2 py-1 text-xs" onClick={() => setFull(true)} aria-label="Full screen"><Maximize2 className="h-3.5 w-3.5" /></button>
          <button className="btn px-2 py-1 text-xs" onClick={download}><Download className="h-3.5 w-3.5" /> SVG</button>
        </div>
      </div>
      {full && (
        <div className="fixed inset-0 z-50 flex flex-col bg-page/95 p-4 backdrop-blur" role="dialog" aria-modal>
          <div className="mb-2 flex justify-end">
            <button className="btn" onClick={() => setFull(false)}><X className="h-4 w-4" /> Close</button>
          </div>
          <div className="flex-1 overflow-auto rounded-xl border border-line bg-surface p-6 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-none"
            dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      )}
    </>
  );
}
