import { Loader2 } from "lucide-react";
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { FiltersProvider } from "./lib/filters";
import { MetaProvider } from "./lib/meta";
import { ThemeProvider } from "./lib/theme";
import CreditHistory from "./pages/CreditHistory";
import Drilldown from "./pages/Drilldown";
import OlapExplorer from "./pages/OlapExplorer";
import Overview from "./pages/Overview";
import Portfolio from "./pages/Portfolio";
import RiskSimulator from "./pages/RiskSimulator";

// Mermaid is large: load the Architecture page (and mermaid) only when it is opened.
const Architecture = lazy(() => import("./pages/Architecture"));

function Splash({ error }: { error?: string }) {
  return (
    <div className="grid min-h-full place-items-center p-6">
      <div className="card card-pad max-w-md text-center">
        {error ? (
          <>
            <p className="text-[15px] font-semibold text-ink">Cannot reach the API</p>
            <p className="mt-2 text-sm text-ink-2">{error}</p>
            <p className="mt-3 text-xs text-ink-3">Start it with <code>hcdw serve</code> (and build the warehouse first with <code>hcdw etl</code>).</p>
          </>
        ) : (
          <p className="flex items-center gap-2 text-sm text-ink-2"><Loader2 className="h-4 w-4 animate-spin" /> Connecting to the warehouse…</p>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <MetaProvider fallback={(err) => <Splash error={err} />}>
        <FiltersProvider>
          <BrowserRouter>
            <Layout>
              <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-raised/50" />}>
                <Routes>
                  <Route path="/" element={<Overview />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/drilldown" element={<Drilldown />} />
                  <Route path="/credit-history" element={<CreditHistory />} />
                  <Route path="/olap" element={<OlapExplorer />} />
                  <Route path="/simulator" element={<RiskSimulator />} />
                  <Route path="/architecture" element={<Architecture />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </Layout>
          </BrowserRouter>
        </FiltersProvider>
      </MetaProvider>
    </ThemeProvider>
  );
}
