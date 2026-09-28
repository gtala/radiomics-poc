"""
Extracción en lote de características radiómicas de los nódulos LIDC-IDRI descargados.

Usa la misma configuración PyRadiomics que la app, para que el modelo entrenado
reciba en producción las mismas features.

Salida:
    outputs/features/<patient_id>.parquet   (parcial por paciente, permite retomar)
    outputs/features.parquet                (tabla final, una fila por nódulo)

Uso:
    python -m scripts.extract_lidc --workers 6
"""

from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "outputs" / "lidc_nodules.csv"
SELECTION = ROOT / "outputs" / "lidc_selection.csv"
PARTIAL_DIR = ROOT / "outputs" / "features"
FEATURES = ROOT / "outputs" / "features.parquet"
CONFIG = ROOT / "data" / "CT_config.yaml"
if not CONFIG.exists():
    CONFIG = ROOT / "config" / "exampleCT.yaml"

META_COLS = [
    "patient_id",
    "series_uid",
    "nodule_idx",
    "label",
    "malignancy_median",
    "n_readers",
    "diameter_mm",
    "slice_thickness",
]


def _scan_to_sitk(scan) -> tuple[sitk.Image, np.ndarray]:
    vol = scan.to_volume(verbose=False)
    image = sitk.GetImageFromArray(vol.transpose(2, 0, 1).astype(np.int16))
    image.SetSpacing(
        (float(scan.pixel_spacing), float(scan.pixel_spacing), float(scan.slice_spacing))
    )
    return image, vol


def process_patient(series_uid: str, nodules: list[dict]) -> Path:
    from app.radiomics_service import extract_features_from_images
    from pylidc.utils import consensus
    from scripts.lidc_compat import pl

    scan = pl.query(pl.Scan).filter(pl.Scan.series_instance_uid == series_uid).first()
    image, vol = _scan_to_sitk(scan)
    clusters = scan.cluster_annotations(verbose=False)

    rows = []
    for nod in nodules:
        cluster = clusters[int(nod["nodule_idx"])]
        cmask, bbox, _ = consensus(cluster, clevel=0.5, pad=[(0, 0), (0, 0), (0, 0)])
        full = np.zeros(vol.shape, dtype=np.uint8)
        full[bbox] = cmask.astype(np.uint8)
        mask = sitk.GetImageFromArray(full.transpose(2, 0, 1))
        mask.CopyInformation(image)
        row = {c: nod[c] for c in META_COLS}
        try:
            result = extract_features_from_images(image, mask, CONFIG, label=1)
            for k, v in result.items():
                if k.startswith("diagnostics_"):
                    continue
                try:
                    row[k] = float(v)
                except (TypeError, ValueError):
                    pass
            row["error"] = ""
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)
        rows.append(row)

    out = PARTIAL_DIR / f"{nodules[0]['patient_id']}.parquet"
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()

    catalog = pd.read_csv(CATALOG)
    selection = pd.read_csv(SELECTION)
    nodules = catalog[catalog["eligible"] & catalog["series_uid"].isin(selection["series_uid"])]
    downloaded = {p.parent.parent.name for p in (ROOT / "data" / "lidc").glob("*/*/.complete")}
    nodules = nodules[nodules["patient_id"].isin(downloaded)]

    PARTIAL_DIR.mkdir(parents=True, exist_ok=True)
    pending = {
        uid: grp.to_dict("records")
        for uid, grp in nodules.groupby("series_uid")
        if not (PARTIAL_DIR / f"{grp['patient_id'].iloc[0]}.parquet").exists()
    }
    print(f"Nódulos: {len(nodules)} · pacientes pendientes: {len(pending)} · workers: {args.workers}")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_patient, uid, nods): uid for uid, nods in pending.items()}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                print(f"[{i}/{len(futures)}] {fut.result().stem}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}/{len(futures)}] error en {futures[fut]}: {exc}", flush=True)

    parts = [pd.read_parquet(p) for p in sorted(PARTIAL_DIR.glob("*.parquet"))]
    df = pd.concat(parts, ignore_index=True)
    df.to_parquet(FEATURES, index=False)
    ok = df[df["error"] == ""]
    print(f"Listo: {len(ok)} nódulos con features ({len(df) - len(ok)} con error)")
    print(ok["label"].value_counts().to_string())
    print(f"Tabla: {FEATURES.relative_to(ROOT)} · {ok.shape[1] - len(META_COLS) - 1} features")


if __name__ == "__main__":
    main()
