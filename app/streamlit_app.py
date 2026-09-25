"""
Aplicación web de radiómica: visualización de volúmenes, extracción de
características con PyRadiomics e interpretación asistida (uso académico).
"""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from app.interpret import api_key_configured, interpret_radiomics  # noqa: E402
from app.radiomics_service import (  # noqa: E402
    extract_features,
    features_to_rows,
    load_image,
    summary_metrics,
    validate_pair,
)
from app.viewer import (  # noqa: E402
    arrays_from_images,
    mask_slice_stats,
    render_mask_range_bar,
    render_slice,
    slice_with_most_mask,
)

st.set_page_config(
    page_title="Radiómica cuantitativa",
    page_icon=None,
    layout="wide",
)

DISCLAIMER = (
    "Plataforma de apoyo a la investigación y la formación en radiómica. "
    "No constituye un dispositivo de uso clínico, no reemplaza el criterio "
    "médico y no emite diagnósticos."
)


def project_defaults() -> tuple[Path | None, Path | None, Path | None]:
    data = ROOT / "data"
    img = data / "lung_001.nii.gz"
    lab = data / "lung_001_label.nii.gz"
    cfg = data / "CT_config.yaml"
    if not cfg.exists():
        cfg = ROOT / "config" / "exampleCT.yaml"
    return (
        img if img.exists() else None,
        lab if lab.exists() else None,
        cfg if cfg.exists() else None,
    )


