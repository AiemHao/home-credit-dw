import { Download, Maximize2, X } from "lucide-react";
import { useState } from "react";

/**
 * Inline a hand-drawn SVG diagram from docs/diagrams. The SVG carries its own styles, keyed to
 * :root[data-theme], so it follows the app's light/dark toggle; as a plain file it follows the OS.
 */
export function Diagram({ svg, name }: { svg: string; name: string }) {
  const [full, setFull] = useState(false);

  const download = () => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `${name}.svg` });
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div className="group relative">
        <div className="overflow-x-auto [&_svg]:mx-auto [&_svg]:block [&_svg]:h-auto [&_svg]:w-full [&_svg]:min-w-[760px] [&_svg]:rounded-lg"
          dangerouslySetInnerHTML={{ __html: svg }} />
        <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition focus-within:opacity-100 group-hover:opacity-100">
          <button className="btn px-2 py-1 text-xs" onClick={() => setFull(true)} aria-label="Full screen">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button className="btn px-2 py-1 text-xs" onClick={download}><Download className="h-3.5 w-3.5" /> SVG</button>
        </div>
      </div>
      {full && (
        <div className="fixed inset-0 z-50 flex flex-col bg-page/95 p-4 backdrop-blur" role="dialog" aria-modal>
          <div className="mb-2 flex justify-end">
            <button className="btn" onClick={() => setFull(false)}><X className="h-4 w-4" /> Close</button>
          </div>
          <div className="flex-1 overflow-auto rounded-xl border border-line bg-surface p-4 [&_svg]:mx-auto [&_svg]:block [&_svg]:h-auto [&_svg]:w-[max(100%,1240px)]"
            dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      )}
    </>
  );
}
