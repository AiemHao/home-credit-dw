"""Train the default-risk classifier.

    pip install -e ".[ml]"
    python -m dss.train

Baseline only (LightGBM, holdout AUC). TODO: tune, cross-validate, calibrate,
SHAP explanations, and record results in models/metrics.json for the report.
"""
from __future__ import annotations

import json

from hcdw.config import ROOT
from hcdw.db import get_conn

from dss.features import CATEGORICAL_FEATURES, FEATURES, load_frame

MODEL_DIR = ROOT / "models"


def main() -> None:
    import joblib
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    con = get_conn(read_only=True)
    df = load_frame(con, labelled=True)
    con.close()

    X, y = df[FEATURES], df["target"].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    model = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                               class_weight="balanced", random_state=42, verbose=-1)
    model.fit(X_tr, y_tr, categorical_feature=CATEGORICAL_FEATURES)
    auc = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.pkl")
    (MODEL_DIR / "metrics.json").write_text(json.dumps({"holdout_auc": round(auc, 4), "n_train": len(X_tr)}, indent=2))
    (MODEL_DIR / "feature_list.json").write_text(json.dumps(FEATURES, indent=2))
    print(f"holdout AUC = {auc:.4f}; saved to {MODEL_DIR / 'model.pkl'}")


if __name__ == "__main__":
    main()
