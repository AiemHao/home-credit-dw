"""Capture report figures (dashboard pages + architecture diagrams) with headless Chrome/Edge.

Start the app first (`hcdw serve`), then:

    python scripts/capture_figures.py                    # light theme, into reports/figures/
    python scripts/capture_figures.py --theme dark --base http://127.0.0.1:8000

Every page is loaded with ?theme=..., Architecture diagrams with ?diagram=<key>.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = [  # (file name, path, window height)
    ("dashboard_overview", "/", 1500),
    ("dashboard_portfolio", "/portfolio", 2300),
    ("dashboard_drilldown", "/drilldown", 1150),
    ("dashboard_credit_history", "/credit-history", 2300),
    ("dashboard_olap_pivot", "/olap", 950),
    ("dashboard_risk_simulator", "/simulator", 1050),
]
DIAGRAMS = [  # (file name, diagram key, window height)
    ("diagram_system_architecture", "system", 1650),
    ("diagram_etl_pipeline", "etl", 2350),
    ("diagram_star_schema", "star", 2750),
    ("diagram_data_lineage", "lineage", 1600),
    ("diagram_request_flow", "request", 1150),
    ("diagram_dss_flow", "dss", 950),
]
CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge",
]


def find_browser() -> str:
    for c in CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise SystemExit("Chrome / Edge not found; pass --browser <path>.")


def shoot(browser: str, url: str, out: Path, height: int, profile: str) -> None:
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
         f"--window-size=1440,{height}", "--virtual-time-budget=20000", f"--screenshot={out}", url],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "figures")
    ap.add_argument("--browser", default=None)
    args = ap.parse_args()

    browser = args.browser or find_browser()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        jobs = [(n, f"{p}?theme={args.theme}", h) for n, p, h in PAGES]
        jobs += [(n, f"/architecture?theme={args.theme}&diagram={k}", h) for n, k, h in DIAGRAMS]
        for name, path, height in jobs:
            out = args.out / f"{name}.png"
            shoot(browser, args.base + path, out, height, profile)
            print(f"{out.relative_to(ROOT)}  <- {path}")


if __name__ == "__main__":
    main()
