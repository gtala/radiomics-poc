"""
MVP local: subir CT + máscara, ver cortes, calcular radiómica,
opcionalmente interpretar con IA (OPENAI_API_KEY en .env).
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
    page_title="Radiómica POC",
    page_icon=None,
    layout="wide",
)

DISCLAIMER = (
    "Herramienta educativa / investigación. No es uso clínico y no reemplaza "
    "a un radiólogo. No diagnostica."
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
        st.session_state.work_dir = tempfile.mkdtemp(prefix="radiomica_mvp_")
    return Path(st.session_state.work_dir)


def main() -> None:
    st.title("Radiómica — nódulo pulmonar (MVP local)")
    st.info(DISCLAIMER)

    def_img, def_lab, def_cfg = project_defaults()

    with st.sidebar:
        st.header("Entradas")
        use_local = st.checkbox(
            "Usar archivos de data/ del proyecto",
            value=bool(def_img and def_lab) and not st.session_state.get("uploaded_pair"),
            help="lung_001.nii.gz + lung_001_label.nii.gz si están en data/. "
            "Desmarcá si subís otro caso.",
        )
        label = st.number_input("Label de la máscara", min_value=1, value=1, step=1)
        hu_min = st.number_input("HU min (ventana)", value=-1000.0)
        hu_max = st.number_input("HU max (ventana)", value=-100.0)
        flip_ud = st.checkbox("Flip vertical", value=True)

        up_img = st.file_uploader("CT (.nii / .nii.gz)", type=["nii", "gz"])
        up_lab = st.file_uploader("Máscara (.nii / .nii.gz)", type=["nii", "gz"])
        up_cfg = st.file_uploader("Config PyRadiomics (.yaml)", type=["yaml", "yml"])

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
        st.warning("Subí **los dos** archivos (CT y máscara) del mismo caso.")
        return

    if up_cfg is not None:
        cfg_id = f"{up_cfg.name}:{up_cfg.size}"
        config_path = work / f"config{Path(up_cfg.name).suffix}"
        if st.session_state.get("cfg_id") != cfg_id:
            save_upload(up_cfg, config_path)
            st.session_state.cfg_id = cfg_id

    if image_path is None or mask_path is None or case_id is None:
        st.warning(
            "Necesitás una CT y una máscara: subilas o dejá los archivos en data/."
        )
        return
    if config_path is None or not config_path.exists():
        st.error("Falta CT_config.yaml (data/ o config/exampleCT.yaml).")
        return

    st.caption(
        f"CT: `{image_path.name}` · Máscara: `{mask_path.name}` · Config: `{config_path.name}`"
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
            st.error(f"No se pudieron leer / validar los volúmenes: {exc}")
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

    img_arr = st.session_state.img_arr
    seg_arr = st.session_state.seg_arr
    image_path = Path(st.session_state.image_path)
    mask_path = Path(st.session_state.mask_path)
    config_path = Path(st.session_state.config_path)

    st.caption(
        f"Volumen {img_arr.shape[::-1]} · HU CT ≈ [{float(img_arr.min()):.0f}, "
        f"{float(img_arr.max()):.0f}] · labels máscara: "
        f"{sorted({int(x) for x in set(np.unique(seg_arr).tolist())})}"
    )
    n_slices = int(img_arr.shape[0])
    counts, z_first, z_last = mask_slice_stats(seg_arr, label=int(label))
    default_z = slice_with_most_mask(seg_arr, label=int(label))

    st.subheader("Visualizador de cortes")
    if "slice_z" not in st.session_state:
        st.session_state.slice_z = int(default_z)

    if z_first >= 0:
        st.caption(
            f"La máscara (label={int(label)}) solo aparece entre los cortes "
            f"**z={z_first}…{z_last}**. Mejor corte: **z={default_z}** "
            f"({int(counts[default_z])} vóxeles). En otros cortes las dos "
            "imágenes se ven iguales (no hay nada que pintar)."
        )
        solo_mask = st.checkbox(
            "Limitar slider solo a cortes con máscara",
            value=False,
            help=f"Restringe el slider a z={z_first}…{z_last}",
        )
    else:
        st.warning(f"No hay vóxeles con label={int(label)} en esta máscara.")
        solo_mask = False

    z_min = int(z_first) if (solo_mask and z_first >= 0) else 0
    z_max = int(z_last) if (solo_mask and z_first >= 0) else n_slices - 1
    # Clamp only if out of range (e.g. after toggling solo_mask), before widget
    if not (z_min <= int(st.session_state.slice_z) <= z_max):
        st.session_state.slice_z = int(min(max(st.session_state.slice_z, z_min), z_max))

    c1, c2 = st.columns([3, 1])
    with c2:
        st.write("")
        st.button(
            "Corte con más máscara",
            on_click=lambda: st.session_state.update(slice_z=int(default_z)),
        )
    with c1:
        z = st.slider(
            "Corte Z",
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
            "Barra de referencia: zona **roja** = hay máscara · línea azul = corte "
            "actual · triángulo amarillo = corte con más máscara."
        )

    voxels_here = int(counts[int(z)])
    if voxels_here == 0:
        st.warning(
            f"En z={int(z)} la máscara está vacía. Probá el botón "
            f"“Corte con más máscara” (z≈{default_z})."
        )
    else:
        st.success(f"En z={int(z)} hay **{voxels_here}** vóxeles de máscara.")

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

    st.subheader("Análisis radiómico")
    if st.button("Analizar con PyRadiomics", type="primary"):
        with st.spinner("Extrayendo características…"):
            try:
                result = extract_features(
                    image_path, mask_path, config_path, label=int(label)
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falló la extracción: {exc}")
                return
        st.session_state["radiomics_result"] = result

    result = st.session_state.get("radiomics_result")
    if not result:
        st.caption("Pulsá Analizar para calcular features (mismo motor que el cuaderno).")
        return

    summary = summary_metrics(result)
    cols = st.columns(min(4, max(1, len(summary))))
    labels = {
        "original_shape_MeshVolume": "MeshVolume",
        "original_shape_Maximum3DDiameter": "Diámetro máx 3D",
        "original_shape_Sphericity": "Esfericidad",
        "original_firstorder_Mean": "Mean HU",
        "original_firstorder_Median": "Median HU",
        "original_firstorder_Minimum": "Min HU",
        "original_firstorder_Maximum": "Max HU",
    }
    for i, (key, val) in enumerate(summary.items()):
        with cols[i % len(cols)]:
            shown = f"{val:.3f}" if isinstance(val, float) else str(val)
            st.metric(labels.get(key, key), shown)

    rows = features_to_rows(result)
    df = pd.DataFrame(rows)
    feat = df[df["kind"] == "feature"].copy()
    st.write(
        f"**{len(feat)}** features numéricas"
        f" (+ {int((df['kind'] == 'diagnostic').sum())} diagnósticos internos)."
    )

    only_original = st.checkbox("Solo image_type = original", value=True)
    if only_original:
        feat = feat[feat["image_type"] == "original"]

    classes = ["(todas)"] + sorted(feat["feature_class"].dropna().unique().tolist())
    pick = st.selectbox("Familia", classes)
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
        "Descargar CSV completo",
        data=csv_buf.getvalue(),
        file_name="radiomics_features.csv",
        mime="text/csv",
    )

    st.subheader("Interpretación con IA (criollo)")
    st.caption(
        "Explica los números en lenguaje simple. No diagnostica. "
        "La API key va en `.env` (nunca en el chat ni en Git)."
    )
    if not api_key_configured():
        st.warning(
            "No hay `OPENAI_API_KEY`. Copiá `.env.example` → `.env`, pegá tu key "
            "ahí, reiniciá Streamlit y volvé a intentar."
        )
    else:
        if st.button("Explicar resultados en criollo"):
            with st.spinner("Consultando el modelo…"):
                try:
                    text = interpret_radiomics(result)
                    st.session_state["ai_interpretation"] = text
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo interpretar: {exc}")
        if st.session_state.get("ai_interpretation"):
            st.markdown(st.session_state["ai_interpretation"])


if __name__ == "__main__":
    main()
