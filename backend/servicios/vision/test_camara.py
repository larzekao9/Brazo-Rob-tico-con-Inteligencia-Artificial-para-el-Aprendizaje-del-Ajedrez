"""Tests de la captura por cámara.

El test contra una cámara real se saltea si esta máquina no tiene ninguna
conectada — el de manejo de error (índice inválido) sí corre siempre, sin
necesitar hardware.
"""
from __future__ import annotations

import cv2
import pytest

from backend.servicios.vision.camara import capturar_foto_tablero


def _hay_camara_disponible() -> bool:
    camara = cv2.VideoCapture(0)
    disponible = camara.isOpened()
    camara.release()
    return disponible


CAMARA_DISPONIBLE = _hay_camara_disponible()


def test_capturar_foto_camara_invalida_lanza_error() -> None:
    with pytest.raises(RuntimeError):
        capturar_foto_tablero(indice_camara=99)


@pytest.mark.skipif(not CAMARA_DISPONIBLE, reason="No hay cámara conectada en esta máquina")
def test_capturar_foto_tablero_devuelve_imagen_valida() -> None:
    imagen = capturar_foto_tablero(indice_camara=0)
    assert imagen is not None
    assert imagen.ndim == 3
