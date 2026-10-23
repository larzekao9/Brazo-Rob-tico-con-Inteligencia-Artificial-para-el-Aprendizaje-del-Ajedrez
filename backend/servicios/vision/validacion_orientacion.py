"""Comprueba con el color de las piezas que la calibración no esté girada 180° respecto del FEN.

Un tablero girado 180° se ve igual que el original (a1 y h8 son las dos casillas oscuras), así que ni la calibración ni la comparación entre
cámaras lo notan: si se marcan las esquinas desde el otro lado, a1 queda donde el tablero tiene impreso h8 y cada recorte de "pieza blanca"
muestra en realidad una negra. Lo que sí delata el giro son las piezas: si el FEN tiene piezas de los dos colores, las casillas donde dice
"blanca" tienen que verse más claras que las que dice "negra". Si se ven más oscuras, las esquinas están giradas.
"""
from __future__ import annotations

import cv2
import numpy as np

from backend.servicios.vision.tablero import recortes_ampliados

DIFERENCIA_MINIMA = 20.0
"""Diferencia de brillo (0-255) entre las piezas blancas y las negras para decidir. En las fotos reales del tablero de madera ronda los 60."""
MINIMO_POR_COLOR = 2
"""Piezas de cada color que hacen falta para comparar (con una sola, una sombra o un reflejo podrían decidir)."""
_ZONA_PIEZA = (slice(20, 80), slice(25, 71))
"""Zona del recorte ampliado (96 × 96) donde cae el cuerpo de la pieza: centro, sin el margen de arriba ni los costados."""


def girar_casilla(casilla: str) -> str:
    """La casilla simétrica respecto del centro del tablero (a1 ↔ h8, e2 ↔ d7): donde cae con las esquinas giradas 180°."""
    return f"{'abcdefgh'[7 - 'abcdefgh'.index(casilla[0])]}{9 - int(casilla[1])}"


def girar_esquinas(esquinas: np.ndarray) -> np.ndarray:
    """Esquinas en el orden de `enderezar_tablero` (a8, h8, h1, a1) con el tablero girado 180°: la nueva a8 es la vieja h1, y así."""
    return np.asarray(esquinas, dtype=np.float32)[[2, 3, 0, 1]]


def _brillo_piezas(recortes: dict[str, np.ndarray], casillas: list[str]) -> float:
    zona = [cv2.cvtColor(recortes[c][_ZONA_PIEZA], cv2.COLOR_BGR2HSV)[..., 2] for c in casillas]
    return float(np.median([z.mean() for z in zona]))


def comprobar(imagen: np.ndarray, esquinas: np.ndarray, etiquetas: dict[str, str]) -> dict:
    """Compara el brillo de las casillas que `etiquetas` dice blancas con el de las que dice negras.

    Args:
        imagen: foto completa (BGR).
        esquinas: las del área de juego, en el orden de `enderezar_tablero` (a8, h8, h1, a1).
        etiquetas: `{casilla: clase}` con clases como `white-pawn` / `black-king` / `vacia`.

    Returns:
        `{estado, brillo_blancas, brillo_negras, mensaje}`. `estado` es `"ok"`, `"invertida"` (las blancas se ven más oscuras: esquinas
        giradas 180°), `"dudosa"` (la diferencia es chica para decidir) o `"sin_datos"` (faltan piezas de algún color).
    """
    blancas = [c for c, clase in etiquetas.items() if clase.startswith("white")]
    negras = [c for c, clase in etiquetas.items() if clase.startswith("black")]
    if len(blancas) < MINIMO_POR_COLOR or len(negras) < MINIMO_POR_COLOR:
        return {
            "estado": "sin_datos", "brillo_blancas": None, "brillo_negras": None,
            "mensaje": f"Para comprobar la orientación hacen falta al menos {MINIMO_POR_COLOR} piezas de cada color.",
        }
    recortes = recortes_ampliados(imagen, esquinas)
    claro, oscuro = _brillo_piezas(recortes, blancas), _brillo_piezas(recortes, negras)
    diferencia = claro - oscuro
    if diferencia >= DIFERENCIA_MINIMA:
        estado, mensaje = "ok", "Las piezas blancas están donde dice el FEN."
    elif diferencia <= -DIFERENCIA_MINIMA:
        estado = "invertida"
        mensaje = (
            "Las piezas que el FEN dice blancas se ven oscuras y las negras claras: la calibración de esta cámara está girada 180° "
            "(a1 quedó donde el tablero tiene impreso h8). Recalibrá marcando a1 en la esquina de la A y el 1 impresos."
        )
    else:
        estado = "dudosa"
        mensaje = "No se distingue bien el color de las piezas (poca luz o reflejos): no se pudo comprobar la orientación."
    return {"estado": estado, "brillo_blancas": round(claro, 1), "brillo_negras": round(oscuro, 1), "mensaje": mensaje}
