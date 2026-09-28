"""Interpretación académica asistida de características radiómicas (no diagnóstico)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

NODULE_REPORT_PROMPT = (Path(__file__).parent / "prompts" / "informe_nodulo.md").read_text(
    encoding="utf-8"
)


SYSTEM_PROMPT = """Eres un asistente académico que explica características radiómicas
extraídas de estudios de tomografía computada (CT) y una región de interés (ROI)
segmentada. Redactas en español formal, claro y preciso, orientado a médicos e
investigadores en formación.

REGLAS OBLIGATORIAS:
- Contexto educativo / investigación. NO diagnostiques (no afirmes cáncer, benignidad,
  malignidad, metástasis ni indiques tratamiento).
- NO emitas recomendaciones clínicas ni concluyas sobre el estado del paciente.
- Explica qué miden las métricas (morfología, intensidades en HU, textura) en términos
  cuantitativos y descriptivos (tamaño relativo, esfericidad, homogeneidad, etc.).
- Refiérete a la región analizada como ROI o lesión segmentada, sin asumir un órgano
  específico salvo que los datos lo indiquen.
- Si faltan datos, indícalo; no inventes valores.
- Cierra siempre con: "Este texto es orientativo y no constituye un informe médico ni un diagnóstico."
"""


def features_for_llm(result: dict[str, Any], max_original: int = 40) -> dict[str, Any]:
    """Subset compacto: resumen + algunas original_* numéricas."""
    summary_keys = [
        "original_shape_MeshVolume",
        "original_shape_VoxelVolume",
        "original_shape_SurfaceArea",
        "original_shape_Maximum3DDiameter",
        "original_shape_MajorAxisLength",
        "original_shape_MinorAxisLength",
        "original_shape_Sphericity",
        "original_shape_Elongation",
        "original_shape_Flatness",
        "original_firstorder_Mean",
        "original_firstorder_Median",
        "original_firstorder_Minimum",
        "original_firstorder_Maximum",
        "original_firstorder_Range",
        "original_firstorder_Entropy",
        "original_firstorder_Skewness",
        "original_firstorder_Kurtosis",
        "original_glcm_Contrast",
        "original_glcm_Correlation",
        "original_glcm_Idm",
        "original_glcm_JointEntropy",
    ]
    summary: dict[str, float] = {}
    for k in summary_keys:
        if k not in result:
            continue
        try:
            summary[k] = float(result[k])
        except (TypeError, ValueError):
            continue

    original: dict[str, float] = {}
    for k, v in result.items():
        if not k.startswith("original_") or k.startswith("diagnostics_"):
            continue
        if k in summary:
            continue
        try:
            original[k] = float(v)
        except (TypeError, ValueError):
            continue
        if len(original) >= max_original:
            break

    n_feat = sum(
        1
        for k in result
        if not k.startswith("diagnostics_")
    )
    return {
        "n_features_total": n_feat,
        "summary": summary,
        "sample_other_original": original,
        "note": "Características PyRadiomics sobre ROI (label indicado) en volumen CT.",
    }


def _secret_or_env(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return default


def api_key_configured() -> bool:
    return bool(_secret_or_env("OPENAI_API_KEY"))


def interpret_radiomics(
    result: dict[str, Any],
    *,
    prediction: dict[str, Any] | None = None,
    model: str | None = None,
) -> str:
    """
    Llama a la API de OpenAI.
    Key: variable de entorno OPENAI_API_KEY, o st.secrets en Streamlit Cloud.
    """
    key = _secret_or_env("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "La interpretación asistida no está configurada en este entorno."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Dependencia de interpretación no disponible en el entorno."
        ) from exc

    payload = features_for_llm(result)
    if prediction:
        system_prompt = NODULE_REPORT_PROMPT
        payload["modelo_probabilidad"] = {
            "probabilidad_texto": prediction.get("probability_text"),
            "categoria": prediction.get("risk_band"),
            "probabilidad_malignidad": round(prediction["probability"], 3),
            "densidad_categoria": prediction.get("density"),
            "features_mas_influyentes": prediction["contributions"],
            "descriptores_clave": prediction.get("descriptors", []),
            "factores_discordantes": prediction.get("discordant", []),
            "metricas_validacion": prediction["metrics"],
        }
        instruction = (
            "Elabore el informe académico del siguiente nódulo pulmonar según la "
            "estructura indicada:\n\n"
        )
    else:
        system_prompt = SYSTEM_PROMPT
        instruction = (
            "Elabore una interpretación académica de las siguientes "
            "características radiómicas de una ROI en CT. Describa solo "
            "métricas cuantitativas; no diagnostique:\n\n"
        )
    client = OpenAI(api_key=key)
    if prediction:
        used_model = model or _secret_or_env("OPENAI_REPORT_MODEL", "gpt-4o")
    else:
        used_model = model or _secret_or_env("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=used_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": instruction + json.dumps(payload, ensure_ascii=False, indent=2),
            },
        ],
    )
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("No se obtuvo respuesta del servicio de interpretación.")
    return text.strip()
