"""
Catálogo de nódulos de LIDC-IDRI a partir de las anotaciones de pylidc
(no requiere imágenes descargadas).

Criterios (docs/plan-modelo.md, Etapa 2):
- nódulo marcado por >= 2 radiólogos
- etiqueta por mediana de malignidad: 1-2 benigno, 4-5 maligno, 3 excluido
- diámetro >= 3 mm

Uso:
    python -m scripts.lidc_catalog
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

from scripts.lidc_compat import pl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "lidc_nodules.csv"

MIN_READERS = 2
MIN_DIAMETER_MM = 3.0


def label_from_malignancy(median: float) -> str | None:
    if median <= 2:
        return "benigno"
    if median >= 4:
        return "maligno"
    return None


def build_catalog() -> pd.DataFrame:
    rows = []
    for scan in pl.query(pl.Scan).all():
        for idx, cluster in enumerate(scan.cluster_annotations(verbose=False)):
            median = statistics.median(a.malignancy for a in cluster)
            diameter = statistics.median(a.diameter for a in cluster)
            rows.append(
                {
                    "patient_id": scan.patient_id,
                    "series_uid": scan.series_instance_uid,
                    "scan_id": scan.id,
                    "nodule_idx": idx,
                    "n_readers": len(cluster),
                    "malignancy_median": median,
                    "diameter_mm": round(diameter, 2),
                    "slice_thickness": scan.slice_thickness,
                    "label": label_from_malignancy(median),
                }
            )
    df = pd.DataFrame(rows)
    df["eligible"] = (
        (df["n_readers"] >= MIN_READERS)
        & (df["diameter_mm"] >= MIN_DIAMETER_MM)
        & df["label"].notna()
    )
    return df


def main() -> None:
    df = build_catalog()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    ok = df[df["eligible"]]
    print(f"Nódulos totales: {len(df)} · elegibles: {len(ok)}")
    print(ok["label"].value_counts().to_string())
    print(f"Pacientes con nódulos elegibles: {ok['patient_id'].nunique()}")
    print("\nEspesor de corte (nódulos elegibles):")
    print(ok["slice_thickness"].value_counts().sort_index().to_string())
    print(f"\nCatálogo guardado en {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