def save_upload(upload, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(upload.getbuffer())
    return dest


def _upload_suffix(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".nii.gz"):
        return ".nii.gz"
    if lower.endswith(".nii"):
        return ".nii"
    return Path(name).suffix or ".nii.gz"


def _session_work_dir() -> Path:
    if "work_dir" not in st.session_state:
        st.session_state.work_dir = tempfile.mkdtemp(prefix="radiomics_job_")
    return Path(st.session_state.work_dir)


def main() -> None:
    st.title("Radiómica cuantitativa")
    st.caption(
        "Análisis de imágenes tomográficas y regiones de interés (ROI) "
        "mediante extracción de características radiómicas."
    )
    st.info(DISCLAIMER)

    def_img, def_lab, def_cfg = project_defaults()

    with st.sidebar:
        st.header("Datos de entrada")
        use_local = st.checkbox(
            "Usar volumen de demostración local",
            value=bool(def_img and def_lab) and not st.session_state.get("uploaded_pair"),
            help="Disponible solo si existen archivos de demostración en el entorno local.",
        )
        label = st.number_input("Etiqueta de la ROI (label)", min_value=1, value=1, step=1)
        hu_min = st.number_input("Ventana HU — mínimo", value=-1000.0)
        hu_max = st.number_input("Ventana HU — máximo", value=-100.0)
        flip_ud = st.checkbox("Invertir eje vertical", value=True)

        up_img = st.file_uploader("Volumen de imagen (.nii / .nii.gz)", type=["nii", "gz"])
        up_lab = st.file_uploader("Máscara / segmentación (.nii / .nii.gz)", type=["nii", "gz"])
        up_cfg = st.file_uploader("Configuración PyRadiomics (.yaml)", type=["yaml", "yml"])

        st.divider()
        st.caption("© 2026 Guillermo Tala · Created by Guillermo Tala")

    work = _session_work_dir()
    image_path: Path | None = None
    mask_path: Path | None = None
    config_path: Path | None = def_cfg
    case_id: str | None = None

    if up_img is not None and up_lab is not None:
        st.session_state["uploaded_pair"] = True
        case_id = f"upload|{up_img.name}:{up_img.size}|{up_lab.name}:{up_lab.size}"
        image_path = work / f"ct{_upload_suffix(up_img.name)}"
        mask_path = work / f"mask{_upload_suffix(up_lab.name)}"
        if st.session_state.get("case_id") != case_id:
            save_upload(up_img, image_path)
            save_upload(up_lab, mask_path)
    elif use_local and def_img and def_lab:
        image_path, mask_path = def_img, def_lab
        case_id = f"local|{image_path.resolve()}|{mask_path.resolve()}"
    elif up_img is not None or up_lab is not None:
        st.warning(
            "Cargue **ambos** archivos del mismo estudio: volumen de imagen y máscara de la ROI."
        )
        return

    if up_cfg is not None:
        cfg_id = f"{up_cfg.name}:{up_cfg.size}"
        config_path = work / f"config{Path(up_cfg.name).suffix}"
        if st.session_state.get("cfg_id") != cfg_id:
            save_upload(up_cfg, config_path)
            st.session_state.cfg_id = cfg_id

    if image_path is None or mask_path is None or case_id is None:
        st.warning(
            "Se requiere un volumen de imagen y su máscara de segmentación "
            "para iniciar el análisis."
        )
        return
    if config_path is None or not config_path.exists():
        st.error(
            "No se encontró el archivo de configuración de PyRadiomics. "
            "Cargue un YAML o verifique la configuración del entorno."
        )
        return

    st.caption(
        f"Imagen: `{image_path.name}` · Máscara: `{mask_path.name}` · "
        f"Configuración: `{config_path.name}`"
    )

    vol_key = f"{case_id}|label={int(label)}"
    case_changed = st.session_state.get("vol_key") != vol_key

    if case_changed or "img_arr" not in st.session_state:
        try:
            image = load_image(image_path)
            mask = load_image(mask_path)
            validate_pair(image, mask)
            img_arr, seg_arr = arrays_from_images(image, mask)
        except Exception as exc:  # noqa: BLE001
            st.error(f"No fue posible cargar o validar los volúmenes: {exc}")
            return
        st.session_state.vol_key = vol_key
        st.session_state.case_id = case_id
        st.session_state.img_arr = img_arr
        st.session_state.seg_arr = seg_arr
        st.session_state.image_path = str(image_path)
        st.session_state.mask_path = str(mask_path)
        st.session_state.config_path = str(config_path)
        st.session_state.slice_z = int(
            slice_with_most_mask(seg_arr, label=int(label))
        )
        st.session_state.pop("radiomics_result", None)
        st.session_state.pop("ai_interpretation", None)

    img_arr = st.session_state.img_arr
    seg_arr = st.session_state.seg_arr
    image_path = Path(st.session_state.image_path)
    mask_path = Path(st.session_state.mask_path)
    config_path = Path(st.session_state.config_path)

    st.caption(
        f"Dimensiones {img_arr.shape[::-1]} · Intensidad (HU) ≈ "
        f"[{float(img_arr.min()):.0f}, {float(img_arr.max()):.0f}] · "
        f"Etiquetas en máscara: "
        f"{sorted({int(x) for x in set(np.unique(seg_arr).tolist())})}"
    )
    n_slices = int(img_arr.shape[0])
    counts, z_first, z_last = mask_slice_stats(seg_arr, label=int(label))
    default_z = slice_with_most_mask(seg_arr, label=int(label))

    st.subheader("Visualización multiplanar (corte axial)")
    if "slice_z" not in st.session_state:
        st.session_state.slice_z = int(default_z)

    if z_first >= 0:
        st.caption(
            f"La ROI (label={int(label)}) está presente entre los cortes "
            f"**z={z_first}…{z_last}**. Corte de máxima extensión: **z={default_z}** "
            f"({int(counts[default_z])} vóxeles)."
        )
        solo_mask = st.checkbox(
            "Limitar el deslizador a cortes con ROI",
            value=False,
            help=f"Restringe el rango a z={z_first}…{z_last}",
        )
    else:
        st.warning(f"No se detectaron vóxeles con label={int(label)} en la máscara.")
        solo_mask = False

    z_min = int(z_first) if (solo_mask and z_first >= 0) else 0
    z_max = int(z_last) if (solo_mask and z_first >= 0) else n_slices - 1
    if not (z_min <= int(st.session_state.slice_z) <= z_max):
        st.session_state.slice_z = int(min(max(st.session_state.slice_z, z_min), z_max))

    c1, c2 = st.columns([3, 1])
    with c2:
        st.write("")
        st.button(
            "Ir al corte de máxima ROI",
            on_click=lambda: st.session_state.update(slice_z=int(default_z)),
        )
    with c1:
        z = st.slider(
            "Índice de corte (Z)",
            min_value=z_min,
            max_value=z_max,
            key="slice_z",
        )

    if z_first >= 0:
        bar = render_mask_range_bar(
            n_slices=n_slices,
            z_first=int(z_first),
            z_last=int(z_last),
            z_current=int(z),
            z_best=int(default_z),
        )
        st.pyplot(bar, clear_figure=True)
        st.caption(
            "Referencia: zona **roja** = cortes con ROI · línea azul = corte "
            "actual · marcador amarillo = máxima extensión de la ROI."
        )

    voxels_here = int(counts[int(z)])
    if voxels_here == 0:
        st.warning(
            f"En z={int(z)} la ROI está vacía. Utilice "
            f"“Ir al corte de máxima ROI” (z≈{default_z})."
        )
    else:
        st.success(f"En z={int(z)} la ROI incluye **{voxels_here}** vóxeles.")

    fig = render_slice(
        img_arr,
        seg_arr,
        z=int(z),
        hu_min=float(hu_min),
        hu_max=float(hu_max),
        label=int(label),
        flip_ud=flip_ud,
    )
    st.pyplot(fig, clear_figure=True)

    st.subheader("Extracción de características radiómicas")
    if st.button("Ejecutar análisis", type="primary"):
        with st.spinner("Extrayendo características con PyRadiomics…"):
            try:
                result = extract_features(
                    image_path, mask_path, config_path, label=int(label)
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error en la extracción: {exc}")
                return
        st.session_state["radiomics_result"] = result
        st.session_state.pop("ai_interpretation", None)

    result = st.session_state.get("radiomics_result")
    if not result:
        st.caption(
            "Presione **Ejecutar análisis** para calcular las características "
            "radiómicas de la ROI seleccionada."
        )
        return

    summary = summary_metrics(result)
    cols = st.columns(min(4, max(1, len(summary))))
    labels = {
        "original_shape_MeshVolume": "Volumen (malla)",
        "original_shape_Maximum3DDiameter": "Diámetro máximo 3D",
        "original_shape_Sphericity": "Esfericidad",
        "original_firstorder_Mean": "Media (HU)",
        "original_firstorder_Median": "Mediana (HU)",
        "original_firstorder_Minimum": "Mínimo (HU)",
        "original_firstorder_Maximum": "Máximo (HU)",
    }
    for i, (key, val) in enumerate(summary.items()):
        with cols[i % len(cols)]:
            shown = f"{val:.3f}" if isinstance(val, float) else str(val)
            st.metric(labels.get(key, key), shown)

    rows = features_to_rows(result)
    df = pd.DataFrame(rows)
    feat = df[df["kind"] == "feature"].copy()
    st.write(
        f"**{len(feat)}** características cuantitativas"
        f" ({int((df['kind'] == 'diagnostic').sum())} parámetros de control del extractor)."
    )

    only_original = st.checkbox("Mostrar solo imagen original (sin filtros)", value=True)
    if only_original:
        feat = feat[feat["image_type"] == "original"]

    classes = ["(todas)"] + sorted(feat["feature_class"].dropna().unique().tolist())
    pick = st.selectbox("Familia de características", classes)
    if pick != "(todas)":
        feat = feat[feat["feature_class"] == pick]

    st.dataframe(
        feat[["feature_class", "name", "key", "value"]],
        use_container_width=True,
        hide_index=True,
    )

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        "Descargar resultados (CSV)",
        data=csv_buf.getvalue(),
        file_name="caracteristicas_radiomicas.csv",
        mime="text/csv",
    )

    st.subheader("Interpretación asistida")
    st.caption(
        "Resumen orientativo de las métricas cuantitativas para apoyo a la "
        "discusión académica. No constituye informe clínico ni diagnóstico."
    )
    if not api_key_configured():
        st.warning(
            "La interpretación asistida no está disponible en este entorno. "
            "Consulte al administrador de la plataforma."
        )
    else:
        if st.button("Generar interpretación"):
            with st.spinner("Generando interpretación…"):
                try:
                    text = interpret_radiomics(result)
                    st.session_state["ai_interpretation"] = text
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No fue posible generar la interpretación: {exc}")
        if st.session_state.get("ai_interpretation"):
            st.markdown(st.session_state["ai_interpretation"])

    st.divider()
    st.caption("© 2026 Guillermo Tala · Created by Guillermo Tala")


if __name__ == "__main__":
    main()
