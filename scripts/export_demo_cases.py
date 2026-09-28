"""
Exporta casos de demostración de LIDC-IDRI que NO se usaron para entrenar el modelo.

Por cada caso guarda el volumen CT y la máscara del nódulo en NIfTI, listos para
subir a la app:
    data/demo/<patient_id>_<etiqueta>_ct.nii.gz
    data/demo/<patient_id>_<etiqueta>_mascara.nii.gz

Uso:
    python -m scripts.export_demo_cases --per-class 2
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

from scripts.download_lidc import CATALOG, MAX_SLICE_THICKNESS, SELECTION, download_one
from scripts.lidc_compat import pl

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
SEED = 7


def pick_cases(per_class: int) -> pd.DataFrame:
    cat = pd.read_csv(CATALOG)
    used = set(pd.read_csv(SELECTION)["patient_id"])
    ok = cat[
        cat["eligible"]
        & (cat["slice_thickness"] <= MAX_SLICE_THICKNESS)
        & ~cat["patient_id"].isin(used)
        & (cat["n_readers"] >= 3)
    ]
    clear = ok[(ok["malignancy_median"] <= 1.5) | (ok["malignancy_median"] >= 4.5)]
    clear = clear.drop_duplicates("patient_id")
    picked = [
        clear[clear["label"] == label].sample(per_class, random_state=SEED)
        for label in ("benigno", "maligno")
    ]
    return pd.concat(picked, ignore_index=True)


def export_case(row) -> tuple[Path, Path]:
    from pylidc.utils import consensus

    scan = pl.query(pl.Scan).filter(pl.Scan.series_instance_uid == row.series_uid).first()
    vol = scan.to_volume(verbose=False)
    spacing = (float(scan.pixel_spacing), float(scan.pixel_spacing), float(scan.slice_spacing))
    image = sitk.GetImageFromArray(vol.transpose(2, 0, 1).astype(np.int16))
    image.SetSpacing(spacing)

    cluster = scan.cluster_annotations(verbose=False)[int(row.nodule_idx)]
    cmask, bbox, _ = consensus(cluster, clevel=0.5, pad=[(0, 0), (0, 0), (0, 0)])
    full = np.zeros(vol.shape, dtype=np.uint8)
    full[bbox] = cmask.astype(np.uint8)
    mask = sitk.GetImageFromArray(full.transpose(2, 0, 1))
    mask.CopyInformation(image)

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{row.patient_id}_{row.label}"
    ct_path, mask_path = DEMO_DIR / f"{stem}_ct.nii.gz", DEMO_DIR / f"{stem}_mascara.nii.gz"
    sitk.WriteImage(image, str(ct_path))
    sitk.WriteImage(mask, str(mask_path))
    return ct_path, mask_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=2)
    args = parser.parse_args()

    for row in pick_cases(args.per_class).itertuples():
        print(f"{row.patient_id}: {row.label} (malignidad {row.malignancy_median}, "
              f"{row.diameter_mm} mm) · descargando…", flush=True)
        download_one(row.patient_id, row.series_uid)
        ct, mask = export_case(row)
        print(f"   → {ct.relative_to(ROOT)} + {mask.name}")


if __name__ == "__main__":
    main()
