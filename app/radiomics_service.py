"""Extracción de características radiómicas con PyRadiomics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import SimpleITK as sitk
from radiomics import featureextractor


def load_image(path: str | Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def validate_pair(image: sitk.Image, mask: sitk.Image) -> None:
    if image.GetSize() != mask.GetSize():
        raise ValueError(
            f"Tamaño distinto: imagen {image.GetSize()} vs máscara {mask.GetSize()}"
        )


def extract_features(
    image_path: str | Path,
    mask_path: str | Path,
    config_path: str | Path,
    label: int = 1,
) -> dict[str, Any]:
    image = load_image(image_path)
    mask = load_image(mask_path)
    validate_pair(image, mask)
    extractor = featureextractor.RadiomicsFeatureExtractor(
        str(config_path), preCrop=True
    )
    return dict(extractor.execute(image, mask, label=label))


def features_to_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in result.items():
        kind = "diagnostic" if key.startswith("diagnostics_") else "feature"
        try:
            num = float(value)
            is_numeric = True
        except (TypeError, ValueError):
            num = None
            is_numeric = False
        parts = key.split("_", 2)
        if kind == "feature" and len(parts) >= 3:
            image_type, feature_class, name = parts[0], parts[1], parts[2]
        elif kind == "feature" and len(parts) == 2:
            image_type, feature_class, name = parts[0], parts[1], ""
        else:
            image_type, feature_class, name = "", "", key
        rows.append(
            {
                "key": key,
                "kind": kind,
                "image_type": image_type,
                "feature_class": feature_class,
                "name": name,
                "value": num if is_numeric else str(value),
                "is_numeric": is_numeric,
            }
        )
    return rows


def summary_metrics(result: dict[str, Any]) -> dict[str, float | str]:
    keys = [
        "original_shape_MeshVolume",
        "original_shape_Maximum3DDiameter",
        "original_shape_Sphericity",
        "original_firstorder_Mean",
        "original_firstorder_Median",
        "original_firstorder_Minimum",
        "original_firstorder_Maximum",
    ]
    out: dict[str, float | str] = {}
    for k in keys:
        if k not in result:
            continue
        try:
            out[k] = float(result[k])
        except (TypeError, ValueError):
            out[k] = str(result[k])
    return out
