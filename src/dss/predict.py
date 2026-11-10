"""Load the trained model and score applications."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from dss.features import FEATURES, prepare
from dss.train import MODEL_DIR


def model_available() -> bool:
    return (MODEL_DIR / "model.pkl").exists()


@lru_cache(maxsize=1)
def load_model():
    import joblib

    return joblib.load(MODEL_DIR / "model.pkl")


def score(df: pd.DataFrame) -> pd.Series:
    """Probability of default for each row (columns = dss.features.FEATURES)."""
    model = load_model()
    X = prepare(df)[FEATURES]
    # TODO: align categorical levels with the training data
    # (model.booster_.pandas_categorical) so single-row what-if inputs score correctly.
    return pd.Series(model.predict_proba(X)[:, 1], index=df.index, name="p_default")
