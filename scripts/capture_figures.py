"""Capture report figures with headless Chrome/Edge.

* Dashboard pages: screenshots of the running app (start it first with `hcdw serve`).
* Diagrams: the SVGs in docs/diagrams rendered on their own, at 2x for print.

    python scripts/capture_figures.py                    # light theme, into reports/figures/
    python scripts/capture_figures.py --theme dark --only diagrams
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = ROOT / "docs" / "diagrams"

PAGES = [  # (file name, path, window height)
    ("dashboard_overview", "/", 1500),
    ("dashboard_portfolio", "/portfolio", 2300),
    ("dashboard_drilldown", "/drilldown", 1150),
    ("dashboard_credit_history", "/credit-history", 2300),
    ("dashboard_olap_pivot", "/olap", 950),
    ("dashboard_risk_simulator", "/simulator", 1050),
    ("dashboard_architecture", "/architecture", 1250),
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


def shoot(browser: str, url: str, out: Path, width: int, height: int, profile: str, scale: int = 1) -> None:
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
         f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
         "--virtual-time-budget=20000", f"--screenshot={out}", url],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120,
    )


def capture_diagrams(browser: str, theme: str, out_dir: Path, profile: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for svg in sorted(DIAGRAM_DIR.glob("*.svg")):
            text = svg.read_text(encoding="utf-8")
            m = re.search(r'viewBox="0 0 (\d+) (\d+)"', text)
            w, h = (int(m.group(1)), int(m.group(2))) if m else (1240, 800)
            # data-theme on <html> selects the diagram's light/dark tokens regardless of the OS setting
            page = Path(tmp) / f"{svg.stem}.html"
            page.write_text(f'<!doctype html><html data-theme="{theme}"><body style="margin:0">{text}</body></html>',
                            encoding="utf-8")
            out = out_dir / f"diagram_{svg.stem[3:]}.png"
            shoot(browser, page.as_uri(), out, w, h, profile, scale=2)
            print(f"{out.relative_to(ROOT)}  <- docs/diagrams/{svg.name}")


def capture_pages(browser: str, base: str, theme: str, out_dir: Path, profile: str) -> None:
    for name, path, height in PAGES:
        out = out_dir / f"{name}.png"
        shoot(browser, f"{base}{path}?theme={theme}", out, 1440, height, profile)
        print(f"{out.relative_to(ROOT)}  <- {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--only", choices=["pages", "diagrams"], default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "figures")
    ap.add_argument("--browser", default=None)
    args = ap.parse_args()

    browser = args.browser or find_browser()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        if args.only in (None, "diagrams"):
            capture_diagrams(browser, args.theme, args.out, profile)
        if args.only in (None, "pages"):
            capture_pages(browser, args.base, args.theme, args.out, profile)


if __name__ == "__main__":
    main()
