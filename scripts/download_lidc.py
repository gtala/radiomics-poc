"""
Descarga un subconjunto balanceado de LIDC-IDRI desde TCIA.

Requiere haber corrido antes `python -m scripts.lidc_catalog`.
Estructura de salida (la que espera pylidc):
    data/lidc/<patient_id>/<SeriesInstanceUID>/*.dcm

Uso:
    python -m scripts.download_lidc --per-class 60
    python -m scripts.download_lidc --per-class 1   # prueba rápida
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd
from tcia_utils import nbia

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "outputs" / "lidc_nodules.csv"
SELECTION = ROOT / "outputs" / "lidc_selection.csv"
DICOM_DIR = ROOT / "data" / "lidc"

MAX_SLICE_THICKNESS = 2.5
SEED = 42


def select_patients(per_class: int) -> pd.DataFrame:
    df = pd.read_csv(CATALOG)
    ok = df[df["eligible"] & (df["slice_thickness"] <= MAX_SLICE_THICKNESS)]
    by_patient = ok.groupby(["patient_id", "series_uid"])["label"].agg(set).reset_index()
    by_patient["group"] = by_patient["label"].map(
        lambda s: "maligno" if "maligno" in s else "benigno"
    )
    picked = [
        by_patient[by_patient["group"] == g].sample(
            n=min(per_class, int((by_patient["group"] == g).sum())), random_state=SEED
        )
        for g in ("maligno", "benigno")
    ]
    return pd.concat(picked)[["patient_id", "series_uid", "group"]].sort_values("patient_id")


def already_downloaded(patient_dir: Path, series_uid: str) -> bool:
    series_dir = patient_dir / series_uid
    return series_dir.is_dir() and any(series_dir.iterdir())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=60)
    args = parser.parse_args()

    sel = select_patients(args.per_class)
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    sel.to_csv(SELECTION, index=False)
    print(f"Seleccionados: {len(sel)} pacientes ({sel['group'].value_counts().to_dict()})")

    for i, row in enumerate(sel.itertuples(), 1):
        patient_dir = DICOM_DIR / row.patient_id
        if already_downloaded(patient_dir, row.series_uid):
            print(f"[{i}/{len(sel)}] {row.patient_id} ya descargado")
            continue
        patient_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{i}/{len(sel)}] {row.patient_id} descargando…", flush=True)
        try:
            nbia.downloadSeries([row.series_uid], input_type="list", path=str(patient_dir))
        except Exception as exc:  # noqa: BLE001
            print(f"   error: {exc}")
            shutil.rmtree(patient_dir / row.series_uid, ignore_errors=True)

    total = sum(f.stat().st_size for f in DICOM_DIR.rglob("*") if f.is_file())
    print(f"Listo. Tamaño en disco: {total / 1e9:.1f} GB en {DICOM_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
