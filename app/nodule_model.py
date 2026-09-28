"""Modelo de probabilidad de malignidad de nódulo a partir de features radiómicas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "modelo_nodulo.joblib"


class CorrelationFilter(BaseEstimator, TransformerMixin):
    """Elimina features con correlación absoluta mayor al umbral (se queda con la primera)."""

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold

    def fit(self, X, y=None):
        corr = np.abs(np.corrcoef(np.asarray(X, dtype=float), rowvar=False))
        corr = np.nan_to_num(corr)
        keep: list[int] = []
        for j in range(corr.shape[0]):
            if all(corr[j, k] <= self.threshold for k in keep):
                keep.append(j)
        self.keep_ = np.array(keep)
        return self

    def transform(self, X):
        return np.asarray(X, dtype=float)[:, self.keep_]

    def get_feature_names_out(self, input_features=None):
        names = np.asarray(input_features) if input_features is not None else self.feature_names_in_
        return names[self.keep_]


def model_available() -> bool:
    return MODEL_PATH.exists()


def load_model() -> dict[str, Any]:
    return joblib.load(MODEL_PATH)


def predict_malignancy(result: dict[str, Any], bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Probabilidad de malignidad y contribución de las features principales."""
    bundle = bundle or load_model()
    names = bundle["feature_names"]
    missing = [n for n in names if n not in result]
    if missing:
        raise ValueError(
            f"Faltan {len(missing)} características requeridas por el modelo "
            f"(p. ej. {missing[0]}). Verifique la configuración de PyRadiomics."
        )
    x = pd.DataFrame([[float(result[n]) for n in names]], columns=names)
    prob = float(bundle["pipeline"].predict_proba(x)[0, 1])
    return {
        "probability": prob,
        "contributions": contributions(bundle, x),
        "metrics": bundle.get("metrics", {}),
    }


def contributions(bundle: dict[str, Any], x: pd.DataFrame, top: int = 8) -> list[dict[str, Any]]:
    """Aporte de cada feature al logit (solo modelos lineales)."""
    pipe = bundle["pipeline"]
    clf = pipe[-1]
    if not hasattr(clf, "coef_"):
        return []
    z = pipe[:-1].transform(x)
    names = pipe[:-1].get_feature_names_out(bundle["feature_names"])
    contrib = z[0] * clf.coef_[0]
    order = np.argsort(-np.abs(contrib))[:top]
    return [
        {"feature": str(names[i]), "contribution": float(contrib[i])}
        for i in order
        if contrib[i] != 0
    ]
