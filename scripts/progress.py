"""
Barra de progreso en vivo de la descarga y la extracción de LIDC-IDRI (lee los logs).

Uso:
    python -m scripts.progress          # se actualiza cada 2 s, Ctrl+C para salir
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = {
    "Descarga ": ROOT / "outputs" / "download_lidc.log",
    "Extracción": ROOT / "outputs" / "extract_lidc.log",
}
STEP = re.compile(r"^\[(\d+)/(\d+)\]", re.M)
BAR = 30


def status(path: Path, started: dict[str, tuple[float, int]], name: str) -> str:
    if not path.exists():
        return f"{name}  en espera"
    steps = STEP.findall(path.read_text(errors="ignore"))
    if not steps:
        return f"{name}  iniciando…"
    done, total = int(steps[-1][0]), int(steps[-1][1])
    errors = path.read_text(errors="ignore").count(" error")
    t0, d0 = started.setdefault(name, (time.time(), done))
    elapsed, advanced = time.time() - t0, done - d0
    eta = ""
    if done >= total:
        eta = "terminado"
    elif advanced > 0 and elapsed > 5:
        secs = int(elapsed / advanced * (total - done))
        eta = f"faltan ~{secs // 60} min {secs % 60:02d} s"
    fill = int(BAR * done / total)
    err = f" · {errors} errores" if errors else ""
    return f"{name}  [{'█' * fill}{'░' * (BAR - fill)}] {done}/{total} {eta}{err}"


def main() -> None:
    started: dict[str, tuple[float, int]] = {}
    try:
        while True:
            lines = [status(p, started, n) for n, p in LOGS.items()]
            sys.stdout.write("\033[2K\r" + "\n\033[2K".join(lines) + f"\033[{len(lines) - 1}A\r")
            sys.stdout.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        sys.stdout.write("\n" * len(LOGS))


if __name__ == "__main__":
    main()
