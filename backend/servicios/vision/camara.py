"""Captura una foto del tablero desde una cámara fija conectada a esta
máquina (HU1, RF06).

Solo toma la foto — pasarla por `reconocer_tablero` (en `reconocimiento.py`)
y mostrarla en una pantalla es responsabilidad de HU6, no de acá.
"""
from __future__ import annotations

import cv2
import numpy as np


def capturar_foto_tablero(indice_camara: int = 0) -> np.ndarray:
    """Toma una foto desde la cámara indicada.

    Args:
        indice_camara: índice del dispositivo de cámara para OpenCV (0 es la
            cámara por defecto del sistema).

    Returns:
        La imagen capturada, en el mismo formato BGR que espera
        `reconocer_tablero` (el que devuelve `cv2.imread`).

    Raises:
        RuntimeError: si no se pudo abrir la cámara o capturar un frame.
    """
    camara = cv2.VideoCapture(indice_camara)
    try:
        if not camara.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara {indice_camara}")
        exito, imagen = camara.read()
        if not exito:
            raise RuntimeError(f"No se pudo capturar una foto de la cámara {indice_camara}")
        return imagen
    finally:
        camara.release()
