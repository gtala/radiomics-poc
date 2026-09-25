"""Visualización 2D de cortes CT + máscara."""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure


def arrays_from_images(
    image: sitk.Image, mask: sitk.Image
) -> tuple[np.ndarray, np.ndarray]:
    img = sitk.GetArrayFromImage(image).astype(np.float32)
    seg = sitk.GetArrayFromImage(mask)
    return img, seg


def slice_with_most_mask(seg: np.ndarray, label: int = 1) -> int:
    counts = (seg == label).reshape(seg.shape[0], -1).sum(axis=1)
    return int(np.argmax(counts))


def mask_slice_stats(seg: np.ndarray, label: int = 1) -> tuple[np.ndarray, int, int]:
    """Returns (counts_per_z, first_z_with_mask, last_z_with_mask)."""
    counts = (seg == label).reshape(seg.shape[0], -1).sum(axis=1)
    nz = np.where(counts > 0)[0]
    if len(nz) == 0:
        return counts, -1, -1
    return counts, int(nz.min()), int(nz.max())


def render_slice(
    img: np.ndarray,
    seg: np.ndarray,
    z: int,
    hu_min: float,
    hu_max: float,
    label: int = 1,
    flip_ud: bool = True,
    overlay_alpha: float = 0.55,
) -> Figure:
    I = img[z]
    S = (seg[z] == label).astype(np.float32)
    if flip_ud:
        I = np.flipud(I)
        S = np.flipud(S)

    fig = Figure(figsize=(10, 5), dpi=100)
    ax1, ax2 = fig.subplots(1, 2)

    ax1.imshow(I, cmap="gray", vmin=hu_min, vmax=hu_max)
    ax1.set_title(f"CT · corte z={z}")
    ax1.axis("off")

    ax2.imshow(I, cmap="gray", vmin=hu_min, vmax=hu_max)
    n_mask = int(S.sum())
    if n_mask > 0:
        red = ListedColormap([(0, 0, 0, 0), (1.0, 0.15, 0.1, 1.0)])
        ax2.imshow(
            S, cmap=red, alpha=overlay_alpha, vmin=0, vmax=1, interpolation="nearest"
        )
        ax2.contour(S, levels=[0.5], colors=["#ffee58"], linewidths=1.2)
        ax2.set_title(f"CT + máscara · {n_mask} vóxeles")
    else:
        ax2.set_title(f"CT + máscara · sin label en z={z}")
    ax2.axis("off")

    fig.tight_layout()
    return fig


def render_mask_range_bar(
    n_slices: int,
    z_first: int,
    z_last: int,
    z_current: int,
    z_best: int | None = None,
) -> Figure:
    """Barra 0..n_slices-1 con la zona de máscara resaltada y el corte actual."""
    fig = Figure(figsize=(8, 0.55), dpi=100)
    ax = fig.add_axes([0.02, 0.35, 0.96, 0.45])
    ax.set_xlim(0, max(n_slices - 1, 1))
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.axhspan(0, 1, color="#2a2a2a", zorder=0)
    if z_first >= 0 and z_last >= z_first:
        ax.axvspan(z_first, z_last, color="#e53935", alpha=0.85, zorder=1)
        ax.text(
            (z_first + z_last) / 2,
            0.5,
            f"máscara z={z_first}–{z_last}",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
            zorder=3,
        )
    ax.axvline(z_current, color="#90caf9", linewidth=2, zorder=2)
    if z_best is not None:
        ax.plot([z_best], [0.5], marker="v", color="#ffee58", markersize=7, zorder=4)
    ax.set_xlabel("Índice de corte Z (rojo = hay máscara)", fontsize=8)
    ax.tick_params(axis="x", labelsize=7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig
