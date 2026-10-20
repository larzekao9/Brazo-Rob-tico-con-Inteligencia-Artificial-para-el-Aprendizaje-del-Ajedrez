"""Lee la ocupación del tablero con VOTACIÓN entre varios cuadros de la cámara en vivo.

Un solo cuadro puede salir con la mano encima, borroso o con una sombra; votando entre varios (y descartando los que no coinciden con
la mayoría) el resultado es estable. Devuelve `{casilla: vacia|blanca|negra}`.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from backend.servicios.vision import ocupacion
from backend.servicios.vision.camara import flujo_de_frames
from backend.servicios.vision.reconocimiento import esquinas_y_margen
from backend.servicios.vision.tablero import dividir_en_casillas, enderezar_tablero

CUADROS = 7
ACUERDO_MINIMO = 0.6
"""Fracción de cuadros que deben coincidir en una casilla para darla por vista; por debajo, la lectura se considera inestable."""


def ocupacion_de_imagen(imagen: np.ndarray) -> np.ndarray:
    """Probabilidades `(64, 3)` de una foto, en el orden de `casillas` (a8, b8 … h1)."""
    esquinas, margen = esquinas_y_margen(imagen)
    casillas = dividir_en_casillas(enderezar_tablero(imagen, esquinas), margen)
    return ocupacion.clasificar_ocupacion(list(casillas.values()))


NOMBRES = [f"{c}{f}" for f in range(8, 0, -1) for c in "abcdefgh"]


def votar(lecturas: list[np.ndarray]) -> tuple[dict[str, str], float]:
    """Mayoría por casilla entre lecturas `(64, 3)`. Devuelve `(mapa, acuerdo_minimo)`; el acuerdo es el de la casilla más dudosa."""
    etiquetas = np.argmax(np.stack(lecturas), axis=2)  # (cuadros, 64)
    mapa, peor = {}, 1.0
    for i, nombre in enumerate(NOMBRES):
        ganador, votos = Counter(etiquetas[:, i].tolist()).most_common(1)[0]
        mapa[nombre] = ocupacion.CLASES_OCUPACION[ganador]
        peor = min(peor, votos / len(lecturas))
    return mapa, peor


def leer_ocupacion_estable(cuadros: int = CUADROS) -> tuple[dict[str, str], float]:
    """Toma `cuadros` cuadros seguidos del video en vivo y devuelve la ocupación por mayoría y el acuerdo (0-1).

    Raises:
        RuntimeError: la cámara no está disponible o dejó de entregar imágenes.
        ValueError: no se detectó el tablero.
    """
    lecturas = []
    for frame in flujo_de_frames():
        lecturas.append(ocupacion_de_imagen(frame))
        if len(lecturas) >= cuadros:
            break
    if not lecturas:
        raise RuntimeError("La cámara no entrega imágenes")
    return votar(lecturas)
