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


def compare_to_reference(value: float, ref: dict | None) -> str:
    """Ubica un valor respecto de los rangos intercuartiles de benignos y malignos."""
    if not ref:
        return "sin referencia"
    b, m = ref["benigno"], ref["maligno"]
    in_b = b["p25"] <= value <= b["p75"]
    in_m = m["p25"] <= value <= m["p75"]
    if in_b and not in_m:
        return "dentro del rango típico de benignos"
    if in_m and not in_b:
        return "dentro del rango típico de malignos"
    if in_b and in_m:
        return "en el rango compartido por benignos y malignos (no discrimina)"
    if value > max(b["p75"], m["p75"]):
        higher = "benignos" if b["p75"] > m["p75"] else "malignos"
        return f"por encima de ambos rangos típicos (del lado de los {higher})"
    if value < min(b["p25"], m["p25"]):
        lower = "benignos" if b["p25"] < m["p25"] else "malignos"
        return f"por debajo de ambos rangos típicos (del lado de los {lower})"
    closer = "benignos" if abs(value - b["mediana"]) < abs(value - m["mediana"]) else "malignos"
    return f"entre ambos rangos, más cercano a los {closer}"


def density_category(mean_hu: float) -> str:
    if mean_hu > 200:
        return (
            "mayor a 200 HU: sugiere calcificación, hallazgo clásicamente asociado a "
            "benignidad (en el entrenamiento ningún nódulo maligno superó este valor)"
        )
    if mean_hu < -300:
        return (
            "menor a −300 HU: compatible con componente en vidrio esmerilado o subsólido "
            "(o volumen parcial con parénquima en nódulos pequeños)"
        )
    return "entre −300 y 200 HU: compatible con densidad sólida"


def discordant_factors(prob: float, descriptors: list[dict], contribs: list[dict]) -> list[str]:
    """Hallazgos que apuntan en sentido contrario a la estimación del modelo."""
    predicted, opposite = ("malignos", "benignos") if prob >= 0.5 else ("benignos", "malignos")
    out = [
        f"{d['feature']}: {d['comparacion']}"
        for d in descriptors
        if opposite in d["comparacion"] and "compartido" not in d["comparacion"]
    ]
    wrong_sign = (lambda c: c < 0) if predicted == "malignos" else (lambda c: c > 0)
    out += [
        f"{c['feature']}: {c['efecto']} (en contra de la estimación final)"
        for c in contribs
        if wrong_sign(c["contribution"])
    ]
    return out


FAMILY_DOMAIN = {
    "shape": "Tamaño y forma",
    "firstorder": "Densidad e intensidad",
    "glcm": "Textura",
    "glszm": "Textura",
    "glrlm": "Textura",
    "gldm": "Textura",
    "ngtdm": "Textura",
}


def feature_domain(name: str) -> str:
    family = name.split("_")[1] if name.count("_") >= 2 else ""
    return FAMILY_DOMAIN.get(family, "Otras")


def readable_feature(name: str) -> str:
    image_type, _, rest = name.partition("_")
    family, _, feature = rest.partition("_")
    image_type = (
        image_type.replace("log-sigma-", "LoG σ=").replace("-0-mm-3D", " mm")
        .replace("wavelet-", "wavelet ").replace("original", "imagen original")
    )
    return f"{feature} ({family}, {image_type})"


def _sigmoid(v: float) -> float:
    return float(1 / (1 + np.exp(-v)))


def probability_text(prob: float) -> str:
    return "> 99 %" if prob > 0.99 else "< 1 %" if prob < 0.01 else f"{prob:.0%}".replace("%", " %")


