"""Validación de los archivos de entrada con mensajes comprensibles para el usuario."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import yaml

FORMAT_HINT = (
    "Se esperan volúmenes NIfTI (.nii o .nii.gz). Si tiene un estudio DICOM, conviértalo "
    "primero (por ejemplo, con 3D Slicer: cargar el DICOM y exportar como .nii.gz)."
)
CONFIG_SECTIONS = {"setting", "imageType", "featureClass", "voxelSetting"}
MAX_MASK_LABELS = 50
MIN_ROI_VOXELS = 10
GEOMETRY_TOLERANCE = 1e-3


class InputError(Exception):
    """Error en los datos de entrada, con mensaje apto para mostrar al usuario."""


def check_extension(name: str, role: str) -> None:
    lower = name.lower()
    if not (lower.endswith(".nii") or lower.endswith(".gz")):
        raise InputError(f"El archivo de {role} «{name}» no tiene un formato admitido. {FORMAT_HINT}")


SAME_FILE_MSG = (
    "Se cargó el mismo archivo como imagen y como máscara{detail}. En «Volumen de imagen» "
    "va la tomografía y en «Máscara / segmentación» el archivo con la región segmentada."
)


def check_not_same_file(img_bytes: bytes, mask_bytes: bytes, img_name: str, mask_name: str) -> None:
    if img_bytes == mask_bytes:
        detail = f" («{img_name}»)" if img_name == mask_name else f" («{img_name}» y «{mask_name}» son idénticos)"
        raise InputError(SAME_FILE_MSG.format(detail=detail))


def read_volume(path: Path, role: str, original_name: str) -> sitk.Image:
    try:
        image = sitk.ReadImage(str(path))
    except Exception as exc:  # noqa: BLE001
        raise InputError(
            f"No se pudo leer el archivo de {role} «{original_name}»: no parece un NIfTI válido "
            f"o está dañado. {FORMAT_HINT}"
        ) from exc
    if image.GetDimension() != 3 or image.GetNumberOfComponentsPerPixel() != 1:
        raise InputError(
            f"El archivo de {role} «{original_name}» no es un volumen 3D en escala de grises "
            f"(dimensiones: {image.GetDimension()}, canales: {image.GetNumberOfComponentsPerPixel()})."
        )
    if min(image.GetSize()) < 2:
        raise InputError(
            f"El archivo de {role} «{original_name}» contiene un solo corte "
            f"(tamaño {image.GetSize()}); se necesita el volumen completo."
        )
    return image


def _close(a, b) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), atol=GEOMETRY_TOLERANCE))


def check_case(
    image: sitk.Image,
    mask: sitk.Image,
    label: int,
    names: tuple[str, str] = ("imagen", "máscara"),
) -> list[str]:
    """Valida el par imagen/máscara. Lanza InputError si no es utilizable; devuelve advertencias."""
    warnings: list[str] = []
    img_name, mask_name = names
    img_arr = sitk.GetArrayViewFromImage(image)
    mask_arr = sitk.GetArrayViewFromImage(mask)

    if img_arr.shape == mask_arr.shape and np.array_equal(img_arr, mask_arr):
        raise InputError(SAME_FILE_MSG.format(detail=" (ambos volúmenes tienen el mismo contenido)"))

    mask_values = np.unique(mask_arr)
    img_is_maskish = np.unique(img_arr[:: max(1, img_arr.shape[0] // 8)]).size <= MAX_MASK_LABELS
    if img_is_maskish and mask_values.size <= MAX_MASK_LABELS:
        raise InputError(
            f"El archivo cargado como imagen («{img_name}») parece una segmentación, no una "
            "tomografía: ¿se cargó la máscara en los dos lugares? En «Volumen de imagen» va la TC."
        )
    if mask_values.size > MAX_MASK_LABELS:
        if img_is_maskish:
            raise InputError(
                "Parece que los archivos están invertidos: el volumen cargado como máscara tiene "
                "intensidades continuas y el cargado como imagen parece una segmentación. "
                "Intercámbielos."
            )
        raise InputError(
            f"La máscara «{mask_name}» tiene {mask_values.size} valores distintos; una segmentación "
            "debería tener pocos (0 = fondo, 1 = ROI, etc.). Verifique que no haya cargado la "
            "imagen dos veces."
        )
    if not np.allclose(mask_values, np.round(mask_values)):
        raise InputError(
            f"La máscara «{mask_name}» contiene valores no enteros; una segmentación debe tener "
            "etiquetas enteras (0 = fondo, 1 = ROI)."
        )

    if image.GetSize() != mask.GetSize():
        raise InputError(
            f"La imagen y la máscara tienen tamaños distintos (imagen {image.GetSize()}, "
            f"máscara {mask.GetSize()}). La máscara debe haberse creado sobre el mismo estudio."
        )
    if not _close(image.GetSpacing(), mask.GetSpacing()):
        raise InputError(
            "La imagen y la máscara tienen distinto espaciado de vóxel "
            f"(imagen {tuple(round(s, 3) for s in image.GetSpacing())} mm, "
            f"máscara {tuple(round(s, 3) for s in mask.GetSpacing())} mm). "
            "Verifique que correspondan a la misma serie."
        )
    if not (_close(image.GetOrigin(), mask.GetOrigin()) and _close(image.GetDirection(), mask.GetDirection())):
        warnings.append(
            "La imagen y la máscara tienen distinta posición u orientación en el espacio. "
            "Verifique en el visor que la ROI coincida con la lesión."
        )

    labels = [int(v) for v in mask_values if v != 0]
    if not labels:
        raise InputError(f"La máscara «{mask_name}» está vacía: no contiene ninguna región segmentada.")
    if label not in labels:
        raise InputError(
            f"La máscara no contiene la etiqueta {label}. Etiquetas presentes: "
            f"{', '.join(map(str, labels))}. Ajuste «Etiqueta de la ROI» en Opciones avanzadas."
        )
    n_voxels = int((mask_arr == label).sum())
    if n_voxels < MIN_ROI_VOXELS:
        raise InputError(
            f"La ROI (etiqueta {label}) tiene solo {n_voxels} vóxeles; es demasiado pequeña para "
            "calcular características radiómicas."
        )

    lo, hi = float(img_arr.min()), float(img_arr.max())
    if lo > -500 or hi < 100:
        warnings.append(
            f"Las intensidades de la imagen ({lo:.0f} a {hi:.0f}) no parecen unidades Hounsfield de "
            "una TC. Los resultados y la probabilidad estimada podrían no ser válidos."
        )
    return warnings


def check_config(path: Path, original_name: str) -> None:
    try:
        content: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise InputError(f"La configuración «{original_name}» no es un YAML válido.") from exc
    if not isinstance(content, dict) or not content:
        raise InputError(f"La configuración «{original_name}» está vacía o no tiene el formato esperado.")
    unknown = set(content) - CONFIG_SECTIONS
    if unknown:
        raise InputError(
            f"La configuración «{original_name}» tiene secciones no reconocidas por PyRadiomics: "
            f"{', '.join(sorted(unknown))}. Secciones válidas: {', '.join(sorted(CONFIG_SECTIONS))}."
        )
