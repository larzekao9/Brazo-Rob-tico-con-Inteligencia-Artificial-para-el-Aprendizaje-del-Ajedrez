"""Importa la calibración del brazo desde los puntos enseñados en DobotStudio Pro (la forma más precisa).

En DobotStudio Pro, en Application > Points, creá estos puntos llevando el brazo con el jog hasta el CENTRO de cada casilla (pinza
vertical y siempre a la misma altura) y poneles estos alias:

    A1, H1, H8, A8    las esquinas del tablero (H8 es opcional pero mejora el ajuste)
    DESCANSO          la posición cero: dónde espera el brazo, fuera del encuadre de la cámara

Después guardá el proyecto, descargalo (trae un `point.json`) y corré:

    python scripts/importar_puntos_dobotstudio.py "C:/Users/USUARIO/Downloads/posicion_brazo/point.json"

Guarda la calibración en `calibracion_local/brazo.json` (no se sube a git), igual que `calibrar_brazo_tablero.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.servicios.brazo.calibracion_brazo import (  # noqa: E402
    ARCHIVO_CALIBRACION_BRAZO,
    guardar_calibracion_brazo,
    puntos_desde_dobotstudio,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    try:
        angulos_cero, puntos = puntos_desde_dobotstudio(Path(sys.argv[1]))
        calibracion = guardar_calibracion_brazo(angulos_cero, puntos)
    except ValueError as error:
        raise SystemExit(f"No se guardó: {error}")
    print(f"Guardado en {ARCHIVO_CALIBRACION_BRAZO}")
    print(f"  puntos usados: {', '.join(puntos)} | posición cero (ángulos): {tuple(round(a, 1) for a in angulos_cero)}")
    print(f"  orientación de la herramienta: {tuple(round(v, 2) for v in calibracion.orientacion)} | altura del tablero z={calibracion.posiciones_casillas['a1'][2]:.1f} mm")
    for aviso in calibracion.avisos:
        print(f"AVISO: {aviso}")


if __name__ == "__main__":
    main()
