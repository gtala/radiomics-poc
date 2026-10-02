"""Perfil visual del caso: cada característica como percentil respecto de nódulos de referencia."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "models" / "referencia_nodulos.json"

# (feature, nombre legible, dominio, qué indica un valor alto, qué indica un valor bajo)
PROFILE_FEATURES = [
    ("original_shape_Maximum3DDiameter", "Diámetro máximo", "Tamaño y forma", "nódulo grande", "nódulo pequeño"),
    ("original_shape_MeshVolume", "Volumen", "Tamaño y forma", "nódulo voluminoso", "nódulo de poco volumen"),
    ("original_shape_Sphericity", "Esfericidad", "Tamaño y forma", "forma esférica, contorno regular", "contorno irregular o lobulado"),
    ("original_shape_Elongation", "Elongación (1 = no elongado)", "Tamaño y forma", "poco elongado", "marcadamente elongado"),
    ("original_shape_Flatness", "Aplanamiento (1 = no aplanado)", "Tamaño y forma", "poco aplanado", "marcadamente aplanado"),
    ("original_shape_SurfaceVolumeRatio", "Superficie / volumen", "Tamaño y forma", "nódulo pequeño o irregular", "nódulo grande y compacto"),
    ("original_firstorder_Mean", "Densidad media (HU)", "Densidad", "denso; valores muy altos sugieren calcificación", "poco denso, posible componente subsólido"),
    ("original_firstorder_10Percentile", "Densidad baja, P10 (HU)", "Densidad", "sin componente hipodenso", "componente hipodenso o en vidrio esmerilado"),
    ("original_firstorder_Maximum", "Densidad máxima (HU)", "Densidad", "focos muy densos", "sin focos densos"),
    ("original_firstorder_Entropy", "Heterogeneidad (entropía)", "Densidad", "densidades heterogéneas", "densidades homogéneas"),
    ("original_firstorder_Skewness", "Asimetría del histograma", "Densidad", "cola hacia densidades altas", "cola hacia densidades bajas"),
    ("original_glcm_Idm", "Homogeneidad local", "Textura", "textura uniforme", "textura poco uniforme"),
    ("original_glcm_Contrast", "Contraste local", "Textura", "cambios bruscos entre vóxeles vecinos", "transiciones suaves entre vóxeles vecinos"),
    ("original_glcm_Imc2", "Estructura de la textura", "Textura", "textura organizada o predecible", "textura poco organizada"),
    ("original_glszm_ZonePercentage", "Fineza de la textura", "Textura", "textura fina, muchas zonas pequeñas", "grandes regiones homogéneas"),
    ("original_glszm_SmallAreaEmphasis", "Predominio de zonas pequeñas", "Textura", "predominan zonas pequeñas", "predominan zonas grandes"),
    ("original_glrlm_LongRunEmphasis", "Textura gruesa", "Textura", "regiones homogéneas extensas", "textura fina"),
    ("original_gldm_DependenceVariance", "Variabilidad de regiones homogéneas", "Textura", "regiones de tamaños muy variables", "regiones de tamaño similar"),
]


def build_reference(df: pd.DataFrame, labels: pd.Series) -> dict[str, Any]:
    """Valores de referencia por característica (todos y por clase), para guardar como JSON."""
    out: dict[str, Any] = {"n": int(len(df)), "features": {}}
    for key, *_rest in PROFILE_FEATURES:
        if key not in df:
            continue
        vals = df[key].astype(float)
        out["features"][key] = {
            "todos": sorted(round(v, 6) for v in vals),
            "benigno": [round(float(np.percentile(vals[labels == "benigno"], q)), 6) for q in (25, 50, 75)],
            "maligno": [round(float(np.percentile(vals[labels == "maligno"], q)), 6) for q in (25, 50, 75)],
        }
    return out


def reference_available() -> bool:
    return REFERENCE_PATH.exists()


def load_reference() -> dict[str, Any]:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def _percentile(sorted_vals: np.ndarray, v: float) -> float:
    left = np.searchsorted(sorted_vals, v, side="left")
    right = np.searchsorted(sorted_vals, v, side="right")
    return float(100 * (left + right) / 2 / len(sorted_vals))


def profile_frame(result: dict[str, Any], reference: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for order, (key, label, domain, high_means, low_means) in enumerate(PROFILE_FEATURES):
        ref = reference["features"].get(key)
        if ref is None or key not in result:
            continue
        allv = np.asarray(ref["todos"], dtype=float)
        value = float(result[key])
        b25, b50, b75 = (_percentile(allv, v) for v in ref["benigno"])
        m25, m50, m75 = (_percentile(allv, v) for v in ref["maligno"])
        rows.append(
            {
                "orden": order,
                "caracteristica": label,
                "dominio": domain,
                "valor": value,
                "percentil": round(_percentile(allv, value), 1),
                "benigno_p25": b25, "benigno_p50": b50, "benigno_p75": b75,
                "maligno_p25": m25, "maligno_p50": m50, "maligno_p75": m75,
                "alto_significa": high_means,
                "bajo_significa": low_means,
            }
        )
    return pd.DataFrame(rows)


def report_findings(result: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    """Comparación de cada característica con los valores típicos de benignos y malignos."""
    frame = profile_frame(result, reference)
    out = []
    for r in frame.sort_values("orden").itertuples():
        ref = reference["features"][PROFILE_FEATURES[r.orden][0]]
        lo, hi = ref["todos"][0], ref["todos"][-1]
        d_b, d_m = abs(r.percentil - r.benigno_p50), abs(r.percentil - r.maligno_p50)
        if abs(d_b - d_m) < 10:
            parecido = "similar a ambos grupos"
        else:
            parecido = "más parecido a benignos" if d_b < d_m else "más parecido a malignos"
        fuera = None
        if r.valor > hi:
            fuera = f"mayor que todos los nódulos de referencia (máximo {hi:.4g})"
        elif r.valor < lo:
            fuera = f"menor que todos los nódulos de referencia (mínimo {lo:.4g})"
        out.append(
            {
                "caracteristica": r.caracteristica,
                "dominio": r.dominio,
                "valor_caso": round(r.valor, 4),
                "mediana_benignos": round(ref["benigno"][1], 4),
                "mediana_malignos": round(ref["maligno"][1], 4),
                "percentil": r.percentil,
                "comparacion": parecido,
                "fuera_de_rango": fuera,
                "valor_alto_indica": r.alto_significa,
                "valor_bajo_indica": r.bajo_significa,
            }
        )
    return out


def highlights(frame: pd.DataFrame, low: float = 10, high: float = 90) -> list[str]:
    """Frases de lectura rápida para los valores extremos."""
    out = []
    for r in frame.sort_values("orden").itertuples():
        if r.percentil >= high:
            out.append(
                f"**{r.caracteristica}**: mayor que el {r.percentil:.0f} % de los nódulos de "
                f"referencia ({r.alto_significa})."
            )
        elif r.percentil <= low:
            out.append(
                f"**{r.caracteristica}**: menor que el {100 - r.percentil:.0f} % de los nódulos "
                f"de referencia ({r.bajo_significa})."
            )
    return out


DOMAIN_ORDER = ["Tamaño y forma", "Densidad", "Textura"]


def profile_chart(frame: pd.DataFrame):
    import altair as alt

    charts = [
        _domain_chart(frame[frame["dominio"] == d], d, show_axis=(i == len(DOMAIN_ORDER) - 1))
        for i, d in enumerate(DOMAIN_ORDER)
        if (frame["dominio"] == d).any()
    ]
    return alt.vconcat(*charts, spacing=18).resolve_scale(color="shared")


def _domain_chart(frame: pd.DataFrame, domain: str, show_axis: bool):
    import altair as alt

    base = alt.Chart(frame).encode(
        y=alt.Y(
            "caracteristica:N",
            sort=alt.SortField("orden"),
            title=None,
            axis=alt.Axis(labelLimit=260),
        )
    )
    x_scale = alt.Scale(domain=[0, 100])
    x_axis = alt.Axis(title="Percentil respecto de los nódulos de referencia") if show_axis else alt.Axis(
        title=None, labels=False
    )
    benign = base.mark_bar(size=5, yOffset=-5, color="#2e9d5b", opacity=0.55).encode(
        x=alt.X("benigno_p25:Q", scale=x_scale, axis=x_axis),
        x2="benigno_p75:Q",
        tooltip=[alt.Tooltip("caracteristica:N", title="Característica")],
    )
    malignant = base.mark_bar(size=5, yOffset=5, color="#d9433b", opacity=0.55).encode(
        x=alt.X("maligno_p25:Q", scale=x_scale),
        x2="maligno_p75:Q",
    )
    point = base.mark_circle(size=260, stroke="white", strokeWidth=1.5, opacity=1).encode(
        x=alt.X("percentil:Q", scale=x_scale),
        color=alt.Color(
            "percentil:Q",
            scale=alt.Scale(scheme="redblue", reverse=True, domain=[0, 100]),
            legend=alt.Legend(title="Percentil"),
        ),
        tooltip=[
            alt.Tooltip("caracteristica:N", title="Característica"),
            alt.Tooltip("valor:Q", title="Valor del caso", format=".3~f"),
            alt.Tooltip("percentil:Q", title="Percentil"),
            alt.Tooltip("alto_significa:N", title="Valor alto indica"),
            alt.Tooltip("bajo_significa:N", title="Valor bajo indica"),
        ],
    )
    text = base.mark_text(align="left", dx=12, fontSize=11, color="#bbbbbb").encode(
        x=alt.X("percentil:Q", scale=x_scale),
        text=alt.Text("percentil:Q", format=".0f"),
    )
    return alt.layer(benign, malignant, point, text).properties(
        title=alt.TitleParams(domain, anchor="start", fontSize=14),
        height=30 * len(frame),
        width="container",
    )
