import clsx from "clsx";
import { useState } from "react";
import sys from "../../../docs/diagrams/01_system_architecture.mmd?raw";
import etl from "../../../docs/diagrams/02_etl_pipeline.mmd?raw";
import star from "../../../docs/diagrams/03_star_schema.mmd?raw";
import lineage from "../../../docs/diagrams/04_data_lineage.mmd?raw";
import request from "../../../docs/diagrams/05_request_flow.mmd?raw";
import dss from "../../../docs/diagrams/06_dss_flow.mmd?raw";
import { Mermaid } from "../components/Mermaid";
import { Card, PageHeader } from "../components/ui";

const DIAGRAMS = [
  {
    key: "system", name: "01_system_architecture", title: "System architecture", code: sys,
    summary: "Five layers, each with one job: source files → ETL → DuckDB warehouse (staging / dw / mart) → FastAPI (OLAP + DSS) → React dashboard.",
    points: [
      "The warehouse is a single DuckDB file: columnar, vectorised, no server to run - full refresh of 2.6 GB of CSV in about 40 s.",
      "The API is the only reader of the warehouse; the browser never sees SQL it can change (dimensions are whitelisted, values are bound parameters).",
      "MotherDuck is an optional shared copy so teammates can query without downloading the data.",
    ],
  },
  {
    key: "etl", name: "02_etl_pipeline", title: "ETL pipeline", code: etl,
    summary: "Seven steps write into a side file; only a run that passes every step replaces the live warehouse.",
    points: [
      "Extract reads every column as text and TRY_CASTs to the declared staging type, so one bad value never aborts a 27M-row load.",
      "Cleaning rules R1–R10 are in pandas (readable, unit-tested); heavy aggregation is in SQL (fast).",
      "Quality gate: primary keys, foreign keys, row completeness and money reconciliation (staging total = fact total).",
    ],
  },
  {
    key: "star", name: "03_star_schema", title: "Star schema (fact constellation)", code: star,
    summary: "Two facts share the customer and time dimensions, so analyses can drill across from applications to bureau credits.",
    points: [
      "Grain: one loan application (SK_ID_CURR) and one bureau credit (SK_ID_BUREAU).",
      "dim_credit_history is a mini-dimension: tens of millions of history rows collapsed into ~200 bucketed profiles.",
      "dim_bureau_category is a junk dimension; dim_time plays two roles (open date, close date) on the bureau fact.",
    ],
  },
  {
    key: "lineage", name: "04_data_lineage", title: "Data lineage", code: lineage,
    summary: "Where every warehouse table comes from - from Kaggle file to staging, aggregate and star-schema table.",
    points: [
      "Child tables (1..N rows per applicant) are collapsed to one credit profile per applicant before they reach a dimension.",
      "fact_bureau_credit keeps the bureau grain and links back to dim_customer for drill-across.",
    ],
  },
  {
    key: "request", name: "05_request_flow", title: "Query flow (OLAP request)", code: request,
    summary: "What happens when an analyst clicks a bar: shared filter state → REST call → whitelisted SQL → cached result.",
    points: [
      "Results are memoised per (query, filters): the warehouse is a static snapshot, so the cache never goes stale until the next ETL.",
      "Typical cold query on 356K applications: 50–200 ms; cached: under 5 ms.",
    ],
  },
  {
    key: "dss", name: "06_dss_flow", title: "Decision support flow", code: dss,
    summary: "The DSS turns a model probability and underwriting rules into one explainable decision.",
    points: [
      "The model is trained on the warehouse (mart.v_application_wide), never on raw files, so the dashboard and the model see the same data.",
      "The strictest outcome wins and every triggered rule is shown as a reason.",
    ],
  },
];

const STACK = [
  ["Storage & OLAP", "DuckDB (local file) · MotherDuck (optional cloud copy)"],
  ["ETL", "Python 3.12 · pandas · DuckDB SQL · Typer CLI (hcdw)"],
  ["Backend", "FastAPI · Uvicorn · cached, whitelisted SQL"],
  ["Frontend", "React 18 · TypeScript · Tailwind CSS · Recharts · Mermaid"],
  ["Decision support", "LightGBM · scikit-learn · business rules"],
  ["Quality", "pytest (ETL, API) · data-quality report per run"],
];

export default function Architecture() {
  // ?diagram=star opens one diagram directly (deep link; used by scripts/capture_figures.py).
  const [active, setActive] = useState(() => {
    const want = new URLSearchParams(window.location.search).get("diagram");
    return DIAGRAMS.some((x) => x.key === want) ? want! : DIAGRAMS[0].key;
  });
  const d = DIAGRAMS.find((x) => x.key === active)!;
  return (
    <div className="space-y-6">
      <PageHeader title="Architecture & design"
        description="How the system is built - from Kaggle files to this page. Diagram sources are plain Mermaid files in docs/diagrams/, rendered here and on GitHub; hover a diagram to download it as SVG for the report." />

      <div className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-surface p-1">
        {DIAGRAMS.map((x, i) => (
          <button key={x.key} onClick={() => setActive(x.key)}
            className={clsx("whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] font-medium transition",
              active === x.key ? "bg-accent-soft text-accent-ink" : "text-ink-2 hover:bg-raised")}>
            <span className="num mr-1.5 text-ink-3">{i + 1}</span>{x.title}
          </button>
        ))}
      </div>

      <Card title={d.title} subtitle={d.summary}>
        <Mermaid key={d.key} code={d.code} name={d.name} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Design notes">
          <ul className="space-y-2.5">
            {d.points.map((p) => (
              <li key={p} className="flex gap-2 text-[13px] leading-relaxed text-ink-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" /> {p}
              </li>
            ))}
          </ul>
          <p className="mt-4 font-mono text-[11px] text-ink-3">docs/diagrams/{d.name}.mmd</p>
        </Card>
        <Card title="Tech stack">
          <dl className="grid gap-x-6 gap-y-2.5 sm:grid-cols-2">
            {STACK.map(([k, v]) => (
              <div key={k}>
                <dt className="eyebrow">{k}</dt>
                <dd className="text-[13px] text-ink-2">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>
    </div>
  );
}
