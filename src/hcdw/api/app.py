"""FastAPI application: JSON endpoints under /api, plus the built React app (frontend/dist) at /.

Run:  hcdw serve            (production: serves the built frontend too)
      hcdw serve --reload   (backend development; run `npm run dev` in frontend/ for the UI)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from hcdw.api.queries import (DIMENSIONS, FILTER_DIMS, MEASURES, Filters, Queries, Warehouse,
                              make_filters)
from hcdw.config import ROOT, get_settings

FRONTEND_DIST = ROOT / "frontend" / "dist"
RESERVED = {"row", "col", "measure", "grain", "levels", "x", "y"}


def parse_filters(request: Request) -> Filters:
    """?age_bucket=25-34&age_bucket=35-44&gender=F -> filters tuple. Unknown keys -> 400."""
    raw: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key in RESERVED:
            continue
        if key not in DIMENSIONS:
            raise HTTPException(400, f"Unknown filter '{key}'")
        raw.setdefault(key, []).append(value)
    return make_filters(raw)


class SimulatorInput(BaseModel):
    amt_income: float = Field(180_000, gt=0)
    amt_credit: float = Field(600_000, gt=0)
    amt_annuity: float = Field(27_000, ge=0)
    age_years: float = Field(38, ge=18, le=100)
    years_employed: float = Field(5, ge=0, le=60)
    ext_source_mean: float = Field(0.5, ge=0, le=1)
    max_dpd_days: int = Field(0, ge=0)
    cnt_bureau_active: int = Field(1, ge=0)
    has_current_overdue: bool = False
    income_type: str = "Working"
    contract_type: str = "Cash loans"


def create_app(dw_path: Path | None = None) -> FastAPI:
    wh = Warehouse(dw_path)
    q = Queries(wh)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        wh.close()

    app = FastAPI(title="Home Credit DW API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.exception_handler(ValueError)
    async def _bad_request(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # ---- metadata -----------------------------------------------------------------------------
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/meta")
    def meta() -> dict:
        s = get_settings()
        return {
            "warehouse": {
                "target": s.dw_target,
                "name": (dw_path or s.dw_path).name if (dw_path or s.dw_target == "local") else s.md_database,
                "anchor_date": s.anchor_date,
                **q.warehouse_info(),
            },
            "dimensions": [{"key": k, "label": v} for k, v in DIMENSIONS.items()],
            "filter_dims": FILTER_DIMS,
            "measures": [{"key": k, "label": lbl, "kind": kind} for k, (lbl, _, kind) in MEASURES.items()],
            "members": {d: q.members(d) for d in DIMENSIONS},
        }

    # ---- application fact ---------------------------------------------------------------------
    @app.get("/api/kpis")
    def kpis(request: Request) -> dict:
        return q.kpis(parse_filters(request))

    @app.get("/api/by/{dim}")
    def by_dimension(dim: str, request: Request) -> list[dict]:
        return q.by_dimension(dim, parse_filters(request))

    @app.get("/api/cross")
    def cross(request: Request, x: str = Query(...), y: str = Query(...)) -> list[dict]:
        return q.cross(x, y, parse_filters(request))

    @app.get("/api/score-curve")
    def score_curve(request: Request) -> list[dict]:
        return q.score_curve(parse_filters(request))

    @app.get("/api/dti-by-outcome")
    def dti_by_outcome(request: Request) -> list[dict]:
        return q.dti_by_outcome(parse_filters(request))

    @app.get("/api/hierarchy")
    def hierarchy(request: Request, levels: str = Query(..., description="comma-separated dims")) -> list[dict]:
        dims = tuple(d for d in levels.split(",") if d)
        if not 1 <= len(dims) <= 4:
            raise HTTPException(400, "levels must name 1 to 4 dimensions")
        return q.hierarchy(dims, parse_filters(request))

    # ---- bureau fact --------------------------------------------------------------------------
    @app.get("/api/bureau/kpis")
    def bureau_kpis(request: Request) -> dict:
        return q.bureau_kpis(parse_filters(request))

    @app.get("/api/bureau/trend")
    def bureau_trend(request: Request, grain: str = Query("quarter", pattern="^(year|quarter|month)$")) -> list[dict]:
        return q.bureau_trend(parse_filters(request), grain)

    @app.get("/api/bureau/by-type")
    def bureau_by_type(request: Request) -> list[dict]:
        return q.bureau_by_type(parse_filters(request))

    # ---- OLAP ---------------------------------------------------------------------------------
    @app.get("/api/pivot")
    def pivot(request: Request, row: str = Query(...), col: str = Query(...),
              measure: str = Query("default_rate")) -> dict:
        return q.pivot(row, col, measure, parse_filters(request))

    @app.get("/api/olap")
    def olap_list() -> list[dict]:
        return [{"name": n, "sql": q.olap_sql(n)} for n in q.olap_files()]

    @app.get("/api/olap/{name}")
    def olap_run(name: str) -> dict:
        return {"name": name, "sql": q.olap_sql(name), **q.run_olap(name)}

    # ---- DSS (model + rules) -------------------------------------------------------
    @app.get("/api/simulator/options")
    def simulator_options() -> dict:
        from dss.predict import model_available

        return {
            "model_available": model_available(),
            "income_type": q.members("income_type"),
            "contract_type": q.members("contract_type"),
        }

    @app.post("/api/simulator/score")
    def simulator_score(inp: SimulatorInput) -> dict:
        from dss.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
        from dss.predict import model_available, score
        from dss.rules import P_GREEN_MAX, P_RED_MIN, evaluate

        goods = inp.amt_credit * 0.9  # typical goods price / credit ratio in the data
        feat = {c: None for c in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
        feat.update({
            "amt_income": inp.amt_income, "amt_credit": inp.amt_credit, "amt_annuity": inp.amt_annuity,
            "amt_goods_price": goods, "debt_to_income": inp.amt_annuity / inp.amt_income,
            "credit_to_income": inp.amt_credit / inp.amt_income, "credit_to_goods": inp.amt_credit / goods,
            "ext_source_mean": inp.ext_source_mean, "age_years": inp.age_years,
            "years_employed": inp.years_employed, "cnt_bureau_active": inp.cnt_bureau_active,
            "max_dpd_days": inp.max_dpd_days, "income_type": inp.income_type,
            "contract_type": inp.contract_type,
        })
        p_default, model_error = None, None
        if model_available():
            try:
                p_default = float(score(pd.DataFrame([feat])).iloc[0])
            except Exception as exc:  # surface model/feature mismatches while the model evolves
                model_error = str(exc)
        decision = evaluate({**feat, "has_current_overdue": inp.has_current_overdue}, p_default)
        return {
            "flag": decision.flag,
            "reasons": decision.reasons,
            "p_default": p_default,
            "model_available": model_available(),
            "model_error": model_error,
            "ratios": {"debt_to_income": feat["debt_to_income"], "credit_to_income": feat["credit_to_income"]},
            "thresholds": {"p_green_max": P_GREEN_MAX, "p_red_min": P_RED_MIN},
        }

    # ---- built frontend (single-page app) -----------------------------------------------------
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        if not FRONTEND_DIST.is_dir():
            return JSONResponse({"detail": "Frontend not built. Run `npm run build` in frontend/, "
                                           "or `npm run dev` there for development."}, status_code=404)
        target = (FRONTEND_DIST / path).resolve()
        if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
