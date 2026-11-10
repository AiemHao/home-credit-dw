"""Project settings: configs/settings.yaml + .env (environment variables win)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def find_root() -> Path:
    """Repo root = first parent holding pyproject.toml and configs/ (override with HCDW_ROOT)."""
    env = os.getenv("HCDW_ROOT")
    if env:
        return Path(env).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "configs").is_dir():
            return parent
    return Path.cwd()


ROOT = find_root()
SQL_DIR = ROOT / "src" / "sql"


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any] = field(repr=False)
    dw_target: str
    dw_path: Path
    raw_dir: Path
    sample_dir: Path
    fixture_dir: Path
    dq_report: Path
    md_database: str
    motherduck_token: str | None

    @property
    def anchor_date(self) -> str:
        return str(self.raw["time"]["anchor_date"])

    @property
    def sql_params(self) -> dict[str, str]:
        """Values substituted into {{placeholders}} in src/sql/*.sql."""
        t = self.raw["time"]
        return {
            "anchor_date": str(t["anchor_date"]),
            "history_days": str(int(t["history_days"])),
            "future_days": str(int(t["future_days"])),
        }

    def bucket(self, name: str) -> tuple[list[float], list[str]]:
        b = self.raw["buckets"][name]
        return [float(e) for e in b["edges"]], list(b["labels"])


def _path(value: str | os.PathLike) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    with open(ROOT / "configs" / "settings.yaml", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    paths = raw["paths"]
    return Settings(
        raw=raw,
        dw_target=os.getenv("DW_TARGET", "local").strip().lower(),
        dw_path=_path(os.getenv("DW_PATH", paths["dw_path"])),
        raw_dir=_path(os.getenv("RAW_DIR", paths["raw_dir"])),
        sample_dir=_path(paths["sample_dir"]),
        fixture_dir=_path(paths["fixture_dir"]),
        dq_report=_path(paths["dq_report"]),
        md_database=os.getenv("MD_DATABASE", "home_credit_dw"),
        motherduck_token=os.getenv("MOTHERDUCK_TOKEN") or None,
    )
