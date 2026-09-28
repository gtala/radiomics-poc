"""
Descarga un subconjunto balanceado de LIDC-IDRI desde TCIA.

Requiere haber corrido antes `python -m scripts.lidc_catalog`.
Estructura de salida (la que espera pylidc):
    data/lidc/<patient_id>/<SeriesInstanceUID>/*.dcm

Uso:
    python -m scripts.download_lidc --per-class 60 --parallel 6
    python -m scripts.download_lidc --per-class 1   # prueba rápida
"""

from __future__ import annotations

import argparse
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
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


COMPLETE_MARKER = ".complete"


def already_downloaded(patient_dir: Path, series_uid: str) -> bool:
    return (patient_dir / series_uid / COMPLETE_MARKER).exists()


def download_one(patient_id: str, series_uid: str) -> str:
    patient_dir = DICOM_DIR / patient_id
    series_dir = patient_dir / series_uid
    shutil.rmtree(series_dir, ignore_errors=True)
    patient_dir.mkdir(parents=True, exist_ok=True)
    nbia.downloadSeries([series_uid], input_type="list", path=str(patient_dir))
    if not series_dir.is_dir() or not any(series_dir.glob("*.dcm")):
        shutil.rmtree(series_dir, ignore_errors=True)
        raise RuntimeError("la serie no se descargó")
    (series_dir / COMPLETE_MARKER).touch()
    return patient_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=60)
    parser.add_argument("--parallel", type=int, default=6)
    args = parser.parse_args()

    sel = select_patients(args.per_class)
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    sel.to_csv(SELECTION, index=False)
    print(f"Seleccionados: {len(sel)} pacientes ({sel['group'].value_counts().to_dict()})")

    pending = [
        r for r in sel.itertuples()
        if not already_downloaded(DICOM_DIR / r.patient_id, r.series_uid)
    ]
    print(f"Pendientes: {len(pending)} · descargas en paralelo: {args.parallel}", flush=True)

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(download_one, r.patient_id, r.series_uid): r.patient_id
            for r in pending
        }
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                print(f"[{i}/{len(futures)}] {fut.result()} listo", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}/{len(futures)}] {futures[fut]} error: {exc}", flush=True)

    total = sum(f.stat().st_size for f in DICOM_DIR.rglob("*") if f.is_file())
    print(f"Listo. Tamaño en disco: {total / 1e9:.1f} GB en {DICOM_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
