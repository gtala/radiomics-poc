"""Genera models/referencia_nodulos.json a partir de outputs/features.parquet.

Uso: .venv/bin/python -m scripts.build_reference
"""

from __future__ import annotations

import json

import pandas as pd

from app.profile_view import REFERENCE_PATH, build_reference

df = pd.read_parquet("outputs/features.parquet")
reference = build_reference(df, df["label"])
reference["fuente"] = "LIDC-IDRI (nódulos del entrenamiento del modelo)"
REFERENCE_PATH.write_text(json.dumps(reference, ensure_ascii=False), encoding="utf-8")
print(f"{REFERENCE_PATH}: {reference['n']} nódulos, {len(reference['features'])} características")
