"""Build data/sample/: a stratified subset of applicants plus every child row that belongs to them.

The sample keeps the original Kaggle file names and columns, so `hcdw etl --source sample`
runs exactly the same pipeline as the full dataset (this is what we submit in data/).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import duckdb
import pandas as pd

from hcdw.db import sql_literal_path
from hcdw.etl.extract import find_source_file

CHILD_BY_CURR = ["bureau", "previous_application", "installments_payments", "POS_CASH_balance",
                 "credit_card_balance"]


def build_sample(raw_dir: Path, out_dir: Path, n_customers: int, test_share: float, seed: int,
                 compress: bool = True) -> dict[str, int]:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    ext = ".csv.gz" if compress else ".csv"
    opts = "HEADER, DELIMITER ','" + (", COMPRESSION gzip" if compress else "")

    def src(stem: str) -> Path | None:
        return find_source_file(raw_dir, stem)

    train = src("application_train")
    if train is None:
        raise FileNotFoundError(f"application_train.csv not found in {raw_dir}")
    test = src("application_test")

    n_test = int(round(n_customers * test_share)) if test is not None else 0
    n_train = n_customers - n_test

    labels = con.execute(
        f"SELECT SK_ID_CURR, TARGET FROM read_csv({sql_literal_path(train)}, header = true)"
    ).df()
    frac = min(1.0, n_train / len(labels))
    picked = labels.groupby("TARGET", group_keys=False).sample(frac=frac, random_state=seed)
    ids = [picked["SK_ID_CURR"]]
    if n_test:
        test_ids = con.execute(
            f"SELECT SK_ID_CURR FROM read_csv({sql_literal_path(test)}, header = true)"
        ).df()
        ids.append(test_ids.sample(n=min(n_test, len(test_ids)), random_state=seed)["SK_ID_CURR"])
    con.register("ids", pd.DataFrame({"sk_id_curr": pd.concat(ids).astype("int64")}))

    counts: dict[str, int] = {}

    def copy(stem: str, where: str) -> None:
        path = src(stem)
        if path is None:
            return
        target = out_dir / f"{stem}{ext}"
        con.execute(
            f"COPY (SELECT * FROM read_csv({sql_literal_path(path)}, header = true, all_varchar = true) "
            f"WHERE {where}) TO {sql_literal_path(target)} ({opts})"
        )
        counts[stem] = con.execute(
            f"SELECT COUNT(*) FROM read_csv({sql_literal_path(target)}, header = true, all_varchar = true)"
        ).fetchone()[0]

    in_ids = "CAST(SK_ID_CURR AS BIGINT) IN (SELECT sk_id_curr FROM ids)"
    for stem in ["application_train", "application_test", *CHILD_BY_CURR]:
        copy(stem, in_ids)

    bureau = src("bureau")
    if bureau is not None:
        copy("bureau_balance",
             f"SK_ID_BUREAU IN (SELECT SK_ID_BUREAU FROM read_csv({sql_literal_path(bureau)}, "
             f"header = true, all_varchar = true) WHERE {in_ids})")

    desc = raw_dir / "HomeCredit_columns_description.csv"
    if desc.exists():
        shutil.copy2(desc, out_dir / desc.name)
    con.close()
    return counts