def risk_band(prob: float) -> str:
    return "bajo" if prob < 0.30 else "intermedio" if prob < 0.70 else "alto"


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
    refs = bundle.get("reference_stats", {})
    contribs = contributions(bundle, x)
    descriptors = [
        {
            "feature": f,
            "valor_caso": float(result[f]),
            "comparacion": compare_to_reference(float(result[f]), refs.get(f)),
            "referencia": refs.get(f),
        }
        for f in bundle.get("key_descriptors", [])
        if f in result
    ]
    mean_hu = result.get("original_firstorder_Mean")
    band = risk_band(prob)
    return {
        "probability": prob,
        "probability_text": probability_text(prob),
        "risk_band": band,
        "orientation": {
            "bajo": "hallazgos compatibles con nódulo de probable naturaleza benigna",
            "intermedio": "hallazgos indeterminados; el modelo no discrimina con claridad",
            "alto": "hallazgos compatibles con nódulo de probable naturaleza maligna",
        }[band],
        "weighting": weighting(bundle, x),
        "density": density_category(float(mean_hu)) if mean_hu is not None else None,
        "contributions": contribs,
        "descriptors": descriptors,
        "discordant": discordant_factors(prob, descriptors, contribs),
        "metrics": bundle.get("metrics", {}),
    }


def weighting(bundle: dict[str, Any], x: pd.DataFrame) -> dict[str, Any] | None:
    """Cómo se compone la probabilidad: punto de partida + aporte neto de cada dominio."""
    pipe = bundle["pipeline"]
    clf = pipe[-1]
    if not hasattr(clf, "coef_"):
        return None
    z = pipe[:-1].transform(x)[0]
    names = pipe[:-1].get_feature_names_out(bundle["feature_names"])
    contrib = z * clf.coef_[0]
    intercept = float(clf.intercept_[0])
    total_abs = float(np.abs(contrib).sum()) or 1.0

    domains: dict[str, dict[str, float]] = {}
    for name, c in zip(names, contrib):
        if c == 0:
            continue
        d = domains.setdefault(feature_domain(str(name)), {"neto": 0.0, "abs": 0.0, "n": 0})
        d["neto"] += float(c)
        d["abs"] += abs(float(c))
        d["n"] += 1

    rows = sorted(
        (
            {
                "dominio": dom,
                "peso_pct": round(100 * v["abs"] / total_abs),
                "aporte_neto_logit": round(v["neto"], 2),
                "sentido": "hacia malignidad" if v["neto"] > 0 else "hacia benignidad",
                "n_features": int(v["n"]),
            }
            for dom, v in domains.items()
        ),
        key=lambda r: -r["peso_pct"],
    )
    return {
        "probabilidad_caso_promedio": probability_text(_sigmoid(intercept)),
        "n_features_modelo": int((clf.coef_[0] != 0).sum()),
        "dominios": rows,
        "explicacion": (
            "El modelo parte de la probabilidad de un nódulo con valores promedio y suma el "
            "aporte de cada característica (regresión logística). peso_pct es la proporción "
            "de la influencia total que corresponde a cada dominio en este caso."
        ),
        "nota_tamano": (
            "El modelo conservó una sola variable de forma porque varias características de "
            "textura e intensidad están fuertemente correlacionadas con el tamaño del nódulo "
            "(correlación 0,6–0,8 con el diámetro en el entrenamiento); el tamaño influye "
            "indirectamente a través de ellas."
        ),
    }


def contributions(bundle: dict[str, Any], x: pd.DataFrame, top: int = 8) -> list[dict[str, Any]]:
    """Aporte de cada feature al logit (solo modelos lineales), con valores de referencia."""
    pipe = bundle["pipeline"]
    clf = pipe[-1]
    if not hasattr(clf, "coef_"):
        return []
    z = pipe[:-1].transform(x)
    names = pipe[:-1].get_feature_names_out(bundle["feature_names"])
    contrib = z[0] * clf.coef_[0]
    refs = bundle.get("reference_stats", {})
    order = np.argsort(-np.abs(contrib))[:top]
    rows = []
    for i in order:
        if contrib[i] == 0:
            continue
        name = str(names[i])
        value = float(x.iloc[0][name])
        rows.append(
            {
                "feature": name,
                "nombre_legible": readable_feature(name),
                "dominio": feature_domain(name),
                "contribution": float(contrib[i]),
                "efecto": "aumenta la probabilidad" if contrib[i] > 0 else "disminuye la probabilidad",
                "valor_caso": value,
                "comparacion": compare_to_reference(value, refs.get(name)),
                "referencia": refs.get(name),
            }
        )
    return rows
